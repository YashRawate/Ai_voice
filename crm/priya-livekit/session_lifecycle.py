# crm/priya-livekit/session_lifecycle.py
"""
Session Lifecycle Management for AdmitAI Priya Voice Agent.
Cleanly separates three distinct lifecycle operations to prevent mid-call re-greetings and memory wipes:
1. start_new_call(): Called EXACTLY ONCE per call on first connection. Only place that plays opening greeting.
2. reconnect_transport(): Re-establishes STT/TTS sockets on noise-induced drops. Preserves facts, stage, and history.
3. apply_language_switch(): Updates language_code only. Preserves session_id, facts, and conversation context.
"""

import logging
import time
import uuid
import traceback
from typing import Optional, Dict, Any

from state import CallState
from session_manager import SessionContext
from test_session_logger import get_or_create_logger, TestSessionLogger

logger = logging.getLogger("priya.session")

# Active call session registry keyed strictly by session_id
_ACTIVE_CALL_REGISTRY: Dict[str, SessionContext] = {}


def start_new_call(
    phone: Optional[str] = None,
    session_id: Optional[str] = None,
    initial_facts: Optional[Dict[str, Any]] = None,
    initial_language: str = "en-IN",
) -> SessionContext:
    """
    Called EXACTLY ONCE per call — on the very first inbound connection/turn.
    This is the ONLY function allowed to initialize call state or play the opening greeting.
    """
    sid = session_id or str(uuid.uuid4())
    test_logger = get_or_create_logger(sid)

    stack_str = "".join(traceback.format_stack()[-6:])
    if sid in _ACTIVE_CALL_REGISTRY:
        logger.warning(
            "[SESSION_INIT] Session %s already exists in registry — duplicate call detected! stack=%s",
            sid, stack_str
        )
        test_logger.log_session_init(reason="duplicate_call_start_attempt", is_first_call=False)
        return _ACTIVE_CALL_REGISTRY[sid]

    logger.warning(
        "[SESSION_INIT] Called for phone=%s | sid=%s | stack=%s",
        phone or "unknown", sid, stack_str
    )
    test_logger.log_session_init(reason="first_inbound_call_start", is_first_call=True)

    ctx = SessionContext(session_id=sid)
    ctx.active_language = initial_language
    ctx.collected = dict(initial_facts or {})
    ctx.stage = "GREETING"
    _ACTIVE_CALL_REGISTRY[sid] = ctx
    return ctx


def get_existing_session(session_id: str) -> Optional[SessionContext]:
    """Retrieve an existing session without re-initializing or re-greeting."""
    return _ACTIVE_CALL_REGISTRY.get(session_id)


def reconnect_transport(ctx: SessionContext, reason: str = "transport_reconnect"):
    """
    Called when the STT/TTS WebSocket drops mid-call (e.g., from noise-induced packet loss).
    Must NOT touch facts, stage, messages, or session_id.
    Must NOT call start_new_call() or play_opening_greeting().
    """
    logger.info(
        "[TRANSPORT_RECONNECT] Reconnecting transport for sid=%s (reason: %s). State and facts preserved.",
        ctx.session_id, reason
    )
    test_logger = get_or_create_logger(ctx.session_id)
    test_logger.log_reconnect(transport="websocket_telephony", reason=reason)


def apply_language_switch(ctx: SessionContext, new_language: str, reason: str = "caller_request", confidence: Optional[float] = None):
    """
    Called when the 6-layer language engine approves a switch.
    Must ONLY set language_code — nothing else.
    Must NOT reset facts, stage, messages, or replay greeting.
    """
    if not new_language or new_language == ctx.active_language:
        return
    old_lang = ctx.active_language
    ctx.active_language = new_language
    logger.info(
        "[LANGUAGE_SWITCH] sid=%s switched language: %s -> %s (reason: %s). Facts ledger (%d items) preserved.",
        ctx.session_id, old_lang, new_language, reason, len(ctx.collected)
    )
    test_logger = get_or_create_logger(ctx.session_id)
    test_logger.log_language_switch(old_lang=old_lang, new_lang=new_language, confidence=confidence)


def end_call_session(session_id: str, disposition: str = "completed", notes: str = ""):
    """Clean up call session on hangup/termination and finalize diagnostic logs."""
    test_logger = get_or_create_logger(session_id)
    test_logger.finalize(disposition=disposition, notes=notes)

    if session_id in _ACTIVE_CALL_REGISTRY:
        logger.info("[SESSION_END] Cleaning up session %s", session_id)
        del _ACTIVE_CALL_REGISTRY[session_id]
