# priya-livekit/language_handler.py
"""
Simple Language Matching & Unified Prompt Handler
Guarantees memory and facts ledger continuity across mid-call language switches.
Language is a variable substituted into ONE shared prompt, never swapping out the core prompt/memory.
"""

import re
from typing import Optional, Dict, Any, List

LANGUAGE_STYLE_BLOCKS = {
    "en-IN": "Respond ONLY in ENGLISH (simple, clear, conversational Indian English). Keep under 25 words.",
    "hi-IN": "Respond ONLY in HINDI / Hinglish (हिंदी / Hinglish). Use respectful 'आप' / 'जी'. Keep under 25 words.",
    "te-IN": "Respond ONLY in TELUGU / Telugish (తెలుగు / Teluglish). Use respectful 'మీరు' / 'అండి' / 'గారు'. Keep under 25 words.",
    "ta-IN": "Respond ONLY in TAMIL / Tanglish (தமிழ் / Tanglish). Keep under 25 words.",
}

CORE_IDENTITY_AND_RULES = """# ROLE & MISSION
You are Priya, a warm, intelligent and consultative Senior Admissions Counsellor at Aditya University (2025-26).
YOUR PRIMARY MISSION: CONVERT EVERY CALLER / ENQUIRY INTO AN ADMISSION.
You are a conversational voice agent, not a form-filling bot.

# CORE CONTEXT-FLOW PRINCIPLE
The conversation is STATEFUL.
- Never restart conversation logic or re-ask known details.
- A newer explicit statement from the caller overrides older stored memory.
- If the caller asks a direct question (fees, hostels, placements, scholarships), ANSWER IT FIRST using verified knowledge before resuming qualification.
- If interrupted, drop your prior thought immediately and answer directly in under 20 words without apologizing.

# 5-STAGE ADMISSION CONVERSATION FLOW
Stage 1: Greeting & Identify Caller (Name, Student vs Parent)
Stage 2: Program & Course Interest (B.Tech CSE, AI/ML, ECE, MBA, Pharmacy)
Stage 3: Academic Background & Eligibility (12th Board %, JEE, EAPCET, ASAT)
Stage 4: Consultative Value Pitch (3,800+ placements, 27 LPA highest, merit scholarships)
Stage 5: High-Conversion Close (Book Campus Visit, ASAT Exam, Application link)

# OFFICIAL FACT SHEET
• Campus: 250-acre smart green campus in Surampalem, Kakinada District, AP. NAAC A++ accredited, NIRF Top 151-200.
• B.Tech Tuition Fees: CSE & Specializations (AI&ML, Data Science) ₹2,75,000/year; Core branches (ECE, EEE, Mech, Civil) ₹1,00,000 to ₹1,35,000/year.
• Merit Scholarships: ≥95%: 50% waiver; 90-95%: 40%; 85-90%: 30%; 80-85%: 20%; 75-80%: 10% waiver.
• Placements: 3,832+ offers, highest package ₹27 LPA (Walmart). Top recruiters: Amazon, Walmart, CISCO, TCS, Infosys.
• Hostels: Non-AC ₹1,15,000/year; AC ₹1,30,000/year.
• Unavailable: MBBS, Law, Aviation, Architecture (suggest B.Tech/Pharmacy/MBA).

# HARD VOICE OUTPUT RULES
1. Spoken response ONLY. Max 25 words per reply. Concise, conversational tone.
2. Max ONE question per turn. Never combine multiple questions.
3. No markdown, bullets, emojis, asterisks, stage directions, or "Priya:" prefix.
"""


