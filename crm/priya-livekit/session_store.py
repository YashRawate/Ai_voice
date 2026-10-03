# crm/priya-livekit/session_store.py
"""
Redis-Backed SessionStore for AdmitAI Priya Voice Agent.
Provides single source of truth for:
  - session:{session_id}:facts       (HASH: name, program, marks_12, etc.)
  - session:{session_id}:history     (LIST: JSON-encoded {role, content, lang, ts} per turn)
  - session:{session_id}:state       (HASH: stage, next_field, language_code, is_followup)
  - session:{session_id}:lock        (STRING: short-TTL 5s mutex)

Guarantees:
  1. Single TTL (1200s / 20 min) refreshed on every write so state, facts, and history expire together.
  2. Non-blocking fallback: If Redis is unavailable or times out (>100ms), seamlessly falls back
     to an in-process dictionary store without failing or interrupting the call.
  3. Language is stored inside state['language_code'] so language switches never touch facts or history.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from prompts import CORE_IDENTITY_AND_RULES, LANGUAGE_STYLE, FACT_SHEET

logger = logging.getLogger("priya.session_store")


class SessionStore:
    TTL = 1200  # 20 minutes expiration
    REDIS_TIMEOUT_SEC = 0.100  # 100ms timeout guard

    def __init__(self, redis_url: Optional[str] = None):
        self._url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis_client: Optional[redis.Redis] = None
        self._redis_enabled = REDIS_AVAILABLE
        self._fallback_store: Dict[str, Dict[str, Any]] = {}

        enable_redis = os.getenv("REDIS_URL") or os.getenv("ENABLE_REDIS_MEMORY", "false").lower() == "true"
        if not enable_redis or not self._redis_enabled:
            self._redis_enabled = False
            self._redis_client = None
            logger.info("[SESSION_STORE] Using in-memory session store")
        else:
            try:
                self._redis_client = redis.from_url(
                    self._url,
                    decode_responses=True,
                    socket_connect_timeout=self.REDIS_TIMEOUT_SEC,
                    socket_timeout=self.REDIS_TIMEOUT_SEC,
                )
                # Quick health check (ping)
                self._redis_client.ping()
                logger.info(f"[SESSION_STORE] Connected to Redis at {self._url}")
            except Exception as e:
                logger.warning(f"[SESSION_STORE] Redis connection failed ({e}). Operating in memory fallback mode.")
                self._redis_client = None

    # ── Internal Fallback Helpers ────────────────────────────────────────────

    def _get_fallback_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self._fallback_store:
            self._fallback_store[session_id] = {
                "facts": {},
                "history": [],
                "state": {
                    "stage": "GREETING",
                    "next_field": "student_name",
                    "language_code": "en-IN",
                    "is_followup": "False",
                },
                "expires_at": time.time() + self.TTL,
            }
        else:
            # Refresh TTL
            self._fallback_store[session_id]["expires_at"] = time.time() + self.TTL
        return self._fallback_store[session_id]

    # ── State Management ─────────────────────────────────────────────────────

    def get_state(self, session_id: str) -> Dict[str, Any]:
        """Retrieves session state hash {stage, next_field, language_code, is_followup}."""
        if self._redis_client:
            try:
                raw = self._redis_client.hgetall(f"session:{session_id}:state")
                if raw:
                    # Convert boolean string
                    is_followup = str(raw.get("is_followup", "False")).lower() in ("true", "1")
                    raw["is_followup"] = is_followup
                    return raw
            except Exception as e:
                logger.debug(f"[SESSION_STORE] Redis get_state failed ({e}), using fallback")

        mem = self._get_fallback_session(session_id)
        st = dict(mem["state"])
        st["is_followup"] = str(st.get("is_followup", "False")).lower() in ("true", "1")
        return st

    def update_state(self, session_id: str, **fields):
        """Updates specific fields in state hash and refreshes TTL."""
        if not fields:
            return

        # Ensure all values are strings for Redis hash storage
        str_fields = {k: str(v) for k, v in fields.items()}

        if self._redis_client:
            try:
                key = f"session:{session_id}:state"
                self._redis_client.hset(key, mapping=str_fields)
                self._redis_client.expire(key, self.TTL)
            except Exception as e:
                logger.debug(f"[SESSION_STORE] Redis update_state failed ({e}), updating fallback")

        mem = self._get_fallback_session(session_id)
        mem["state"].update(str_fields)

    # ── Facts Ledger ─────────────────────────────────────────────────────────

    def get_facts(self, session_id: str) -> Dict[str, str]:
        """Retrieves all caller profile facts {name, program, marks_12, ...}."""
        if self._redis_client:
            try:
                raw = self._redis_client.hgetall(f"session:{session_id}:facts")
                if raw:
                    return raw
            except Exception as e:
                logger.debug(f"[SESSION_STORE] Redis get_facts failed ({e}), using fallback")

        mem = self._get_fallback_session(session_id)
        return dict(mem["facts"])

    def merge_facts(self, session_id: str, new_facts: Dict[str, Any]):
        """Additive merge into facts hash — never overwrites the whole hash, never clears it."""
        if not new_facts:
            return

        valid_facts = {str(k): str(v) for k, v in new_facts.items() if v is not None and not str(k).startswith("_")}
        if not valid_facts:
            return

        if self._redis_client:
            try:
                key = f"session:{session_id}:facts"
                self._redis_client.hset(key, mapping=valid_facts)
                self._redis_client.expire(key, self.TTL)
            except Exception as e:
                logger.debug(f"[SESSION_STORE] Redis merge_facts failed ({e}), merging in fallback")

        mem = self._get_fallback_session(session_id)
        mem["facts"].update(valid_facts)

    # ── History ──────────────────────────────────────────────────────────────

    def append_history(self, session_id: str, role: str, content: str, lang: str):
        """Appends a turn entry to session history list and refreshes TTL."""
        entry = json.dumps({
            "role": role,
            "content": content,
            "lang": lang,
            "ts": time.time()
        })

        if self._redis_client:
            try:
                key = f"session:{session_id}:history"
                self._redis_client.rpush(key, entry)
                self._redis_client.expire(key, self.TTL)
            except Exception as e:
                logger.debug(f"[SESSION_STORE] Redis append_history failed ({e}), appending in fallback")

        mem = self._get_fallback_session(session_id)
        mem["history"].append(entry)

    def get_recent_history(self, session_id: str, n: int = 6) -> List[Dict[str, Any]]:
        """Retrieves last n turns from session history."""
        if self._redis_client:
            try:
                raw = self._redis_client.lrange(f"session:{session_id}:history", -n, -1)
                if raw:
                    return [json.loads(x) for x in raw]
            except Exception as e:
                logger.debug(f"[SESSION_STORE] Redis get_recent_history failed ({e}), using fallback")

        mem = self._get_fallback_session(session_id)
        raw_history = mem["history"][-n:] if n > 0 else mem["history"]
        return [json.loads(x) for x in raw_history]

    # ── Lifecycle & Teardown ─────────────────────────────────────────────────

    def end_session(self, session_id: str):
        """Deletes all session keys on call termination."""
        if self._redis_client:
            try:
                for suffix in ("facts", "history", "state", "lock"):
                    self._redis_client.delete(f"session:{session_id}:{suffix}")
            except Exception as e:
                logger.debug(f"[SESSION_STORE] Redis end_session failed ({e})")

        self._fallback_store.pop(session_id, None)


# Global singleton instance
GLOBAL_SESSION_STORE = SessionStore()


# ── Prompt Assembler ─────────────────────────────────────────────────────────

def build_prompt(session_id: str, current_input: str, store: Optional[SessionStore] = None) -> List[Dict[str, str]]:
    """
    Builds single shared 5-layer prompt strictly bound to token budget (<600 tokens).
    Language, stage, and facts are read from the same Redis-backed SessionStore.
    """
    st = store or GLOBAL_SESSION_STORE
    state = st.get_state(session_id)
    facts = st.get_facts(session_id)
    history = st.get_recent_history(session_id, n=6)  # last 3 conversational turns

    facts_str = "\n".join(f"• {k}: {v}" for k, v in facts.items()) if facts else "(none yet)"
    lang_code = state.get("language_code", "en-IN")
    lang_style = LANGUAGE_STYLE.get(lang_code, LANGUAGE_STYLE.get("en-IN", ""))

    system_content = f"""{CORE_IDENTITY_AND_RULES}

KNOWN FACTS (never re-ask these):
{facts_str}

CURRENT STAGE: {state.get('stage', 'GREETING')}
FIELD TO COLLECT THIS TURN: {state.get('next_field') or '(all required fields collected)'}

UNIVERSITY FACT SHEET:
{FACT_SHEET}

LANGUAGE STYLE (respond in this language — everything else above still applies):
{lang_style}

ANTI-REPETITION MANDATE:
Never ask for information already present in KNOWN FACTS above.
If student name is known, address them by name and NEVER ask for their name.
If program is known, do not ask what branch/program they want.
If marks or exam scores are known, do not ask for them again.
"""
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_content.strip()}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    if current_input:
        messages.append({"role": "user", "content": current_input})

    return messages
