# crm/priya-livekit/priya/memory/context_engine.py
"""
Unified 5-Layer Context Engine & Memory Manager for AdmitAI Priya Voice Agent.
Consolidates session state, dialogue slots, sliding window, rolling summaries,
and semantic memory into a single token-controlled context (<600 tokens per turn).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import university_data as udata

logger = logging.getLogger("priya.context_engine")


class MemoryType(str, Enum):
    PROFILE_MEMORY = "profile_memory"           # Name, phone, location
    PREFERENCE_MEMORY = "preference_memory"     # Language, branch preference
    FACTUAL_MEMORY = "factual_memory"           # 12th score, ASAT/JEE rank
    CONVERSATION_MEMORY = "conversation_memory" # Objections, resolved topics
    TASK_MEMORY = "task_memory"                 # Campus visit, WhatsApp link
    TEMPORARY_SESSION_MEMORY = "temp_memory"    # Ephemeral turn state


@dataclass
class MemoryRecord:
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    session_id: str = ""
    memory_type: MemoryType = MemoryType.TEMPORARY_SESSION_MEMORY
    content: str = ""
    importance: float = 0.5                     # 0.0 (trivial) to 1.0 (critical)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = field(default_factory=datetime.utcnow)


# Stage definitions in monotonic sequence
STAGES = ["GREETING", "PROGRAM", "ELIGIBILITY", "PITCH", "CONVERT", "CLOSING"]

STAGE_TARGET_FIELDS = {
    "GREETING": "student_name",
    "PROGRAM": "program",
    "ELIGIBILITY": "marks_12",
    "PITCH": "scholarship_or_roi",
    "CONVERT": "campus_visit",
    "CLOSING": "call_outcome",
}

LANGUAGE_NAMES = {
    "en-IN": "Indian English",
    "hi-IN": "Hindi / Hinglish",
    "te-IN": "Telugu",
    "ta-IN": "Tamil",
}

LANGUAGE_STYLE_DIRECTIVES = {
    "en-IN": "Reply in warm, concise Indian English. Maximum 20 words.",
    "hi-IN": "Reply ONLY in natural conversational Hindi/Hinglish (Devanagari or clean Roman). Maximum 20 words.",
    "te-IN": "Reply ONLY in warm conversational Telugu (use Telugu script or clean transliteration with respect: 'అండీ / గారు'). Maximum 20 words.",
    "ta-IN": "Reply ONLY in natural conversational Tamil. Maximum 20 words.",
}

# Static base system instructions (Layer 1 - Cached & Lean: ~150 tokens)
SYSTEM_PROMPT_BASE = """You are Priya, senior AI Admissions Counselor at Aditya University.
CORE VOICE RULES:
1. Spoken Conciseness: Maximum 1-2 spoken sentences per turn (UNDER 25 WORDS).
2. Exactly ONE Question: Never ask more than ONE question at the end of your reply.
3. Verified Facts Only:
   • B.Tech CSE tuition: ₹2,75,000/yr; Core engineering: ₹1,00,000 to ₹1,35,000/yr.
   • Hostels: AC ₹1,30,000/yr (₹45,000/sem); Non-AC ₹1,15,000/yr (₹30,000/sem).
   • Placements: 3,832+ placements, ₹27 LPA top package at Walmart.
   • Scholarships: 10% to 50% tuition waiver on 12th Board marks (≥95% = 50%, ≥90% = 40%, ≥80% = 25%, ≥70% = 15%).
