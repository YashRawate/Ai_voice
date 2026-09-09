# conversation_history.py
"""
Conversation History Tracking System for Priya Voice Agent.
Maintains the ENTIRE conversation history from start to end without context loss.
Extracts facts, tracks asked questions, prevents repetition, and supports 20+ turn calls.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("priya.conversation_history")


class ConversationHistory:
    """Tracks the ENTIRE conversation history from start to end with zero context loss."""

    # Mapping from generic question IDs or slot keys to canonical fact keys
    FACT_MAPPING = {
        "q_score": "score",
        "score_question": "score",
        "12th_score": "score",
        "class_12_score": "score",
        "q_program": "program",
        "program_question": "program",
        "program_of_interest": "program",
        "q_name": "name",
        "name_question": "name",
        "student_name": "name",
        "q_exam": "exam",
        "exam_question": "exam",
        "entrance_exams_taken": "exam",
        "q_city": "city",
        "city_question": "city",
        "current_city": "city",
        "q_visit": "visit",
        "campus_visit": "visit",
        "visit_datetime": "visit",
    }

    def __init__(self, call_id: str = "call_default"):
        self.call_id = call_id
        self.turns: List[Dict[str, Any]] = []  # ENTIRE conversation history, never deleted
        self.facts: Dict[str, Any] = {}       # All facts ever mentioned
        self.extracted_facts = self.facts     # Alias for backwards compatibility
        self.questions_asked: Set[str] = set() # Questions / topics already asked
        self.asked_questions = self.questions_asked # Alias
        self.refusals: Set[str] = set()       # Questions/topics user refused or deferred
        self.user_preferences: Dict[str, Any] = {}
        self.sentiment_history: List[str] = []
        self.call_start = datetime.now()
        self.call_start_time = self.call_start

    def add_turn(
        self,
        user_msg: str,
        agent_msg: str,
        latency: float = 0.0,
        language: str = "en-IN"
    ) -> Dict[str, Any]:
        """Add complete turn to history."""
        turn_num = len(self.turns) + 1
        turn = {
            "num": turn_num,
            "turn_number": turn_num,
            "time": datetime.now(),
            "timestamp": datetime.now(),
            "user": user_msg or "",
            "user_input": user_msg or "",
            "agent": agent_msg or "",
            "agent_response": agent_msg or "",
            "latency": latency,
            "language": language or "en-IN",
        }
        self.turns.append(turn)

        # Automatically extract facts and register any assistant questions asked
        if user_msg:
            self.extract_facts(user_msg)
        if agent_msg and "?" in agent_msg:
            self._infer_and_record_agent_question(agent_msg)

        return turn

    def extract_facts(self, text: str) -> Dict[str, Any]:
        """
        Extract facts mentioned by user:
        Score (12th/intermediate), Program/Branch, Student Name, Entrance Exams,
        City/Location, Hostel, etc.
        """
        if not text:
            return {}

        new_facts: Dict[str, Any] = {}
        text_lower = text.lower()

        # 1. Extract score (e.g. 92%, 95.5%, scored 88, 92 in 12th)
        score_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*(?:%|percent|percentage)', text_lower)
        if not score_match:
            score_match = re.search(r'(?:scored|got|have|marks|score(?:\s+is)?)\s+(\d{1,2}(?:\.\d+)?)', text_lower)
        if not score_match:
            score_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*(?:in\s*(?:12th|inter|intermediate|board|cbse))', text_lower)

        if score_match:
            try:
                val = float(score_match.group(1))
                if 35.0 <= val <= 100.0:
                    score_str = f"{val:g}%" if val != int(val) else f"{int(val)}%"
                    new_facts['score'] = score_str
                    new_facts['class_12_score'] = score_str
            except (ValueError, IndexError):
                pass

        # 2. Extract program / branch
        program_keywords = [
            ("CSE (Data Science)", [r'\b(data\s*science|cse\s*data\s*science|ds)\b', 'డేటా సైన్స్', 'डेटा साइंस']),
            ("AI/ML", [r'\b(aiml|ai\s*[\/&]?\s*ml|ai\s*and\s*ml|ai&ml|artificial\s*intelligence|machine\s*learning)\b', r'ai\/ml', 'ఏఐ', 'आर्टिफिशियल']),
            ("CSE", [r'\b(cse|computer\s*science|cs|computer\s*engineering)\b', 'కంప్యూటర్ సైన్స్', 'कंप्यूटर साइंस']),
            ("ECE", [r'\b(ece|electronics|electronics\s*and\s*communication)\b', 'ఈసీఈ', 'इलेक्ट्रॉनिक्स']),
            ("EEE", [r'\b(eee|electrical|electrical\s*and\s*electronics)\b', 'ఈఈఈ', 'इलेक्ट्रिकल']),
            ("Mechanical", [r'\b(mech|mechanical|mechanical\s*engineering)\b', 'మెకానికల్', 'मैकेनिकल']),
            ("Civil", [r'\b(civil|civil\s*engineering)\b', 'సివిల్', 'सिविल']),
            ("Agriculture", [r'\b(agri|agriculture|agricultural)\b', 'అగ్రికల్చర్', 'एग्रीकल्चर']),
            ("Petroleum", [r'\b(petro|petroleum)\b', 'పెట్రోలియం', 'पेट्रोलियम']),
            ("Mining", [r'\b(mining)\b', 'మైనింగ్', 'माइनिंग']),
            ("MBA", [r'\b(mba|management|master\s*of\s*business)\b']),
            ("BBA", [r'\b(bba|bachelor\s*of\s*business)\b']),
            ("Pharmacy", [r'\b(pharmacy|pharm|b\.?pharm|pharm\.?\s*d)\b', 'ఫార్మసీ', 'फार्मेसी']),
            ("MCA", [r'\b(mca)\b']),
            ("BCA", [r'\b(bca)\b']),
        ]

        for prog_name, patterns in program_keywords:
            matched = False
            for pat in patterns:
                if re.search(pat, text_lower, re.IGNORECASE) or pat in text:
                    new_facts['program'] = prog_name
                    new_facts['program_of_interest'] = prog_name
                    matched = True
                    break
            if matched:
                break

        # 3. Extract name
        invalid_names = {
            "interested", "admission", "calling", "student", "good", "fine", "asking",
            "looking", "inquiring", "checking", "wondering", "telling", "trying", "here",
            "just", "now", "not", "talking", "with", "from", "in", "at", "for", "about",
            "platform", "first", "which", "what", "how", "why", "where", "you", "me",
            "done", "doing", "passed", "studying", "yes", "yeah", "yep", "no", "nah",
            "okay", "ok", "sure", "fine", "hello", "hi", "hey", "alright", "sare", "theek"
        }
        name_match = re.search(
            r'(?:my\s*name\s*is|i\s*am|i\'m|this\s*is|call\s*me|naa\s*peru|mera\s*naam)\s+([a-zA-Z]{3,20})',
            text_lower
        )
        if name_match:
            candidate = name_match.group(1).capitalize()
            if candidate.lower() not in invalid_names and not candidate.lower().endswith("ing"):
                new_facts['name'] = candidate
                new_facts['student_name'] = candidate

        # 4. Extract entrance exams
        exams_map = {
            "JEE": r'\b(jee|jee\s*mains?|jee\s*advanced|iit)\b',
            "AP_EAPCET": r'\b(ap\s*eapcet|ap\s*eamcet|eapcet|eamcet|apeapcet|apeamcet)\b',
            "TS_EAMCET": r'\b(ts\s*eamcet|ts\s*eapcet|tseamcet|tseapcet)\b',
            "ASAT": r'\b(asat|aditya\s*scholarship|aditya\s*entrance)\b',
            "CUET": r'\b(cuet)\b',
            "NEET": r'\b(neet)\b',
            "CAT": r'\b(cat)\b',
            "MAT": r'\b(mat)\b',
            "ICET": r'\b(icet|apicet|tsicet)\b',
        }
        detected_exams = []
        for exam_key, pat in exams_map.items():
            if re.search(pat, text_lower):
                detected_exams.append(exam_key)

        if detected_exams:
            exam_str = ", ".join(detected_exams)
            new_facts['exam'] = exam_str
            existing_exam = self.facts.get('entrance_exams_taken', '')
            if existing_exam:
                combined = set([e.strip() for e in existing_exam.split(',') if e.strip()] + detected_exams)
                new_facts['entrance_exams_taken'] = ", ".join(sorted(combined))
            else:
                new_facts['entrance_exams_taken'] = exam_str

        # 5. Extract city
        city_patterns = [
            r'(?:from|live\s*in|living\s*in|stay\s*in|staying\s*in|native\s*(?:is|place\s*is)?|location\s*(?:is)?)\s+([A-Za-z]{3,20})',
            r'([A-Za-z]{3,20})\s+(?:lo\s*untunnanu|lo\s*untamu|lo\s*unta|nunchi|se\s*bol\s*raha|se\s*hoon|se\s*hu)',
        ]
        for c_pat in city_patterns:
            c_match = re.search(c_pat, text_lower, re.IGNORECASE)
            if c_match:
                city_cand = c_match.group(1).capitalize()
                if city_cand.lower() not in invalid_names:
                    new_facts['city'] = city_cand
                    new_facts['current_city'] = city_cand
                    break

        # 6. Extract preferences
        if any(w in text_lower for w in ['hostel', 'accommodation', 'room', 'mess', 'stay']):
            self.user_preferences['interested_in'] = 'hostel'
            new_facts['hostel_interest'] = True

        if any(w in text_lower for w in ['scholarship', 'waiver', 'discount', 'fee concession']):
            self.user_preferences['scholarship_interest'] = True

        if any(w in text_lower for w in ['campus visit', 'visit campus', 'come to college', 'see campus']):
            self.user_preferences['visit_interest'] = True

        # Check for user refusal / postponement
        self._detect_refusals(text_lower)

        # Update persistent facts
        self.facts.update(new_facts)
        return new_facts

    def _detect_refusals(self, text_lower: str):
        """Detect if user declines or postpones answering certain questions."""
        # Score refusal
        if any(w in text_lower for w in ["don't know score", "dont know score", "haven't checked", "havent checked",
                                         "no score", "results awaited", "will tell later", "tell later",
                                         "not now", "later for score"]):
            self.record_refusal("q_score")
            self.record_refusal("score_question")

        # Exam refusal
        if any(w in text_lower for w in ["no exam", "haven't taken", "havent taken", "didn't give", "did not give",
                                         "not written", "not applicable", "no jee", "no eapcet", "no entrance"]):
            self.record_refusal("q_exam")
            self.record_refusal("exam_question")
            self.facts["exam"] = "None"
            self.facts["entrance_exams_taken"] = "None"

        # Name refusal / skip
        if any(w in text_lower for w in ["don't want to tell", "just tell me", "skip name", "call me later"]):
            self.record_refusal("q_name")
            self.record_refusal("name_question")

        # Visit refusal
        if any(w in text_lower for w in ["cannot visit", "can't visit", "too far", "not possible to visit", "busy"]):
            self.record_refusal("q_visit")
            self.record_refusal("campus_visit")

    def _infer_and_record_agent_question(self, text: str):
        """Detect question categories asked by agent to prevent repeated inquiries."""
        t_low = text.lower()
        if any(w in t_low for w in ["name", "naam", "peru"]):
            self.record_question_asked("q_name")
            self.record_question_asked("name_question")
        if any(w in t_low for w in ["which program", "which branch", "which course", "what course"]):
            self.record_question_asked("q_program")
            self.record_question_asked("program_question")
        if any(w in t_low for w in ["score", "percentage", "marks", "12th", "intermediate"]):
            self.record_question_asked("q_score")
            self.record_question_asked("score_question")
        if any(w in t_low for w in ["jee", "eapcet", "eamcet", "entrance exam", "exam"]):
            self.record_question_asked("q_exam")
            self.record_question_asked("exam_question")
        if any(w in t_low for w in ["visit", "campus visit", "tour"]):
            self.record_question_asked("q_visit")
            self.record_question_asked("campus_visit")

    def record_question_asked(self, question_id: str):
        """Remember that we already asked this question."""
        self.questions_asked.add(question_id)

    def is_question_asked(self, question_id: str) -> bool:
        """Check if this question was already asked in the call."""
        canonical = self.FACT_MAPPING.get(question_id, question_id)
        return (
            question_id in self.questions_asked
            or canonical in self.questions_asked
            or f"q_{canonical}" in self.questions_asked
            or f"{canonical}_question" in self.questions_asked
        )

    def record_refusal(self, question_id: str):
        """Record that the user declined or deferred this question."""
        self.refusals.add(question_id)
        canonical = self.FACT_MAPPING.get(question_id, question_id)
        self.refusals.add(canonical)

    def is_refused(self, question_id: str) -> bool:
        """Check if user previously refused or postponed this topic."""
        canonical = self.FACT_MAPPING.get(question_id, question_id)
        return (
            question_id in self.refusals
            or canonical in self.refusals
            or f"q_{canonical}" in self.refusals
        )

    def has_fact(self, fact_key: str) -> bool:
        """Check if we already know this fact (voluntarily provided or asked)."""
        canonical = self.FACT_MAPPING.get(fact_key, fact_key)
        # Check canonical, original, and common aliases
        candidates = [fact_key, canonical]
        if canonical == "score":
            candidates.extend(["12th_score", "class_12_score"])
        elif canonical == "program":
            candidates.extend(["program_of_interest", "specialization"])
        elif canonical == "name":
            candidates.extend(["student_name"])
        elif canonical == "exam":
            candidates.extend(["entrance_exams_taken"])
        elif canonical == "city":
            candidates.extend(["current_city"])

        return any(k in self.facts and bool(self.facts[k]) for k in candidates)

    def has_fact_for(self, question_id: str) -> bool:
        """Alias for has_fact matching question IDs."""
        return self.has_fact(question_id)

    def get_fact(self, fact_key: str) -> Optional[Any]:
        """Get value of a known fact."""
        canonical = self.FACT_MAPPING.get(fact_key, fact_key)
        candidates = [fact_key, canonical]
        if canonical == "score":
            candidates.extend(["12th_score", "class_12_score"])
        elif canonical == "program":
            candidates.extend(["program_of_interest", "specialization"])
        elif canonical == "name":
            candidates.extend(["student_name"])
        elif canonical == "exam":
            candidates.extend(["entrance_exams_taken"])
        elif canonical == "city":
            candidates.extend(["current_city"])

        for k in candidates:
            if k in self.facts and self.facts[k]:
                return self.facts[k]
        return None

    def should_ask_question(self, question_id: str, fact_key: Optional[str] = None) -> bool:
        """
        Determine if we should ask this question.
        Returns False if:
        1. Already asked in this call
        2. Answer is already known (voluntarily provided or earlier captured)
        3. Caller previously declined or asked to postpone
        """
        target_fact = fact_key or self.FACT_MAPPING.get(question_id, question_id)

        if self.is_question_asked(question_id):
            return False

        if self.is_refused(question_id) or self.is_refused(target_fact):
            return False

        if self.has_fact(target_fact):
            return False

        return True

    def get_context(self) -> str:
        """
        Build complete conversation history context string for LLM.
        Includes ALL turns, facts gathered, and questions to avoid.
        """
        lines = [
            "═══════════════════════════════════════════════════════════════",
            f"ENTIRE CONVERSATION HISTORY (Call started {self.call_start.strftime('%H:%M:%S')}):",
            "═══════════════════════════════════════════════════════════════",
        ]

        if not self.turns:
            lines.append("No previous turns yet. This is turn 1.")
        else:
            for turn in self.turns:
                t_num = turn.get("num") or turn.get("turn_number")
                lang = turn.get("language", "en-IN")
                u_text = turn.get("user") or turn.get("user_input") or ""
                a_text = turn.get("agent") or turn.get("agent_response") or ""
                lines.append(f"Turn {t_num} ({lang}):")
                lines.append(f"  User: {u_text}")
                lines.append(f"  Agent: {a_text}")

        lines.extend([
            "",
            "═══════════════════════════════════════════════════════════════",
            "FACTS EXTRACTED FROM CALLER (DO NOT RE-ASK):",
            "═══════════════════════════════════════════════════════════════",
        ])

        if self.facts:
            # Display unique canonical facts
            displayed = set()
            for k, v in self.facts.items():
                canon = self.FACT_MAPPING.get(k, k)
                if canon not in displayed:
                    lines.append(f"- {canon.upper()}: {v}")
                    displayed.add(canon)
        else:
            lines.append("- No facts discovered yet.")

        lines.extend([
            "",
            "═══════════════════════════════════════════════════════════════",
            "QUESTIONS ALREADY ASKED / ANSWERED / REFUSED (NEVER REPEAT):",
            "═══════════════════════════════════════════════════════════════",
        ])

        all_blocked = set(self.questions_asked) | set(self.refusals)
        if all_blocked:
            for q in sorted(all_blocked):
                lines.append(f"- {q}")
        else:
            lines.append("- None yet.")

        return "\n".join(lines)

    def get_full_context(self) -> str:
        """Alias for get_context."""
        return self.get_context()

    def get_call_duration(self):
        """Get call duration timedelta."""
        return datetime.now() - self.call_start

    def get_call_summary(self) -> Dict[str, Any]:
        """Summary of entire call."""
        return {
            "call_id": self.call_id,
            "duration": self.get_call_duration(),
            "duration_seconds": self.get_call_duration().total_seconds(),
            "turns_count": len(self.turns),
            "facts_discovered": dict(self.facts),
            "questions_asked": list(self.questions_asked),
            "refusals": list(self.refusals),
            "preferences": dict(self.user_preferences),
        }

    def get_full_transcript(self) -> str:
        """Generate complete, formatted call transcript."""
        transcript = [
            f"COMPLETE CALL TRANSCRIPT ({self.call_id})",
            "=" * 60,
            f"Start Time: {self.call_start.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Turns: {len(self.turns)}",
            "=" * 60,
            "",
        ]

        for turn in self.turns:
            t_num = turn.get("num") or turn.get("turn_number")
            lang = turn.get("language", "en-IN")
            u_text = turn.get("user") or turn.get("user_input") or ""
            a_text = turn.get("agent") or turn.get("agent_response") or ""
            t_time = turn.get("time") or turn.get("timestamp")
            time_str = t_time.strftime("%H:%M:%S") if hasattr(t_time, "strftime") else str(t_time)
            latency = turn.get("latency", 0.0)

            transcript.append(f"Turn {t_num} [{time_str}] ({lang}):")
            transcript.append(f"User:  {u_text}")
            transcript.append(f"Priya: {a_text}")
            transcript.append(f"(Latency: {latency:.2f}s)")
            transcript.append("")

        summary = self.get_call_summary()
        transcript.extend([
            "=" * 60,
            "CALL SUMMARY:",
            f"- Total Duration: {summary['duration_seconds']:.1f}s",
            f"- Turns Count: {summary['turns_count']}",
            f"- Facts Discovered: {json.dumps(summary['facts_discovered'], indent=2)}",
            f"- Questions Asked: {list(summary['questions_asked'])}",
            f"- Refusals: {list(summary['refusals'])}",
            "=" * 60,
        ])

        return "\n".join(transcript)
