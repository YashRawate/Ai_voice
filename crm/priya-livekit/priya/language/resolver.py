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


def resolve_mixed_language(detected_lang: Optional[str], transcript: str, session_lang: str = "en-IN") -> str:
    """
    Policy: once an Indic language is established for the session, minor code-mixing
    or short neutral utterances do NOT flip it back to English.
    
    Only switch on:
    1. Explicit user language switch command ('speak in English', 'हिंदी में बात करो').
    2. A sufficiently long, confident utterance in a different language.

    Args:
        detected_lang: Raw detected language from STT or audio/script detector.
        transcript: Spoken text transcription.
        session_lang: Currently locked conversation language for the session.

    Returns:
        Resolved language code ('en-IN', 'hi-IN', 'te-IN', or 'ta-IN').
    """
    text = (transcript or "").strip()
    norm_session = normalize_lang_code(session_lang)
    norm_detected = normalize_lang_code(detected_lang)

    # 1. Explicit User Request (Highest Priority — 100% confidence)
    if text:
        explicit = _EXPLICIT_DETECTOR.detect_explicit_switch(text)
        if explicit.is_explicit_switch and explicit.target_language in SUPPORTED_LANGS:
            logger.info(f"[LANG_RESOLVER] Explicit switch request detected: {norm_session} -> {explicit.target_language}")
            return explicit.target_language

    # If detection agrees with current session language, keep it
    if norm_detected == norm_session:
        return norm_session

    # 2. Short Utterance Guard (< 15 characters)
    # Short responses like 'okay', 'yes', 'fee kitna', 'batao' must not flip the session language
    if len(text) < 15:
        logger.debug(f"[LANG_RESOLVER] Short utterance ({len(text)} chars) — preserving session lang '{norm_session}'")
        return norm_session

    # 3. Code-Mixed Speech Stability Guard
    # If session is already in Hindi/Telugu/Tamil, do not flip to English because of English loanwords
    if norm_session in {"hi-IN", "te-IN", "ta-IN"} and norm_detected == "en-IN":
        # Check if the sentence has Indic markers or code-mixed loanwords
        words = set(re.sub(r'[^a-zA-Z\s]', '', text.lower()).split())
        has_indic_words = bool(_INDIC_MARKERS.search(text))
        has_loanwords = bool(words & _LOANWORDS)

        # Native script presence
        has_indic_script = bool(re.search(r'[\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF]', text))

        if has_indic_script or has_indic_words or has_loanwords:
            logger.info(f"[LANG_RESOLVER] Code-mixed speech detected with Indic markers — holding locked lang '{norm_session}'")
            return norm_session

        # Only switch to English if utterance is long (>= 25 chars) and purely conversational English
        if len(text) < 25:
            logger.info(f"[LANG_RESOLVER] Ambiguous English utterance (<25 chars) — holding locked lang '{norm_session}'")
            return norm_session

    # 4. Genuine, confident language switch
    logger.info(f"[LANG_RESOLVER] Confirmed language switch: {norm_session} -> {norm_detected}")
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