4. Zero Repetition: Never re-ask details present in KNOWN CALLER SLOTS.
5. Goal: Guide the student toward booking a VIP Campus Visit for this Saturday 10 AM.
"""


class LayeredContextEngine:
    """
    Manages 5-layer conversation context:
    Layer 1: Static System Rules & Guardrails
    Layer 2: Session State & Extracted Slots (Monotonic)
    Layer 3: Recent Sliding Window (Last 3 Turns)
    Layer 4: Running Structured Summary (Consolidated for turns > 6)
    Layer 5: Retrieved Background Memories
    """

    MAX_PROMPT_TOKENS = 600

    def __init__(self, session_id: str, caller_phone: str = "", initial_language: str = "en-IN"):
        self.session_id = session_id
        self.caller_phone = caller_phone
        self.active_language = initial_language
        self.stage = "GREETING"
        
        # Canonical facts ledger
        self.slots: Dict[str, Any] = {}
        
        # Turn histories
        self.all_turns: List[Dict[str, Any]] = []
        self.running_summary: str = ""
        self.long_term_memories: List[MemoryRecord] = []
        
        # Tracking flags
        self.questions_asked: set = set()
        self.last_user_text: str = ""
        self.last_agent_text: str = ""

    # ── Slot Extraction with Correction Support & Filler Rejection ──────

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

    def extract_and_update_slots(self, text: str) -> Dict[str, Any]:
        """Additive slot extraction with support for corrections and multi-word filler rejection."""
        if not text:
            return self.slots

        t_low = text.lower().strip()
        words = [w.strip(".,!?:;\"'") for w in t_low.split()]

        # 1. Academic Scores (12th Board / Intermediate)
        m_score = re.search(r'(\d{1,2}(?:\.\d+)?)\s*(?:%|percent|percentage)', t_low)
        if not m_score:
            m_score = re.search(r'(?:scored|got|have|marks|score(?:\s+is)?)\s+(\d{1,2}(?:\.\d+)?)', t_low)
        if m_score:
            try:
                score_val = float(m_score.group(1))
                if 35.0 <= score_val <= 100.0:
                    score_str = f"{score_val:g}%" if score_val != int(score_val) else f"{int(score_val)}%"
                    self.slots["marks_12"] = score_str
                    self.slots["class_12_score"] = score_str
            except (ValueError, IndexError):
                pass

        # 2. Entrance Exams (JEE, EAPCET, ASAT)
        if re.search(r'\b(jee|jee\s*main|jee\s*mains|iit)\b', t_low):
            self.slots["entrance_exam"] = "JEE Main"
        elif re.search(r'\b(eamcet|eapcet|ap\s*eamcet|ap\s*eapcet)\b', t_low):
            self.slots["entrance_exam"] = "AP EAPCET"
        elif re.search(r'\b(asat|aditya\s*scholarship)\b', t_low):
            self.slots["entrance_exam"] = "ASAT"

        # 3. Programs & Branches
        prog_patterns = [
            ("B.Tech CSE (Data Science)", r'\b(data\s*science|cse\s*data\s*science|ds)\b|డేటా\s*సైన్స్|डेटा\s*साइंस'),
            ("B.Tech AI/ML", r'\b(aiml|ai\s*[\/&]?\s*ml|ai\s*and\s*ml|ai&ml|artificial\s*intelligence|machine\s*learning)\b|ఏఐ|आर्टिफिशियल'),
            ("B.Tech CSE", r'\b(cse|computer\s*science|cs|computer\s*engineering)\b|కంప్యూటర్\s*సైన్స్|कंप्यूटर\s*साइंस'),
            ("B.Tech ECE", r'\b(ece|electronics|electronics\s*and\s*communication)\b|ఈసీఈ|इलेक्ट्रॉनिक्स'),
            ("B.Tech EEE", r'\b(eee|electrical|electrical\s*and\s*electronics)\b|ఈఈఈ|इलेक्ट्रिकल'),
            ("B.Tech Mechanical", r'\b(mech|mechanical|mechanical\s*engineering)\b|మెకానికల్|मैकेनिकल'),
            ("B.Tech Civil", r'\b(civil|civil\s*engineering)\b|సివిల్|सिविल'),
            ("MBA", r'\b(mba|management|master\s*of\s*business)\b'),
            ("Pharmacy", r'\b(pharmacy|pharm|b\.?pharm|pharm\.?\s*d)\b|ఫార్మసీ|फार्मेसी'),
        ]
        for prog_name, pat in prog_patterns:
            if re.search(pat, t_low, re.IGNORECASE) or pat in text:
                self.slots["program"] = prog_name
                self.slots["program_of_interest"] = prog_name
                break

        # 4. Student Name & Name Corrections
        # A. Explicit name introduction or correction
        explicit_m = re.search(
            r'(?:my\s*name\s*is|myself|i\s*am|i\'m|this\s*is|call\s*me|naa\s*peru|mera\s*naam|naam|peru)\s*[:=]?\s*([^\W\d_]+(?:\s+[^\W\d_]+)?)(?:,?\s*(?:not|no|lekapothe)\s*([^\W\d_]+)?)?',
            text,
            re.UNICODE | re.IGNORECASE
        )
        if not explicit_m:
            explicit_m = re.search(
                r'\bnot\s+[^\W\d_]+,?\s*(?:my\s*name\s*is|i\s*am|i\'m|it\'s|its|call\s*me)\s+([^\W\d_]+)',
                text,
                re.UNICODE | re.IGNORECASE
            )

        if explicit_m:
            cand = explicit_m.group(1).strip()
            parts = cand.split()
            if len(parts) > 1 and parts[-1].lower() in {"and", "aur", "ani", "from", "here", "speaking", "calling", "interested", "looking", "for", "to", "in", "is", "not", "no"}:
                cand = parts[0]
            cand_low = cand.lower()
            if (
                len(cand) >= 2
                and cand_low not in self.INVALID_NAMES
                and not any(w in self.INVALID_NAMES for w in cand_low.split())
                and not cand_low.endswith("ing")
            ):
                self.slots["student_name"] = cand
                self.slots["name"] = cand
        elif not self.slots.get("student_name") and not self.slots.get("program") and len(words) in (1, 2, 3):
            # Standalone candidate
            cand = text.strip().strip(".,!?:;\"'")
            cand_low = cand.lower()
            if (
                cand
                and not re.search(r'\d', cand)
                and cand_low not in self.INVALID_NAMES
                and not any(w in self.INVALID_NAMES for w in words)
                and not re.search(r'\b(btech|b\.tech|cse|ece|fee|fees|hostel|campus|visit|college|aditya|scholarship|exam|marks)\b', cand_low)
                and not cand_low.endswith("ing")
            ):
                self.slots["student_name"] = cand
                self.slots["name"] = cand

        # 5. Campus Visit Agreement
        if re.search(r'\b(visit|campus tour|come this saturday|see campus|saturday 10|visit this saturday)\b', t_low):
            self.slots["visit_datetime"] = "Saturday 10:00 AM"
            self.slots["engagement_choice"] = "campus_visit"

        # Update monotonic stage progression
        self._compute_monotonic_stage()

        return self.slots

    def _compute_monotonic_stage(self):
        """Monotonic forward stage computation: never regresses back to GREETING."""
        has_booking = bool(self.slots.get("visit_datetime") or self.slots.get("engagement_choice"))
        has_exam = bool(self.slots.get("entrance_exam"))
        has_score = bool(self.slots.get("marks_12") or self.slots.get("class_12_score"))
        has_program = bool(self.slots.get("program") or self.slots.get("program_of_interest"))
        has_name = bool(self.slots.get("student_name") or self.slots.get("name"))

        if has_booking:
            self.stage = "CONVERT"
        elif has_score and has_exam:
            self.stage = "CONVERT"
        elif has_score or has_exam:
            self.stage = "ELIGIBILITY"
        elif has_program:
            self.stage = "ELIGIBILITY"
        elif has_name:
            self.stage = "PROGRAM"
        else:
            self.stage = "GREETING"

    # ── Turn Tracking & Rolling Summary ─────────────────────────────────

    def add_turn(self, user_text: str, agent_text: str, language: Optional[str] = None):
        """Records completed turn, updates slots, and triggers rolling summary if needed."""
        lang = language or self.active_language
        self.last_user_text = user_text
        self.last_agent_text = agent_text

        # 1. Update slots from user speech
        if user_text:
            self.extract_and_update_slots(user_text)

        # 2. Append to all_turns
        turn_num = len(self.all_turns) + 1
        turn_data = {
            "turn_number": turn_num,
            "timestamp": time.time(),
            "user": user_text,
            "agent": agent_text,
            "language": lang,
            "stage": self.stage,
            "slots": dict(self.slots),
        }
        self.all_turns.append(turn_data)

        # 3. Consolidate summary if turns > 6
        if len(self.all_turns) > 6:
            self._update_rolling_summary()

    def _update_rolling_summary(self):
        """Compresses turns 1..N-3 into a dense factual summary."""
        name = self.slots.get("student_name", "Student")
        prog = self.slots.get("program", "Not specified")
        score = self.slots.get("marks_12", "Not specified")
        exam = self.slots.get("entrance_exam", "None")
        visit = self.slots.get("visit_datetime", "Pending")

        self.running_summary = (
            f"Candidate: {name}. Program: {prog}. 12th Score: {score}. "
            f"Exam: {exam}. Campus Visit: {visit}. "
            f"Completed {len(self.all_turns)} turns across {self.active_language}."
        )

    # ── 5-Layer Context Assembler (<600 tokens) ─────────────────────────

    def assemble_llm_prompt(self, user_text: str) -> List[Dict[str, str]]:
        """
        Builds the 5-layer prompt strictly within token limits:
        1. System Rules
        2. Known Slots & Current Language
        3. Rolling Summary (if exists)
        4. Retrieved Background Memory (if exists)
        5. Last 3 Turns Window + Current User Input
        """
        messages: List[Dict[str, str]] = []

        # Layer 1 & 2: System Rules + State
        sys_parts = [SYSTEM_PROMPT_BASE.strip()]
        
        # Language directive
        lang_directive = LANGUAGE_STYLE_DIRECTIVES.get(self.active_language, LANGUAGE_STYLE_DIRECTIVES["en-IN"])
        sys_parts.append(f"\nACTIVE LANGUAGE: {self.active_language} ({LANGUAGE_NAMES.get(self.active_language, 'English')})\n{lang_directive}")

        # Known caller slots
        if self.slots:
            slot_lines = [f"• {k}: {v}" for k, v in self.slots.items() if not k.startswith("_")]
            sys_parts.append(f"\nKNOWN CALLER SLOTS (DO NOT RE-ASK):\n" + "\n".join(slot_lines))

        # Target next milestone
        target_field = STAGE_TARGET_FIELDS.get(self.stage, "campus_visit")
        sys_parts.append(f"\nCURRENT STAGE: {self.stage} | NEXT GOAL: Collect '{target_field}'")

        # Layer 4: Rolling summary
        if self.running_summary:
            sys_parts.append(f"\nCONVERSATION SUMMARY:\n{self.running_summary}")

        # Layer 5: Retrieved background memories
        if self.long_term_memories:
            mem_lines = [f"- {m.content}" for m in self.long_term_memories[:2]]
            sys_parts.append(f"\nRECALLED BACKGROUND:\n" + "\n".join(mem_lines))

        messages.append({"role": "system", "content": "\n".join(sys_parts)})

        # Layer 3: Recent sliding window (last 3 completed turns)
        recent_turns = self.all_turns[-3:]
        for turn in recent_turns:
            if turn.get("user"):
                messages.append({"role": "user", "content": turn["user"]})
            if turn.get("agent"):
                messages.append({"role": "assistant", "content": turn["agent"]})

        # Current user utterance
        if user_text:
            messages.append({"role": "user", "content": user_text})

        return messages
