"""
Session Context and Conversation State Management for Priya Admissions Voice Agent.

Handles:
- In-memory turn history tracking with bounded context window (cuts LLM tokens by ~80%)
- Question de-duplication to prevent repetitive queries
- Multilingual goodbye / wrap-up intent detection
- Collected field tracking and session serialization
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

try:
    from azure_store import AZURE_COSMOS_STORE
except ImportError:
    AZURE_COSMOS_STORE = None

from conversation_history import ConversationHistory
from long_conversation import LongConversationManager

logger = logging.getLogger("priya.session")


@dataclass
class ConversationTurn:
    role: str                       # 'user' | 'assistant' | 'system'
    text: str
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0        # STT confidence (0.0 to 1.0)
    language: str = "en-IN"


# Multilingual goodbye & closing phrase regexes
_GOODBYE_PATTERNS = [
    # English
    r'\b(thank\s*you|thanks|bye|goodbye|that(\'?s|\s+is)\s+(all|it|enough)|nothing\s+else|have\s+a\s+good\s+day|talk\s+to\s+you\s+later|see\s+you)\b',
    # Hindi
    r'(धन्यवाद|शुक्रिया|अलविदा|नमस्ते|ठीक\s*है\s*(धन्यवाद|शुक्रिया|bye)?|बस\s*(इतना\s*ही|काफी\s*है)|और\s*कुछ\s*नहीं|बाय)',
    # Telugu
    r'(ధన్యవాదాలు|థాంక్స్|చాలు|ఇక\s*చాలు|సరే\s*(థాంక్స్|ధన్యవాదాలు)|మళ్ళీ\s*మాట్లాడతాను|బై)',
    # Tamil
    r'(நன்றி|போதும்|வணக்கம்|பை)',
]
_GOODBYE_RE = re.compile("|".join(_GOODBYE_PATTERNS), re.IGNORECASE)

# Question topic keys for de-duplication
QUESTION_TOPIC_KEYS = {
    "program_interest": ["program", "course", "branch", "specializ", "degree"],
    "student_name": ["name", "naam", "peru", "caller"],
    "entrance_exam": ["exam", "entrance", "asat", "jee", "eapcet", "score", "rank"],
    "campus_visit": ["visit", "campus", "aana", "date", "time", "ravadam"],
    "city": ["city", "native", "location", "place", "ikkada", "kahan"],
}


def is_garbled_input(text: str, confidence: float = 1.0) -> bool:
    """Check if user input is garbled noise or low confidence STT."""
    if not text or not text.strip():
        return True
    if confidence < 0.65:
        return True
    words = text.strip().split()
    if len(words) >= 4 and len(set(words)) == 1:
        return True
    return False


def is_valid_user_speech(transcript: str, min_chars: int = 1) -> bool:
    """
    Validates STT transcript against noise bursts, breathing, coughs, and artifacts.
    Rejects non-speech noise so Priya never gets falsely interrupted.
    Supports genuine short words ('Yes', 'No', 'Wait', 'Stop', 'Haan', 'Sare').
    """
    if not transcript or not transcript.strip():
        return False
    clean = transcript.strip().lower()
    junk_patterns = {
        "", "[noise]", "[music]", "[silence]", "[cough]", "[laughter]", 
        "[applause]", "[sigh]", "[snort]", "[pant]", "[throat-clearing]",
        "...", ".", "..", "?", "!", "-", "--", "---", "*", "_", "mhm", "uh", "um"
    }
    if clean in junk_patterns:
        return False
    # Ensure there is at least one alphanumeric or Indian-script character (Hindi, Telugu, Tamil, etc.)
    if not re.search(r'[a-zA-Z0-9\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF]', clean):
        return False
    return True


class SessionContext:
    """Represents a single active caller session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.start_time: float = time.time()
        self.turns: List[ConversationTurn] = []
        self.collected: Dict[str, str] = {}
        self.history: ConversationHistory = ConversationHistory(call_id=session_id)
        self.long_mgr: LongConversationManager = LongConversationManager(call_id=session_id)
        self.questions_asked: Set[str] = self.history.questions_asked
        self.topics_discussed: Set[str] = set()
        self.is_closed: bool = False
        self.goodbye_detected: bool = False
        self.active_language: str = "en-IN"

    def add_turn(self, role: str, text: str, confidence: float = 1.0, language: str = "en-IN") -> ConversationTurn:
        """Record one conversation turn."""
        if not text or not text.strip():
            return None
        turn = ConversationTurn(
            role=role,
            text=text.strip(),
            timestamp=time.time(),
            confidence=confidence,
            language=language or self.active_language,
        )
        self.turns.append(turn)
        if language:
            self.active_language = language

        # Forward turn to 4-Layer Long Conversation Manager
        if hasattr(self, "long_mgr") and self.long_mgr:
            if role == "user":
                self.long_mgr.record_turn(user_text=text.strip(), role="user", language=language or self.active_language)
                # Sync facts extracted by long_mgr to self.collected
                for k, v in self.long_mgr.get_facts().items():
                    if v and not self.collected.get(k):
                        self.collected[k] = str(v)
            elif role == "assistant":
                self.long_mgr.record_turn(agent_text=text.strip(), role="assistant", language=language or self.active_language)
            # Sync topics discussed
            self.topics_discussed.update(self.long_mgr.history.topics_discussed)

        # Forward turn to ConversationHistory for complete context retention
        if hasattr(self, "history") and self.history:
            if role == "user":
                self.history.add_turn(text.strip(), "", language=language or self.active_language)
                for k, v in self.history.facts.items():
                    if v and not self.collected.get(k):
                        self.collected[k] = str(v)
            elif role == "assistant":
                if self.history.turns and not self.history.turns[-1].get("agent"):
                    self.history.turns[-1]["agent"] = text.strip()
                    self.history.turns[-1]["agent_response"] = text.strip()
                else:
                    self.history.add_turn("", text.strip(), language=language or self.active_language)

        # If assistant asked something, record question category
        if role == "assistant" and "?" in text:
            self._record_asked_questions(text)

        # Sync turn to Azure Cosmos DB in background (non-blocking)
        if AZURE_COSMOS_STORE and AZURE_COSMOS_STORE.enabled:
            AZURE_COSMOS_STORE.save_turn_async(
                session_id=self.session_id,
                turn_number=len(self.turns),
                speaker=role,
                text=text,
                language=language or self.active_language,
                confidence=confidence,
            )

        return turn

    def _record_asked_questions(self, text: str):
        """Infer and record question category from assistant utterance."""
        t_low = text.lower()
        for q_key, keywords in QUESTION_TOPIC_KEYS.items():
            if any(k in t_low for k in keywords):
                self.questions_asked.add(q_key)
                if hasattr(self, "history") and self.history:
                    self.history.record_question_asked(q_key)
                if hasattr(self, "long_mgr") and self.long_mgr:
                    self.long_mgr.mark_topic_discussed(q_key)

    def mark_question_asked(self, question_key: str):
        """Explicitly record a question as asked."""
        self.questions_asked.add(question_key)
        if hasattr(self, "history") and self.history:
            self.history.record_question_asked(question_key)
        if hasattr(self, "long_mgr") and self.long_mgr:
            self.long_mgr.mark_topic_discussed(question_key)

    def is_question_redundant(self, question_key: str) -> bool:
        """Check if this topic / question has already been answered or asked."""
        if hasattr(self, "long_mgr") and self.long_mgr:
            if not self.long_mgr.should_ask_about(question_key):
                return True
        if hasattr(self, "history") and self.history:
            if not self.history.should_ask_question(question_key):
                return True

        # If we already have the collected data, it's redundant
        if question_key == "program_interest" and (self.collected.get("program_of_interest") or self.collected.get("specialization") or self.collected.get("program")):
            return True
        if question_key == "student_name" and (self.collected.get("student_name") or self.collected.get("name")):
            return True
        if question_key in ("entrance_exam", "exam") and (self.collected.get("entrance_exams_taken") or self.collected.get("exam")):
            return True
        if question_key in ("score", "academic_score", "class_12_score") and (self.collected.get("class_12_score") or self.collected.get("class_10_score") or self.collected.get("score")):
            return True
        if question_key in ("city", "location") and (self.collected.get("current_city") or self.collected.get("city")):
            return True
        if question_key == "campus_visit" and self.collected.get("visit_datetime"):
            return True
        return question_key in self.questions_asked

    def record_topic(self, topic: str):
        """Mark a domain topic (FEES, SCHOLARSHIPS, etc.) as discussed."""
        if topic:
            self.topics_discussed.add(topic.upper())
            if hasattr(self, "long_mgr") and self.long_mgr:
                self.long_mgr.mark_topic_discussed(topic)

    def was_topic_discussed(self, topic: str) -> bool:
        """Check if a topic has already been covered in this call."""
        if hasattr(self, "long_mgr") and self.long_mgr:
            if self.long_mgr.has_topic_been_discussed(topic):
                return True
        return topic.upper() in self.topics_discussed

    def get_last_n_turns(self, n: int = 5) -> List[ConversationTurn]:
        """Return the most recent N turns for LLM context (avoids context bloat)."""
        return self.turns[-n:] if len(self.turns) > n else self.turns

    def detect_goodbye(self, text: str) -> bool:
        """Check if user text indicates call wrap-up / goodbye."""
        if not text:
            return False
        if hasattr(self, "long_mgr") and self.long_mgr:
            if self.long_mgr.detect_goodbye(text):
                self.goodbye_detected = True
                return True
        clean = text.strip()
        # Short turns like "Thank you", "ठीक है", "Bye"
        if len(clean.split()) <= 6 and _GOODBYE_RE.search(clean):
            self.goodbye_detected = True
            return True
        return False

    def close(self):
        """Mark session as ended."""
        self.is_closed = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state for logging / CRM storage."""
        data = {
            "session_id": self.session_id,
            "duration_sec": round(time.time() - self.start_time, 2),
            "total_turns": len(self.turns),
            "collected": self.collected,
            "questions_asked": list(self.questions_asked),
            "topics_discussed": list(self.topics_discussed),
            "active_language": self.active_language,
            "is_closed": self.is_closed,
        }
        if hasattr(self, "long_mgr") and self.long_mgr:
            data["dialogue_state"] = self.long_mgr.state.state
            data["facts"] = self.long_mgr.get_facts()
            data["sliding_window_turns"] = len(self.long_mgr.sliding_window.get_turns())
        return data


class SessionStore:
    """In-memory thread-safe registry of active sessions."""

    def __init__(self):
        self._sessions: Dict[str, SessionContext] = {}
        self._archive: Dict[str, Dict[str, Any]] = {}

    def get_or_create(self, session_id: str) -> SessionContext:
        if not session_id:
            session_id = f"sess_{int(time.time() * 1000)}"
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionContext(session_id)
            logger.info(f"[SESSION] Created new session: {session_id}")
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[SessionContext]:
        return self._sessions.get(session_id)

    def archive(self, session_id: str):
        if session_id in self._sessions:
            ctx = self._sessions.pop(session_id)
            ctx.close()
            summary_dict = ctx.to_dict()
            self._archive[session_id] = summary_dict
            logger.info(f"[SESSION] Archived session: {session_id} ({len(ctx.turns)} turns)")
            if AZURE_COSMOS_STORE and AZURE_COSMOS_STORE.enabled:
                AZURE_COSMOS_STORE.save_session_complete_async(summary_dict)

    def active_count(self) -> int:
        return len(self._sessions)


# Global singleton instance
GLOBAL_SESSION_STORE = SessionStore()


class DialogueSlotManager:
    """Extracts student profile details and conversation slots from caller speech."""

    EXAM_PATTERNS = {
        "JEE": r'\b(jee|jee\s*mains?|jee\s*advanced|iit)\b',
        "AP_EAPCET": r'\b(ap\s*eapcet|ap\s*eamcet|eapcet|eamcet|apeapcet|apeamcet)\b',
        "TS_EAMCET": r'\b(ts\s*eamcet|ts\s*eapcet|tseamcet|tseapcet)\b',
        "ASAT": r'\b(asat|aditya\s*scholarship|aditya\s*entrance)\b',
        "CUET": r'\b(cuet|common\s*entrance)\b',
        "NEET": r'\b(neet)\b',
        "CAT": r'\b(cat)\b',
        "MAT": r'\b(mat)\b',
        "NMAT": r'\b(nmat)\b',
        "ICET": r'\b(icet|apicet|tsicet)\b',
    }

    SCORE_PATTERNS = [
        r'(\d{1,2}(?:\.\d+)?)\s*(?:percent|%|percentage)',
        r'(?:scored|got|have|marks|marks\s*(?:are|is)?|score\s*(?:is)?)\s*(\d{1,2}(?:\.\d+)?)',
        r'(\d{1,2}(?:\.\d+)?)\s*(?:in\s*(?:12th|inter|intermediate|board|cbse|bie))',
    ]

    PROGRAM_PATTERNS = {
        "B.Tech CSE": r'\b(cse|computer\s*science|cs|computer\s*engineering)\b|కంప్యూటర్\s*సైన్స్|कंप्यूटर\s*साइंस',
        "B.Tech AI/ML": r'\b(aiml|ai\s*ml|ai\s*and\s*ml|ai&ml|artificial\s*intelligence|machine\s*learning)\b|ఏఐ|आर्टिफिशियल',
        "B.Tech CSE (Data Science)": r'\b(data\s*science|cse\s*data\s*science|ds)\b|డేటా\s*సైన్స్|डेटा\s*साइंस',
        "B.Tech ECE": r'\b(ece|electronics|electronics\s*and\s*communication)\b|ఈసీఈ|इलेक्ट्रॉनिक्स',
        "B.Tech EEE": r'\b(eee|electrical|electrical\s*and\s*electronics)\b|ఈఈఈ|इलेक्ट्रिकल',
        "B.Tech Mechanical": r'\b(mech|mechanical|mechanical\s*engineering)\b|మెకానికల్|मैकेनिकल',
        "B.Tech Civil": r'\b(civil|civil\s*engineering)\b|సివిల్|सिविल',
        "B.Tech Agricultural": r'\b(agri|agriculture|agricultural|agricultural\s*engineering)\b|అగ్రికల్చర్|एग्रीकल्चर',
        "B.Tech Petroleum": r'\b(petro|petroleum|petroleum\s*technology)\b|పెట్రోలియం|पेट्रोलियम',
        "B.Tech Mining": r'\b(mining|mining\s*engineering)\b|మైనింగ్|माइनिंग',
        "MBA": r'\b(mba|management|master\s*of\s*business)\b',
        "BBA": r'\b(bba|bachelor\s*of\s*business)\b',
        "Pharmacy": r'\b(pharmacy|pharm|b\.?pharm|b\.?pharmacy|pharm\.?\s*d)\b|ఫార్మసీ|फार्मेसी',
        "MCA": r'\b(mca|master\s*of\s*computer)\b',
        "BCA": r'\b(bca|bachelor\s*of\s*computer)\b',
    }

    CITY_PATTERNS = [
        r'(?:from|live\s*in|living\s*in|stay\s*in|staying\s*in|native\s*(?:is|place\s*is)?|location\s*(?:is)?)\s+([A-Za-z]{3,20})',
        r'([A-Za-z]{3,20})\s+(?:lo\s*untunnanu|lo\s*untamu|lo\s*unta|nunchi|se\s*bol\s*raha|se\s*hoon|se\s*hu)',
    ]

    INVALID_NAMES = {
        "interested", "admission", "calling", "student", "good", "fine", "asking",
        "looking", "inquiring", "checking", "wondering", "telling", "trying", "here",
        "just", "now", "not", "talking", "with", "from", "in", "at", "for", "about",
        "platform", "first", "which", "what", "how", "why", "where", "you", "me",
        "done", "doing", "passed", "studying", "yes", "yeah", "yep", "no", "nah",
        "okay", "ok", "sure", "fine", "hello", "hi", "hey", "alright", "sare", "theek",
        "like", "that", "this", "there", "then", "want", "visit", "visiting", "book",
        "feel", "feeling", "role", "position", "treasury", "thunder", "situation", "status",
        "know", "knowing", "tell", "said", "say", "saying", "actually", "right", "wrong",
        "these", "those", "some", "any", "every"
    }

    INVALID_CITIES = {
        "like", "that", "this", "here", "there", "then", "now", "just", "want", "visit",
        "visiting", "tell", "telling", "asking", "college", "school", "university",
        "campus", "aditya", "engineering", "btech", "cse", "admission", "student",
        "home", "house", "room", "hostel", "interested", "good", "fine", "yes", "sure",
        "okay", "ok", "alright", "morning", "afternoon", "evening", "today", "tomorrow"
    }

    @classmethod
    def extract_slots(cls, text: str, current_slots: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract all details from user's message.
        Called EVERY TURN before LLM is invoked.
        """
        current_dict = dict(current_slots) if isinstance(current_slots, dict) else {}
        if not text:
            return current_dict

        updated = dict(current_dict)
        t_low = text.lower().strip()

        # Detect explicit correction intent
        is_correction = bool(re.search(r'\b(actually|sorry|not|no|instead|correction|galti\s*se|change|kaadhu|nenu\s*kaadu)\b', t_low))

        # 1. EXTRACT SCORES (supports corrections like 'Actually I scored 82%')
        for pattern in cls.SCORE_PATTERNS:
            match = re.search(pattern, t_low)
            if match:
                try:
                    score_val = float(match.group(1))
                    if 35.0 <= score_val <= 100.0:
                        old_score = updated.get("class_12_score")
                        updated["class_12_score"] = f"{score_val}%"
                        if is_correction and old_score and old_score != f"{score_val}%":
                            logger.info(f"[CORRECTION] Updated score from {old_score} to {score_val}%")
                        else:
                            logger.info(f"[SLOT] Extracted score: {score_val}%")
                        break
                except (ValueError, IndexError):
                    pass

        # 2. EXTRACT ENTRANCE EXAMS
        for exam_name, pattern in cls.EXAM_PATTERNS.items():
            if re.search(pattern, t_low):
                current_exams = updated.get("entrance_exams_taken", "")
                if exam_name not in current_exams:
                    updated["entrance_exams_taken"] = f"{current_exams}, {exam_name}".strip(", ")
                    logger.info(f"[SLOT] Extracted exam: {exam_name}")

        # 3. EXTRACT PROGRAMS (supports corrections like 'Actually I want AI/ML')
        for prog_name, pattern in cls.PROGRAM_PATTERNS.items():
            if re.search(pattern, t_low) or re.search(pattern, text):
                if is_correction or not updated.get("program_of_interest"):
                    old_prog = updated.get("program_of_interest")
                    updated["program_of_interest"] = prog_name
                    if is_correction and old_prog and old_prog != prog_name:
                        logger.info(f"[CORRECTION] Updated program from {old_prog} to {prog_name}")
                    else:
                        logger.info(f"[SLOT] Extracted program: {prog_name}")
                    break

        # 4. EXTRACT NAMES & SUPPORT CORRECTIONS
        explicit_match = re.search(
            r'(?:my\s*name\s*is|myself|i\s*am|i\'m|this\s*is|call\s*me|naa\s*peru|mera\s*naam|naam|peru)\s*[:=]?\s*([^\W\d_]+(?:\s+[^\W\d_]+)?)(?:,?\s*(?:not|no|lekapothe)\s*([^\W\d_]+)?)?',
            text,
            re.UNICODE | re.IGNORECASE
        )
        if not explicit_match:
            explicit_match = re.search(
                r'\bnot\s+[^\W\d_]+,?\s*(?:my\s*name\s*is|i\s*am|i\'m|it\'s|its|call\s*me)\s+([^\W\d_]+)',
                text,
                re.UNICODE | re.IGNORECASE
            )

        if explicit_match:
            candidate = explicit_match.group(1).strip()
            parts = candidate.split()
            if len(parts) > 1 and parts[-1].lower() in {"and", "aur", "ani", "from", "here", "speaking", "calling", "interested", "looking", "for", "to", "in", "is", "not", "no"}:
                candidate = parts[0]
            cand_low = candidate.lower()
            if (
                len(candidate) >= 2
                and cand_low not in cls.INVALID_NAMES
                and not any(w in cls.INVALID_NAMES for w in cand_low.split())
                and not cand_low.endswith("ing")
            ):
                # Explicit statement or correction overrides any previous slot guess
                old_name = updated.get("student_name")
                updated["student_name"] = candidate
                if old_name and old_name != candidate:
                    logger.info(f"[CORRECTION] Updated name from {old_name} to {candidate}")
                else:
                    logger.info(f"[SLOT] Extracted explicit/corrected name: {candidate}")
        elif not updated.get("student_name") and not updated.get("program_of_interest") and len(text.strip().split()) in (1, 2, 3):
            # Standalone candidate
            cand = text.strip().strip(".,!?:;\"'")
            cand_low = cand.lower()
            words = [w.strip(".,!?:;\"'") for w in cand_low.split()]
            if (
                cand
                and not re.search(r'\d', cand)
                and cand_low not in cls.INVALID_NAMES
                and not any(w in cls.INVALID_NAMES for w in words)
                and not re.search(r'\b(btech|b\.tech|cse|ece|fee|fees|hostel|campus|visit|college|aditya|scholarship|exam|marks)\b', cand_low)
                and not cand_low.endswith("ing")
            ):
                updated["student_name"] = cand
                logger.info(f"[SLOT] Extracted standalone name: {cand}")

        # 5. EXTRACT CITY / LOCATION
        if is_correction or not updated.get("current_city"):
            for c_pat in cls.CITY_PATTERNS:
                c_match = re.search(c_pat, t_low, re.IGNORECASE)
                if c_match:
                    city_candidate = c_match.group(1).capitalize()
                    if city_candidate.lower() not in cls.INVALID_NAMES and city_candidate.lower() not in cls.INVALID_CITIES:
                        updated["current_city"] = city_candidate
                        logger.info(f"[SLOT] Extracted city: {city_candidate}")
                        break

        # 6. EXTRACT COLLEGE / SCHOOL
        if is_correction or not updated.get("college"):
            college_match = re.search(
                r'(?:studied\s*in|completed\s*in|from|at|in)?\s*([A-Za-z0-9\s]{2,25}?)\s+(?:junior\s*college|college|polytechnic|institute)',
                t_low,
                re.IGNORECASE
            )
            if college_match:
                raw_cand = college_match.group(1).strip()
                # Clean leading prepositions
                raw_cand = re.sub(r'^(from|at|in|my|the|\d+(?:th)?)\s+', '', raw_cand, flags=re.I).strip()
                if raw_cand and len(raw_cand) >= 2 and raw_cand.lower() not in cls.INVALID_NAMES and raw_cand.lower() not in cls.INVALID_CITIES:
                    college_cand = raw_cand.title() + " College"
                    updated["college"] = college_cand
                    logger.info(f"[SLOT] Extracted college: {college_cand}")

        return updated

    @classmethod
    def detect_already_told(cls, text: str, slots: Dict[str, Any]) -> Optional[str]:
        """
        Detects if caller is reacting to a redundant question:
        e.g. 'I already told you my name', 'Maine already apna course bataya tha'
        Returns a friendly acknowledgment referencing the known fact.
        """
        if not text:
            return None
        t_low = text.lower()
        if re.search(r'\b(already\b.*?\b(told|said|gave|mentioned|bataya|bola|cheppanu|cheppa)|i\s*told\s*you|cheppanu\s*kada|already\s*cheppa)\b', t_low):
            name = slots.get("student_name") or slots.get("name")
            prog = slots.get("program_of_interest") or slots.get("program")
            marks = slots.get("class_12_score") or slots.get("marks")

            # Check what they're referring to
            if any(w in t_low for w in ["name", "naam", "peru"]) and name:
                return f"You're right, {name}! Let's continue."
            elif any(w in t_low for w in ["course", "program", "branch", "cse", "btech"]) and prog:
                return f"Yes, you mentioned {prog}. Let's proceed."
            elif any(w in t_low for w in ["marks", "percentage", "score", "percent"]) and marks:
                return f"Yes, {marks} in 12th! Let's continue."
            elif name:
                return f"You're right, {name}! My apologies, let's move ahead."
            else:
                return "You're right, let's continue."
        return None