class LanguageHandler:
    """Match caller's language and build unified stateful prompts."""

    # Map STT output to standard language codes
    LANGUAGE_MAP = {
        "en": "en-IN",
        "en-in": "en-IN",
        "en-IN": "en-IN",
        "english": "en-IN",
        "eng": "en-IN",

        "hi": "hi-IN",
        "hi-in": "hi-IN",
        "hi-IN": "hi-IN",
        "hindi": "hi-IN",
        "hin": "hi-IN",

        "te": "te-IN",
        "te-in": "te-IN",
        "te-IN": "te-IN",
        "telugu": "te-IN",
        "tel": "te-IN",

        "ta": "ta-IN",
        "ta-in": "ta-IN",
        "ta-IN": "ta-IN",
        "tamil": "ta-IN",
        "tam": "ta-IN",
    }

    # Regex indicators for text fallback
    _TELUGU_SCRIPT = re.compile(r'[\u0C00-\u0C7F]')
    _HINDI_SCRIPT = re.compile(r'[\u0900-\u097F]')
    _TAMIL_SCRIPT = re.compile(r'[\u0B80-\u0BFF]')

    _TELUGU_WORDS = re.compile(
        r'\b(entha|enti|entandi|cheppandi|telusukovalani|kavali|kavalani|undi|undhi|unnanu|untundi|untundhi|'
        r'meeru|naaku|chudandi|adagali|chadavali|chaduvutunnanu|cheyali|chey|mariyu|kadha|kadhara|emi|ela|'
        r'eppudu|akkada|ikkada|emiti|sare|babu|amma|vachanu|vasthanu|unnara|chudam|chesanu|ivvandi|cheppara|'
        r'lekapothe|pettandi|undha|leka|chala|baguntunda|bhayya|ayya|garu|andi|mastaru|masthu|mastu|etla|'
        r'etlundhi|kaneesam|koddiga|chusthunna)\b',
        re.I
    )

    _HINDI_WORDS = re.compile(
        r'\b(kya|hai|hain|kitna|kitni|kitne|hoga|hogi|hoge|bataiye|batao|bata|chahiye|kaise|kahan|kaha|aap|'
        r'tum|mujhe|aur|theek|accha|kab|kyun|bol|bolo|raha|rahi|rahe|hoon|hun|sunte|sunao|kare|karna|'
        r'chahunga|chahungi|milega|milegi|bhai|bhaiya|yaar|dost|kaisa|sahi hai)\b',
        re.I
    )

    _TAMIL_WORDS = re.compile(
        r'\b(enna|eppadi|solunga|venum|irukku|enga|ungalukku|enakku|kandippa|vanakkam|nandri)\b',
        re.I
    )

    _ENGLISH_WORDS = re.compile(
        r'\b(can i|i want|could you|what is|tell me|how much|campus visit|admission|application|book|saturday|sunday|thank you|goodbye|please)\b',
        re.I
    )

    _NEUTRAL_WORDS = {
        "ok", "okay", "yes", "yeah", "yep", "sure", "fine", "alright", "hmm", "ha",
        "haan", "avunu", "sare", "theek", "theek hai"
    }

    @staticmethod
    def normalize_language(detected_language: Optional[str]) -> str:
        """
        Convert whatever STT returns to standard format
        Input: "english", "en", "hindi", "hi-IN", etc.
        Output: "en-IN", "hi-IN", "te-IN", or "ta-IN"
        """
        if not detected_language:
            return "en-IN"  # Default to English

        normalized = detected_language.lower().strip()
        return LanguageHandler.LANGUAGE_MAP.get(normalized, "en-IN")

    # Backward-compatible alias
    get_language_code = normalize_language

    @staticmethod
    def get_language_style(language_code: str) -> str:
        """Get concise language style directive."""
        code = LanguageHandler.normalize_language(language_code)
        return LANGUAGE_STYLE_BLOCKS.get(code, LANGUAGE_STYLE_BLOCKS["en-IN"])

    @staticmethod
    def build_unified_prompt(
        facts_ledger: str = "",
        stage: str = "Stage 1: Greeting & Identify Caller",
        next_field: str = "",
        language_code: str = "en-IN",
        conversation_history: str = "",
        system_base: str = ""
    ) -> str:
        """
        Build ONE unified prompt where language is a substituted variable.
        Facts ledger, session history, and stage are NEVER wiped or swapped on language change.
        """
        code = LanguageHandler.normalize_language(language_code)
        lang_style = LanguageHandler.get_language_style(code)

        base = (system_base.strip() if system_base else CORE_IDENTITY_AND_RULES.strip())

        parts = [base]
        if facts_ledger and facts_ledger.strip() != "None yet":
            parts.append(f"\n# KNOWN FACTS LEDGER (do NOT re-ask anything listed here):\n{facts_ledger.strip()}")
        if stage:
            parts.append(f"\n# CURRENT STAGE: {stage}")
        if next_field:
            parts.append(f"# OBJECTIVE / FIELD TO COLLECT THIS TURN: {next_field}")
        if conversation_history:
            parts.append(f"\n# RECENT CONVERSATION CONTEXT:\n{conversation_history.strip()}")

        parts.append(f"\n# LANGUAGE STYLE (respond in this language — all facts & rules above still apply):\n{lang_style}")
        return "\n".join(parts)

    @staticmethod
    def get_language_prompt(language_code: str) -> str:
        """
        Get prompt for language. Uses unified prompt architecture so facts/rules are never lost.
        """
        code = LanguageHandler.normalize_language(language_code)
        return LanguageHandler.build_unified_prompt(language_code=code)

    # Backward-compatible alias
    get_llm_instruction = get_language_prompt

    @classmethod
    def match_language(
        cls,
        stt_detected_language: Optional[str] = None,
        transcript_text: Optional[str] = None,
        current_language: str = "en-IN"
    ) -> str:
        """
        Match caller's language with zero-hysteresis turn-by-turn mirroring.
        Priority:
        1. Explicit language switch requests (100% priority)
        2. Direct script detection (Telugu, Devanagari, Tamil)
        3. Romanized keywords / indicators
        4. STT language detection (if non-default)
        5. Neutral confirmations (keep current conversation language)
        6. Default English
        """
        if transcript_text and transcript_text.strip():
            t = transcript_text.strip()
            t_low = t.lower()
            clean_lower = re.sub(r'[^a-zA-Z0-9\s]', '', t_low).strip()

            # 1. Explicit Switch Request (Highest Priority)
            if re.search(r'\b(speak in english|in english|english please|english lo|english mein|english la)\b', t_low):
                return "en-IN"
            if re.search(r'\b(hindi mein|hindi me|hindi please|hindi bol|hindi baat|hindi lo)\b', t_low):
                return "hi-IN"
            if re.search(r'\b(telugu lo|telugu please|telugu matladu|telugu cheppu)\b', t_low):
                return "te-IN"
            if re.search(r'\b(tamil la|tamil please|tamil pesu)\b', t_low):
                return "ta-IN"

            # 2. Maintain active language on neutral words like "yes", "okay", "sure"
            if clean_lower in cls._NEUTRAL_WORDS and current_language:
                return current_language

            # 3. Direct Unicode script detection
            if cls._TELUGU_SCRIPT.search(t):
                return "te-IN"
            if cls._HINDI_SCRIPT.search(t):
                return "hi-IN"
            if cls._TAMIL_SCRIPT.search(t):
                return "ta-IN"

        # 4. Check STT detected language (resolves code-mixing when Romanized text is ambiguous)
        if stt_detected_language and stt_detected_language.lower().strip() not in ("unknown", ""):
            code = cls.normalize_language(stt_detected_language)
            if code:
                return code

        if transcript_text and transcript_text.strip():
            t = transcript_text.strip()
            # 5. Romanized dialect keywords
            if cls._TELUGU_WORDS.search(t):
                return "te-IN"
            if cls._HINDI_WORDS.search(t):
                return "hi-IN"
            if cls._TAMIL_WORDS.search(t):
                return "ta-IN"

            # 6. English phrasing detection
            if cls._ENGLISH_WORDS.search(t):
                return "en-IN"

        return current_language or "en-IN"


