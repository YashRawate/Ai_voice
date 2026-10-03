# crm/priya-livekit/priya/language/resolver.py
"""
Language Resolver & Code-Mixed Stability Engine for AdmitAI Priya Voice Agent.

Ensures:
1. Language detection locks cleanly for the turn.
2. Code-mixed utterances (e.g. Hindi with English loanwords) do not flip Priya back to English.
3. System prompt strictly pins 'MUST respond ONLY in <language>' on every turn.
4. The same active_language flows through STT -> LLM -> TTS without mismatch.
"""

from __future__ import annotations

import re
import logging
from typing import Optional, Set, Dict

from explicit_switch_detector import ExplicitLanguageSwitchDetector

logger = logging.getLogger("priya.language_resolver")

SUPPORTED_LANGS: Set[str] = {"hi-IN", "te-IN", "ta-IN", "en-IN"}

LANG_NAMES: Dict[str, str] = {
    "hi-IN": "Hindi",
    "te-IN": "Telugu",
    "ta-IN": "Tamil",
    "en-IN": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "en": "English",
}

LANG_SCRIPTS: Dict[str, str] = {
    "hi-IN": "Devanagari script (हिंदी)",
    "te-IN": "Telugu script (తెలుగు)",
    "ta-IN": "Tamil script (தமிழ்)",
    "en-IN": "English",
}

_EXPLICIT_DETECTOR = ExplicitLanguageSwitchDetector()

# Indic grammatical markers and loanword indicators in Romanized code-mixing
_INDIC_MARKERS = re.compile(
    r'\b(hai|hain|kya|kitna|kitni|kitne|hoga|hogi|batao|bataiye|chahiye|mein|me|ka|ki|ke|ko|se|aur|'
    r'undi|undhi|entha|enti|cheppandi|telusukovalani|kavali|kavalani|garu|andi|bhayya|kadha|mariyu|'
    r'enna|eppadi|solunga|venum|irukku|enga)\b',
    re.I
)

# Common higher-ed loanwords used in code-mixed conversation
_LOANWORDS = {
    "admission", "admissions", "status", "fee", "fees", "scholarship", "scholarships",
    "campus", "hostel", "placement", "placements", "branch", "computer", "science",
    "marks", "score", "exam", "exams", "percent", "percentage", "jee", "eapcet", "asat",
    "okay", "ok", "yes", "sure", "form", "application", "college", "university"
}


def normalize_lang_code(code: Optional[str]) -> str:
    """Normalize language codes: 'hi' -> 'hi-IN', 'te' -> 'te-IN', etc."""
    if not code:
        return "en-IN"
    c = code.strip().lower()
    if c in {"hi", "hindi", "hi-in"}:
        return "hi-IN"
    if c in {"te", "telugu", "te-in"}:
        return "te-IN"
    if c in {"ta", "tamil", "ta-in"}:
        return "ta-IN"
    if c in {"en", "english", "en-in", "en-us"}:
        return "en-IN"
    return code if code in SUPPORTED_LANGS else "en-IN"


from transcript_guards import dominant_script, ALLOWED_SCRIPTS

_SWITCH_STREAKS: Dict[str, Dict[str, Any]] = {}


def resolve_mixed_language(detected_lang: Optional[str], transcript: str, session_lang: str = "en-IN", session_id: str = "default") -> str:
    """
    Policy: once a language is established for the session, minor code-mixing,
    short utterances, or background chatter do NOT flip the language.
    
    Only switch on:
    1. Explicit user language switch command ('speak in English', 'हिंदी में बात करो', 'Telugu lo matladandi').
    2. Supported script (LATIN, DEVANAGARI, TELUGU).
    3. 2 consecutive long utterances (>= 4 words) in the new language.

    Args:
        detected_lang: Raw detected language from STT or audio/script detector.
        transcript: Spoken text transcription.
        session_lang: Currently locked conversation language for the session.
        session_id: Session identifier to track hysteresis streaks.

    Returns:
        Resolved language code ('en-IN', 'hi-IN', 'te-IN', or 'ta-IN').
    """
    text = (transcript or "").strip()
    norm_session = normalize_lang_code(session_lang)
    norm_detected = normalize_lang_code(detected_lang)

    # 1. Explicit User Request (Highest Priority — 100% confidence, immediate)
    if text:
        explicit = _EXPLICIT_DETECTOR.detect_explicit_switch(text)
        if explicit.is_explicit_switch and explicit.target_language in SUPPORTED_LANGS:
            logger.info(f"[LANG_RESOLVER] Explicit switch request detected: {norm_session} -> {explicit.target_language}")
            _SWITCH_STREAKS.pop(session_id, None)
            return explicit.target_language

    # If detection agrees with current session language, keep it and reset any pending switch streak
    if norm_detected == norm_session:
        _SWITCH_STREAKS.pop(session_id, None)
        return norm_session

    # 2. Supported Script Check: Never switch to/from an unsupported script (e.g. Bengali)
    script = dominant_script(text)
    if script is not None and script not in ALLOWED_SCRIPTS:
        logger.info(f"[LANG_RESOLVER] Unsupported script '{script}' in utterance — holding locked lang '{norm_session}'")
        return norm_session

    # 3. Short Utterance Guard (< 4 words or < 15 characters)
    words = re.findall(r'\w+', text)
    if len(words) < 4 or len(text) < 15:
        logger.debug(f"[LANG_RESOLVER] Short utterance ({len(words)} words, {len(text)} chars) — preserving session lang '{norm_session}'")
        return norm_session

    # 4. Code-Mixed Speech Stability Guard
    # If session is already in Hindi/Telugu/Tamil, do not flip to English because of English loanwords
    if norm_session in {"hi-IN", "te-IN", "ta-IN"} and norm_detected == "en-IN":
        word_set = set(w.lower() for w in words)
        has_indic_words = bool(_INDIC_MARKERS.search(text))
        has_loanwords = bool(word_set & _LOANWORDS)
        has_indic_script = bool(re.search(r'[\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF]', text))

        if has_indic_script or has_indic_words or has_loanwords:
            logger.info(f"[LANG_RESOLVER] Code-mixed speech with Indic markers — holding locked lang '{norm_session}'")
            return norm_session

        if len(text) < 25:
            logger.info(f"[LANG_RESOLVER] Ambiguous English utterance (<25 chars) — holding locked lang '{norm_session}'")
            return norm_session

    # 5. Consecutive Long Utterance Requirement (requires 2 consecutive turns in candidate language)
    streak_data = _SWITCH_STREAKS.get(session_id, {"candidate": "", "count": 0})
    if streak_data.get("candidate") == norm_detected:
        streak_data["count"] += 1
    else:
        streak_data = {"candidate": norm_detected, "count": 1}
    _SWITCH_STREAKS[session_id] = streak_data

    if streak_data["count"] < 2:
        logger.info(f"[LANG_RESOLVER] Pending language switch to {norm_detected} (streak 1/2, need 2 consecutive) — holding '{norm_session}'")
        return norm_session

    # Confirmed after 2 consecutive turns
    _SWITCH_STREAKS.pop(session_id, None)
    logger.info(f"[LANG_RESOLVER] Confirmed language switch (2 consecutive long turns): {norm_session} -> {norm_detected}")
    return norm_detected


def build_language_system_prompt(active_language: str, base_prompt: str = "") -> str:
    """
    Builds the explicit per-turn language mandate that forces the LLM to respond
    strictly in the caller's language and script.
    """
    norm_lang = normalize_lang_code(active_language)
    lang_name = LANG_NAMES.get(norm_lang, "English")
    script_name = LANG_SCRIPTS.get(norm_lang, "English")

    if norm_lang == "en-IN":
        mandate = (
            "CRITICAL LANGUAGE INSTRUCTION: The user is speaking in English. "
            "You MUST respond ONLY in simple, clear, conversational English. "
            "Keep your reply under 25 words with exactly ONE question."
        )
    else:
        mandate = (
            f"CRITICAL LANGUAGE INSTRUCTION:\n"
            f"The user is speaking in {lang_name}.\n"
            f"You MUST respond ONLY in {lang_name}, using {script_name} (not transliterated/romanized).\n"
            f"Do NOT switch to English even if the user's sentence contains English words mixed in — "
            f"reply fully in {lang_name}.\n"
            f"Keep your reply under 25 words with exactly ONE question."
        )

    if base_prompt:
        return f"{base_prompt}\n\n{mandate}"
    return mandate