class SessionMemory:
    """
    Session memory keyed strictly by session_id.
    Maintains facts ledger, conversation history, and stage across mid-call language switches.
    """

    def __init__(self, session_id: str = "call_default"):
        self.session_id = session_id
        self.conversation_history: List[Dict[str, Any]] = []
        self.facts_ledger: Dict[str, Any] = {}
        self.current_language: str = "en-IN"
        self.current_stage: str = "Stage 1: Greeting & Identify Caller"
        self.pending_field: str = "student_name"

    def set_fact(self, key: str, value: Any):
        """Record or update a fact in the ledger."""
        if value is not None and str(value).strip():
            self.facts_ledger[key] = str(value).strip()

    def get_fact(self, key: str) -> Optional[Any]:
        """Get a fact from the ledger."""
        return self.facts_ledger.get(key)

    def get_facts_ledger_str(self) -> str:
        """Get formatted string of known facts."""
        if not self.facts_ledger:
            return "None yet"
        return "\n".join(f"• {k}: {v}" for k, v in self.facts_ledger.items())

    def add_turn(self, transcript: str, response: str, language_used: str):
        """Add conversation turn and auto-update facts and stage."""
        self.conversation_history.append({
            "transcript": transcript,
            "response": response,
            "language": language_used
        })
        self.current_language = language_used
        self._extract_facts_from_turn(transcript)

    def _extract_facts_from_turn(self, text: str):
        """Auto-extract basic slots into facts_ledger."""
        if not text:
            return
        t_low = text.lower()

        # Check name
        m_name = re.search(r'\b(?:my name is|i am|this is|name is|peru|naam)\s+([A-Za-z]+)', text, re.I)
        if m_name and "student_name" not in self.facts_ledger:
            cand = m_name.group(1).title()
            if cand.lower() not in {"interested", "calling", "speaking", "here", "fine"}:
                self.facts_ledger["student_name"] = cand
                self.current_stage = "Stage 2: Program & Course Interest"
                self.pending_field = "program"

        # Check program with word boundaries
        if re.search(r'\b(cse|computer science|ai/ml|data science|ece|eee|mech|civil|mba|bba|pharmacy)\b', t_low) or re.search(r'\b(ai|ml)\b', t_low):
            if re.search(r'\b(cse|computer science)\b', t_low):
                self.facts_ledger["program"] = "B.Tech CSE"
            elif re.search(r'\b(ai|ml|data science|ai/ml)\b', t_low):
                self.facts_ledger["program"] = "B.Tech AI/ML"
            elif re.search(r'\b(ece)\b', t_low):
                self.facts_ledger["program"] = "B.Tech ECE"
            elif re.search(r'\b(mba)\b', t_low):
                self.facts_ledger["program"] = "MBA"
            elif re.search(r'\b(pharmacy)\b', t_low):
                self.facts_ledger["program"] = "Pharmacy"
            elif re.search(r'\b(bba)\b', t_low):
                self.facts_ledger["program"] = "BBA"
            elif "program" not in self.facts_ledger:
                self.facts_ledger["program"] = "B.Tech"
            self.current_stage = "Stage 3: Academic Background & Eligibility"
            self.pending_field = "marks_12"

        # Check score
        m_score = re.search(r'(\d{2}(?:\.\d+)?)\s*%', text)
        if m_score:
            self.facts_ledger["marks_12"] = f"{m_score.group(1)}%"
            self.current_stage = "Stage 4: Consultative Value Pitch & Close"
            self.pending_field = "campus_visit"

        # Check exams with word boundaries
        if re.search(r'\b(jee|jee main|jee mains)\b', t_low):
            self.facts_ledger["entrance_exam"] = "JEE Main"
        elif re.search(r'\b(eamcet|eapcet|ap eamcet|ap eapcet)\b', t_low):
            self.facts_ledger["entrance_exam"] = "AP EAPCET"
        elif re.search(r'\b(asat)\b', t_low):
            self.facts_ledger["entrance_exam"] = "ASAT"

    def get_context(self, max_turns: int = 5) -> str:
        """Get conversation context for LLM."""
        recent = self.conversation_history[-max_turns:]
        if not recent:
            return ""
        return "\n".join([
            f"Turn {i+1} ({turn['language']}): Caller: '{turn['transcript']}' -> Priya: '{turn['response']}'"
            for i, turn in enumerate(recent)
        ])


# Shorthand mapping and instructions
LANGUAGE_INSTRUCTIONS = {
    "en-IN": "Respond in ENGLISH only. Keep <25 words. Be helpful.",
    "hi-IN": "HINDI में ONLY जवाब दें। जवाब 25 शब्दों से कम रखें।",
    "te-IN": "TELUGU లో ONLY జవాబ్ ఇవ్వండి। 25 పదాల కంటే తక్కువ.",
    "ta-IN": "TAMIL இல் ONLY பதிலளிக்கவும். 25 சொற்களுக்குக் குறைவாக.",
}


def get_language_code(stt_language: Optional[str]) -> str:
    """Convert STT language to standard code."""
    return LanguageHandler.normalize_language(stt_language)


# Quick test
if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    # Test language normalization
    test_inputs = ["english", "hindi", "telugu", "tamil", "en", "hi", "te", "ta"]
    for inp in test_inputs:
        output = LanguageHandler.normalize_language(inp)
        print(f"{inp:15} -> {output}")
