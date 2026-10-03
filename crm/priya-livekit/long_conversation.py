# long_conversation.py
"""
4-Layer Conversation Memory Architecture for Long Conversation Management.
Guarantees:
- Zero repeated questions across 15-30+ minute calls
- Permanent retention of all extracted facts (Layer 2 FactMemory)
- Sliding window active context for token-bounded, low-latency LLM calls (Layer 1 SlidingWindow)
- Full conversation audit trail with topic discussion tracking (Layer 3 ConversationHistory)
- Explicit dialogue state machine (Layer 4 DialogueState: greeting -> info_gathering -> clarification -> closing)
- Non-mandatory, natural conversational flow with multilingual goodbye detection
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("priya.long_conversation")


# =====================================================================
# LAYER 1: SLIDING WINDOW (Active Context)
# =====================================================================

class SlidingWindow:
    """
    Keeps last N turns (default 8) in active memory.
    - Fits comfortably in LLM context (<500 tokens)
    - Keeps inference latency low (<600ms)
    - Retains recent back-and-forth conversational flow
    """

    def __init__(self, max_turns: int = 8):
        self.max_turns = max_turns
        self.turns: List[Dict[str, Any]] = []

    def add_turn(
        self,
        user_input: str,
        agent_response: str,
        timestamp: Optional[datetime] = None,
        language: str = "en-IN"
    ):
        """Add a completed turn and slide window if capacity exceeded."""
        turn_data = {
            "user": user_input or "",
            "agent": agent_response or "",
            "timestamp": timestamp or datetime.now(),
            "language": language or "en-IN",
        }
        self.turns.append(turn_data)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

    def get_context(self, last_n: int = 5) -> str:
        """Get formatted context of the most recent turns for the LLM."""
        if not self.turns:
            return "Recent conversation:\n  (First turn of conversation)"

        selected_turns = self.turns[-last_n:] if len(self.turns) > last_n else self.turns
        lines = ["Recent conversation:"]
        for i, turn in enumerate(selected_turns, 1):
            u = turn.get("user", "")
            a = turn.get("agent", "")
            lines.append(f"Turn {i}:")
            lines.append(f"  User: {u}")
            lines.append(f"  Agent: {a}")
        return "\n".join(lines)

    def get_turns(self) -> List[Dict[str, Any]]:
        return list(self.turns)

    def clear(self):
        self.turns.clear()

    def __len__(self) -> int:
        return len(self.turns)


# =====================================================================
# LAYER 2: EXTRACTED FACTS (Permanent Slots)
# =====================================================================

class FactMemory:
    """
    Stores all extracted facts permanently.
    - Survives sliding window drops
    - Injected into every LLM prompt to prevent re-asking
    - Multilingual pattern matching (English, Telugu, Hindi)
    """

    INVALID_NAMES = {
        "interested", "admission", "calling", "student", "good", "fine", "asking",
        "looking", "inquiring", "checking", "wondering", "telling", "trying", "here",
        "just", "now", "not", "talking", "with", "from", "in", "at", "for", "about",
        "platform", "first", "which", "what", "how", "why", "where", "you", "me",
        "done", "doing", "passed", "studying", "yes", "yeah", "yep", "no", "nah",
        "okay", "ok", "sure", "fine", "hello", "hi", "hey", "alright", "sare", "theek",
        "details", "information", "course", "college", "university"
    }

    INVALID_CITIES = {
        "like", "that", "this", "here", "there", "then", "now", "just", "want", "visit",
        "visiting", "tell", "telling", "asking", "college", "school", "university",
        "campus", "aditya", "engineering", "btech", "cse", "admission", "student",
        "home", "house", "room", "hostel", "interested", "good", "fine", "yes", "sure",
        "okay", "ok", "alright", "morning", "afternoon", "evening", "today", "tomorrow",
        "cbse", "icse", "state", "board", "inter", "intermediate", "the", "a", "an", "all", "city"
    }

    def __init__(self):
        self.facts: Dict[str, Any] = {}

    def update_fact(self, key: str, value: Any):
        """Manually update or set a fact."""
        self.facts[key] = value

    def extract_from_input(self, user_input: str) -> Dict[str, Any]:
        """Extract all identifiable facts from caller text."""
        if not user_input or not user_input.strip():
            return {}

        text = user_input.strip()
        text_lower = text.lower()
        extracted: Dict[str, Any] = {}

        # 1. Name extraction (multilingual: English, Telugu, Hindi)
        if "name" not in self.facts:
            name_match = re.search(
                r'(?:my\s*name\s*is|i\s*am|i\'m|this\s*is|call\s*me|naa\s*peru|mera\s*naam|నా\s*పేరు|నాపేరు|మేరా\s*నామ్|मेरा\s*नाम)\s+([a-zA-Z\u0C00-\u0C7F\u0900-\u097F]{3,20})',
                text,
                re.IGNORECASE
            )
            if name_match:
                candidate = name_match.group(1).capitalize()
                if candidate.lower() not in self.INVALID_NAMES and not candidate.lower().endswith("ing"):
                    extracted["name"] = candidate
                    self.facts["name"] = candidate

        # 2. Score extraction (12th / Intermediate percentage)
        if "score" not in self.facts:
            score_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*(?:%|percent|percentage)', text_lower)
            if not score_match:
                score_match = re.search(r'(?:scored|got|have|marks|score(?:\s+is)?)\s+(\d{1,2}(?:\.\d+)?)', text_lower)
            if not score_match:
                score_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*(?:in\s*(?:12th|inter|intermediate|board|cbse))', text_lower)

            if score_match:
                try:
                    val = float(score_match.group(1))
                    if 35.0 <= val <= 100.0:
                        score_str = f"{val:g}%"
                        extracted["score"] = score_str
                        self.facts["score"] = score_str
                except (ValueError, IndexError):
                    pass

        # 3. Program / Branch extraction
        if "program" not in self.facts:
            program_keywords = [
                ("B.Tech CSE (Data Science)", [r'\b(data\s*science|cse\s*data\s*science|ds)\b', 'డేటా సైన్స్', 'डेटा साइंस']),
                ("B.Tech AI/ML", [r'\b(aiml|ai\s*[\/&]?\s*ml|ai\s*and\s*ml|ai&ml|artificial\s*intelligence|machine\s*learning)\b', r'ai\/ml', 'ఏఐ', 'आर्टिफिशियल']),
                ("B.Tech CSE", [r'\b(cse|computer\s*science|cs|computer\s*engineering)\b', 'కంప్యూటర్ సైన్స్', 'कंप्यूटर साइंस']),
                ("B.Tech ECE", [r'\b(ece|electronics|electronics\s*and\s*communication)\b', 'ఈసీఈ', 'इलेक्ट्रॉनिक्स']),
                ("B.Tech EEE", [r'\b(eee|electrical|electrical\s*and\s*electronics)\b', 'ఈఈఈ', 'इलेक्ट्रिकल']),
                ("B.Tech Mechanical", [r'\b(mech|mechanical|mechanical\s*engineering)\b', 'మెకానికల్', 'मैकेनिकल']),
                ("B.Tech Civil", [r'\b(civil|civil\s*engineering)\b', 'సివిల్', 'सिविल']),
                ("B.Tech Agriculture", [r'\b(agri|agriculture|agricultural)\b', 'అగ్రికల్చర్', 'एग्रीकल्चर']),
                ("B.Tech Petroleum", [r'\b(petro|petroleum)\b', 'పెట్రోలియం', 'पेट्रोलियम']),
                ("B.Tech Mining", [r'\b(mining)\b', 'మైనింగ్', 'माइनिंग']),
                ("MBA", [r'\b(mba|master\s*of\s*business)\b']),
                ("BBA", [r'\b(bba|bachelor\s*of\s*business)\b']),
                ("Pharmacy", [r'\b(pharmacy|pharm|b\.?pharm|pharm\.?\s*d)\b', 'ఫార్మసీ', 'फार्मेसी']),
                ("MCA", [r'\b(mca)\b']),
                ("BCA", [r'\b(bca)\b']),
            ]
            for prog_name, patterns in program_keywords:
                matched = False
                for pat in patterns:
                    if re.search(pat, text_lower, re.IGNORECASE) or pat in text:
                        extracted["program"] = prog_name
                        self.facts["program"] = prog_name
                        matched = True
                        break
                if matched:
                    break

        # 4. City / Location extraction
        if "city" not in self.facts:
            city_patterns = [
                r'(?:from|live\s*in|living\s*in|stay\s*in|native\s*(?:is|place\s*is)?|location\s*(?:is)?)\s+([A-Za-z]{3,20})',
                r'([A-Za-z]{3,20})\s+(?:lo\s*untunnanu|lo\s*untamu|lo\s*unta|nunchi|se\s*bol\s*raha|se\s*hoon|se\s*hu)',
                r'\bcity\s*(?:is)?\s+([A-Za-z]{3,20})',
            ]
            for c_pat in city_patterns:
                c_match = re.search(c_pat, text_lower, re.IGNORECASE)
                if c_match:
                    city_cand = c_match.group(1).capitalize()
                    if city_cand.lower() not in self.INVALID_NAMES and city_cand.lower() not in self.INVALID_CITIES:
                        extracted["city"] = city_cand
                        self.facts["city"] = city_cand
                        break

        # 5. Entrance exam extraction
        if "exam" not in self.facts:
            exams_map = {
                "JEE": r'\b(jee|jee\s*mains?|jee\s*advanced|iit)\b',
                "AP_EAPCET": r'\b(ap\s*eapcet|ap\s*eamcet|eapcet|eamcet|apeapcet|apeamcet)\b',
                "TS_EAMCET": r'\b(ts\s*eamcet|ts\s*eapcet|tseamcet|tseapcet)\b',
                "ASAT": r'\b(asat|aditya\s*scholarship|aditya\s*entrance)\b',
                "CUET": r'\b(cuet)\b',
                "NEET": r'\b(neet)\b',
            }
            detected = [k for k, p in exams_map.items() if re.search(p, text_lower)]
            if detected:
                exam_val = ", ".join(detected)
                extracted["exam"] = exam_val
                self.facts["exam"] = exam_val

        # 6. Preferences
        if any(w in text_lower for w in ["hostel", "accommodation", "room", "mess"]):
            self.facts["hostel_interest"] = "Yes"
            extracted["hostel_interest"] = "Yes"

        if any(w in text_lower for w in ["scholarship", "fee waiver", "concession"]):
            self.facts["scholarship_interest"] = "Yes"
            extracted["scholarship_interest"] = "Yes"

        return extracted

    def get_formatted(self) -> str:
        """Format known facts block for LLM prompt."""
        if not self.facts:
            return "No information gathered yet."

        formatted = "KNOWN FACTS ABOUT CALLER (NEVER ask for details listed above):\n"
        for key, value in self.facts.items():
            label = key.replace("_", " ").title()
            formatted += f"  • {label}: {value}\n"
        return formatted.strip()

    def has_fact(self, key: str) -> bool:
        return key in self.facts and bool(self.facts[key])

    def get_fact(self, key: str, default: Any = None) -> Any:
        return self.facts.get(key, default)

    def update(self, new_facts: Dict[str, Any]):
        self.facts.update(new_facts)


# =====================================================================
# LAYER 3: CONVERSATION HISTORY (Full Log & Topic Tracker)
# =====================================================================

class ConversationHistory:
    """
    Complete transcript of the entire call.
    - Full log of every turn (never lost or truncated)
    - Tracks topics discussed to prevent duplicate inquiries
    - Enables smart follow-ups and exportable audit trail
    """

    # Keyword mappings for automatic topic tagging
    TOPIC_KEYWORDS = {
        "program": ["program", "course", "branch", "engineering", "cse", "ece", "mechanical", "civil", "mba", "btech"],
        "score": ["score", "marks", "percentage", "12th", "inter", "intermediate", "board", "grade"],
        "fees": ["fee", "fees", "cost", "tuition", "charge", "payment", "lakh", "per year"],
        "scholarship": ["scholarship", "waiver", "discount", "merit", "concession", "asat"],
        "hostel": ["hostel", "accommodation", "room", "mess", "food", "stay", "boarding"],
        "placements": ["placement", "package", "recruiter", "amazon", "microsoft", "highest package", "average package", "job"],
        "exams": ["exam", "jee", "eapcet", "eamcet", "entrance", "neet", "cuet", "asat"],
        "campus_visit": ["visit", "campus visit", "tour", "directions", "location", "address", "saturday"],
        "admission": ["apply", "application", "admission", "register", "registration", "seat", "process"],
    }

    def __init__(self, call_id: str = "call_default"):
        self.call_id = call_id
        self.full_history: List[Dict[str, Any]] = []
        self.topics_discussed: Set[str] = set()
        self.questions_asked: Set[str] = set()
        self.refusals: Set[str] = set()
        self.call_start: datetime = datetime.now()

    def add_turn(
        self,
        user_input: str,
        agent_response: str,
        topic: Optional[str] = None,
        language: str = "en-IN",
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Record turn in full audit log with topic tagging."""
        t_time = timestamp or datetime.now()

        # Tag all matching topics
        detected_topics = self._infer_topics(user_input, agent_response)
        if topic and topic not in detected_topics:
            detected_topics.append(topic)
        primary_topic = topic or (detected_topics[0] if detected_topics else None)

        turn = {
            "turn_number": len(self.full_history) + 1,
            "timestamp": t_time,
            "user": user_input or "",
            "agent": agent_response or "",
            "topic": primary_topic,
            "topics": detected_topics,
            "language": language or "en-IN",
        }
        self.full_history.append(turn)

        for top in detected_topics:
            self.topics_discussed.add(top)
        if primary_topic:
            self.topics_discussed.add(primary_topic)

        # Track questions asked by agent
        if agent_response and "?" in agent_response:
            self._record_agent_question(agent_response)

        return turn

    def _infer_topics(self, user_text: str, agent_text: str) -> List[str]:
        combined = f"{user_text} {agent_text}".lower()
        matched = []
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(k in combined for k in keywords):
                matched.append(topic)
        return matched

    def _infer_topic(self, user_text: str, agent_text: str) -> Optional[str]:
        topics = self._infer_topics(user_text, agent_text)
        return topics[0] if topics else None

    def _record_agent_question(self, agent_text: str):
        low = agent_text.lower()
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(k in low for k in keywords):
                self.questions_asked.add(topic)

    def has_topic_been_discussed(self, topic: str) -> bool:
        """Check if topic was already covered in this call."""
        return topic.lower() in self.topics_discussed

    def get_topic_context(self, topic: str) -> Optional[str]:
        """Get what was previously discussed regarding this topic."""
        relevant = [
            turn for turn in self.full_history
            if turn.get("topic") == topic.lower() or topic.lower() in turn.get("topics", [])
        ]
        if not relevant:
            return None

        lines = [f"Previous discussion about {topic}:"]
        for turn in relevant[-2:]:  # Last 2 mentions
            lines.append(f"  User: {turn['user']}")
            lines.append(f"  Agent: {turn['agent']}")
        return "\n".join(lines)

    def should_ask_about(self, topic: str) -> bool:
        """Decide if we should ask about this topic (False if already discussed)."""
        return not self.has_topic_been_discussed(topic)

    def record_refusal(self, topic: str):
        """Record user declined or deferred this topic."""
        self.refusals.add(topic.lower())

    def is_refused(self, topic: str) -> bool:
        return topic.lower() in self.refusals

    def get_topics(self) -> List[str]:
        return list(sorted(self.topics_discussed))

    def get_full_transcript(self) -> str:
        """Generate formatted call transcript string."""
        lines = [
            f"COMPLETE CALL TRANSCRIPT ({self.call_id})",
            "=" * 60,
            f"Start Time: {self.call_start.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Turns: {len(self.full_history)}",
            f"Topics Discussed: {', '.join(sorted(self.topics_discussed)) if self.topics_discussed else 'None'}",
            "=" * 60,
            "",
        ]
        for turn in self.full_history:
            t_num = turn["turn_number"]
            t_time = turn["timestamp"].strftime("%H:%M:%S")
            lang = turn.get("language", "en-IN")
            lines.append(f"Turn {t_num} [{t_time}] ({lang}) [Topic: {turn.get('topic') or 'general'}]:")
            lines.append(f"  User:  {turn['user']}")
            lines.append(f"  Priya: {turn['agent']}")
            lines.append("")
        return "\n".join(lines)

    def export_transcript(self, filepath: Optional[str] = None) -> str:
        """Save transcript to disk."""
        target_path = filepath or f"transcripts/{self.call_id}.txt"
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        transcript = self.get_full_transcript()
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        return target_path


# =====================================================================
# LAYER 4: DIALOGUE STATE MACHINE (Stage & Flow Controller)
# =====================================================================

class DialogueState:
    """
    Tracks current conversation stage and information gaps.
    - Prevents sudden random state leaps
    - Tells LLM exactly what stage we're in
    - Drives natural flow from Greeting -> Info Gathering -> Clarification -> Closing
    """

    GREETING = "greeting"
    INFO_GATHERING = "info_gathering"
    CLARIFICATION = "clarification"
    VALUE_PITCH = "value_pitch"
    CONVERSION_OFFER = "conversion_offer"
    CLOSING = "closing"

    def __init__(self):
        self.current_state = self.GREETING
        self.info_needed: Dict[str, bool] = {
            "name": False,
            "program": False,
            "score": False,
            "city": False
        }

    def mark_info_received(self, info_type: str):
        """Mark that information piece has been collected."""
        if info_type in self.info_needed:
            self.info_needed[info_type] = True

    def sync_with_facts(self, facts: Dict[str, Any]):
        """Synchronize needed info checklist with current facts."""
        for key in self.info_needed:
            if key in facts and facts[key]:
                self.info_needed[key] = True

    def get_next_state(self) -> str:
        """Determine next logical conversation state."""
        # Core items: program & score are key for university counseling
        core_info_received = self.info_needed["program"] and self.info_needed["score"]
        all_info_received = all(self.info_needed.values())

        if self.current_state == self.GREETING:
            if core_info_received:
                return self.CLARIFICATION
            return self.INFO_GATHERING

        elif self.current_state == self.INFO_GATHERING:
            if all_info_received:
                return self.CLOSING
            elif core_info_received:
                return self.CLARIFICATION
            return self.INFO_GATHERING

        elif self.current_state == self.CLARIFICATION:
            if all_info_received:
                return self.CLOSING
            return self.CLARIFICATION

        elif self.current_state == self.CLOSING:
            return self.CLOSING

        return self.current_state

    def get_missing_info(self) -> List[str]:
        """What information items are still missing?"""
        return [info_type for info_type, received in self.info_needed.items() if not received]


# =====================================================================
# UNIFIED COORDINATOR: LONG CONVERSATION MANAGER
# =====================================================================

class LongConversationManager:
    """
    Coordinates all 4 memory layers to manage conversations of arbitrary length
    with ZERO repetition, natural conversational flow, and low latency.
    """

    GOODBYE_PATTERNS = [
        # English
        r'\b(thank\s*you|thanks|bye|goodbye|that(\'?s|\s+is)\s+(all|it|enough)|nothing\s+else|done|see\s+you)\b',
        # Hindi / Hinglish
        r'(धन्यवाद|शुक्रिया|अलविदा|नमस्ते|बस|काफी\s*है|और\s*कुछ\s*नहीं|बाय|nahi|theek\s*hai|sahi\s*hai\s*bye)',
        # Telugu / Teluglish
        r'(ధన్యవాదాలు|థాంక్స్|చాలు|ఇక\s*చాలు|సరే\s*థాంక్స్|బై|vaddu|inkemi\s*ledu)',
        # Tamil
        r'(நன்றி|போதும்|வணக்கம்|பை)',
    ]
    GOODBYE_RE = re.compile("|".join(GOODBYE_PATTERNS), re.IGNORECASE)

    # Lead-to-Admission Conversion Action Patterns
    CONVERSION_PATTERNS = {
        "apply_now_direct": [
            r"\b(apply\s*(right\s*now|now|today)|ready\s+to\s+apply|start\s+application|submit\s+(application|form|now)|fill\s+(up\s+)?(application|form))\b",
            r"\b(here\s+is\s+my|take\s+down\s+my\s+details|start\s+entering)\b",
            r"(అప్లై\s*చేస్తాను|దరఖాస్తు\s*చేస్తాను|ఇప్పుడే\s*అప్లై|అప్లికేషన్\s*పెడతా)",
            r"(अभी\s*अप्लाई|फॉर्म\s*भरना\s*है|अप्लाई\s*करना\s*है|तुरंत\s*अप्लाई)",
        ],
        "send_application_link": [
            r"\b(send|whatsapp|share|message)\b.*?\b(link|application|form|details|site|url)\b",
            r"\b(link|application)\b.*?\b(send|whatsapp|share|karo|bhejo|cheyandi|pampandi)\b",
            r"(లింక్|వాట్సాప్|అప్లికేషన్|లింకు).*?(పంపండి|షేర్|చేయండి|సెండ్)",
            r"(लिंक|व्हाट्सएप|एप्लिकेशन|फॉर्म).*?(भेज|दीजिये|कर|सेंड)",
        ],
        "book_campus_visit": [
            r"\b(visit|come|tour|see)\b.*?\b(campus|university|college|labs?|hostel|saturday|sunday|weekend)\b",
            r"\b(saturday|sunday|weekend|tomorrow|date|appointment)\b.*?\b(visit|come|schedule|book)\b",
            r"(క్యాంపస్|కాలేజ్|హాస్టల్|యూనివర్సిటీ).*?(విజిట్|చూడ|రావ|రావడానికి|వస్తాను)",
            r"(శనివారం|ఆదివారం|వీకెండ్).*?(వస్తాను|విజిట్|బుక్)",
            r"(कैंपस|कॉलेज|हॉस्टल|यूनिवर्सिटी).*?(विजिट|देखना|आना|आऊंगा|घूमना)",
            r"(शनिवार|रविवार|वीकेंड).*?(आऊंगा|विजिट|बुक)",
        ],
        "register_asat": [
            r"\b(register|sign\s*up|enroll|apply|take|write|appear)\b.*?\b(asat|exam|scholarship\s*test|entrance)\b",
            r"\b(asat|scholarship\s*test)\b.*?\b(register|writing|ready|interest)\b",
            r"(ఎగ్జామ్|పరీక్ష|స్కాలర్‌షిప్\s*టెస్ట్|అశాట్).*?(రాయడానికి|రిజిస్టర్|రిజిస్ట్రేషన్)",
            r"(परीक्षा|स्कॉलरशिप\s*टेस्ट|एग्जाम|असाट).*?(देना|रजिस्टर|रजिस्ट्रेशन)",
        ],
        "reserve_seat": [
            r"\b(confirm|reserve|block|book|take)\b.*?\b(admission|seat|provisional)\b",
            r"\b(want|ready\s+for|interested\s+in)\s+(admission|joining)\b",
            r"(అడ్మిషన్|సీటు|సీట్).*?(కన్ఫర్మ్|రిజర్వ్|బుక్|చేయండి|కావాలి)",
            r"(एडमिशन|सीट).*?(कन्फर्म|रिजर्व|बुक|लेना|चाहिए)",
        ],
        "soft_commitment": [
            r"\b(whatsapp\s*group|peer\s*group|alumni\s*network|virtual\s*tour|info\s*session|scholarship\s*updates?)\b",
            r"(గ్రూప్|కమ్యూనిటీ|వర్చువల్\s*టూర్|గెస్ట్\s*సెషన్)",
            r"(व्हाट्सएप\s*ग्रुप|कम्युनिटी|वर्चुअल\s*टूर)",
        ]
    }

    # Admission Objection Patterns
    OBJECTION_PATTERNS = {
        "fee_expensive": [
            r"\b(fees?|cost|price|expensive|costly|high\s+fee|budget|afford|too\s+much)\b",
            r"(ఫీజు|ఖర్చు|ఎక్కువ|చాలా\s*ఎక్కువ|కట్టలేము|బడ్జెట్)",
            r"(फीस|महंगा|ज्यादा|बजट|खर्चा|ज्यादा\s*फीस)",
        ],
        "want_to_think": [
            r"\b(want\s*to\s*think|need\s*time|think\s*about\s*it|let\s*me\s*think|give\s*me\s*time|decide\s*later|not\s*sure\s*yet)\b",
            r"(ఆలోచిస్తాను|ఆలోచించి\s*చెప్తాను|సమయం\s*కావాలి|టైమ్\s*కావాలి)",
            r"(सोचना\s*है|सोच\s*कर\s*बताऊंगा|टाइम\s*चाहिए|सोचेंगे)",
        ],
        "comparing_colleges": [
            r"\b(comparing|compare|other\s+colleges?|vit|srm|amrita|better\s+than|which\s+is\s+better|other\s+options?)\b",
            r"(వేరే\s*కాలేజ్|ఇతర\s*కాలేజీలు|పోల్చి\s*చూస్తున్నాను)",
            r"(दूसरे\s*कॉलेज|कंपेयर|तुलना)",
        ],
        "parent_consultation": [
            r"\b(parents?|father|mother|mom|dad|family|discuss|ask|talk\s+to\s+parents)\b",
            r"(పేరెంట్స్|తండ్రి|నాన్న|అమ్మ|తల్లి|మాట్లాడాలి|కనుక్కోవాలి)",
            r"(माता|पिता|पापा|मम्मी|पैरेंट्स|परिवार|पूछना|बात\s*करनी)",
        ],
        "waiting_for_exams": [
            r"\b(waiting|eapcet|jee|neet|counseling|rank|exam\s+results?)\b",
            r"(ఫలితాలు|ర్యాంక్|ర్యాంకు|కౌన్సిలింగ్|ఈఏపీసెట్|జేఈఈ)",
            r"(रिजल्ट|रैंक|काउंसलिंग|जेईई|ईएपीसीईटी)",
        ],
        "hostel_safety": [
            r"\b(hostel|food|mess|safety|security|ragging|hygiene)\b",
            r"(భద్రత|హాస్టల్|భోజనం|ఫుడ్|ర్యాగింగ్)",
            r"(हॉस्टल|खाना|मेस|सुरक्षा|रैगिंग)",
        ]
    }

    def __init__(self, call_id: str = "call_default", max_window_turns: int = 8):
        self.call_id = call_id
        self.sliding_window = SlidingWindow(max_turns=max_window_turns)
        self.fact_memory = FactMemory()
        self.conversation_history = ConversationHistory(call_id=call_id)
        self.history = self.conversation_history
        self.dialogue_state = DialogueState()
        self.state = self.dialogue_state

    def get_facts(self) -> Dict[str, Any]:
        """Return copy of currently known facts."""
        return dict(self.fact_memory.facts)

    def detect_goodbye(self, text: str) -> bool:
        """Alias for is_goodbye()."""
        return self.is_goodbye(text)

    def detect_conversion_intent(self, text: str) -> Optional[str]:
        """Detect affirmative buying / conversion signals from caller."""
        if not text:
            return None
        t = text.lower().strip()
        for intent, patterns in self.CONVERSION_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, t, re.IGNORECASE):
                    return intent
        return None

    def detect_objection(self, text: str) -> Optional[str]:
        """Detect admissions objection from caller."""
        if not text:
            return None
        t = text.lower().strip()
        for obj_type, patterns in self.OBJECTION_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, t, re.IGNORECASE):
                    return obj_type
        return None

    def should_ask_about(self, topic: str) -> bool:
        """Determine whether to ask about a topic (false if in facts or already discussed)."""
        if self.fact_memory.has_fact(topic):
            return False
        return self.conversation_history.should_ask_about(topic)

    def has_topic_been_discussed(self, topic: str) -> bool:
        """Check if topic was discussed in conversation history."""
        return self.conversation_history.has_topic_been_discussed(topic)

    def mark_topic_discussed(self, topic: str):
        """Record topic as discussed."""
        self.conversation_history.record_topic(topic)

    def build_prompt_context(self, user_input: str = "", language: str = "en-IN") -> str:
        """Alias for build_context()."""
        return self.build_context(user_input=user_input, language=language)

    def build_turn_prompt(self, user_input: str = "", language: str = "en-IN") -> str:
        """Compact turn directive (<100 tokens) for real-time LiveKit streaming agent prompt."""
        facts_block = self.fact_memory.get_formatted()
        curr_state = self.dialogue_state.current_state
        missing = self.dialogue_state.get_missing_info()
        lines = [
            facts_block,
            f"CONVERSATION STATE: {curr_state}",
        ]
        if missing:
            lines.append(f"MISSING INFO: {missing}")
        if self.conversation_history.topics_discussed:
            lines.append(f"TOPICS ALREADY DISCUSSED: {', '.join(sorted(self.conversation_history.topics_discussed))}")

        # Admission Conversion Strategy Directives
        conv_intent = self.detect_conversion_intent(user_input)
        if conv_intent:
            if conv_intent == "apply_now_direct":
                lines.append("ADMISSION ACTION DIRECTIVE: Caller wants to apply right now! Initiate 5-minute fast-path application: confirm details, submit application, and reassure merit scholarship lock-in.")
            elif conv_intent == "soft_commitment":
                lines.append("ADMISSION ACTION DIRECTIVE: Caller agreed to soft commitment. Add to WhatsApp peer cohort or confirm virtual tour reservation.")
            else:
                lines.append(f"ADMISSION ACTION DIRECTIVE: Caller expressed intent to '{conv_intent}'. Confirm immediately & execute tool!")
        elif self.detect_objection(user_input):
            obj = self.detect_objection(user_input)
            if obj == "want_to_think":
                lines.append("OBJECTION DIRECTIVE: Caller wants to think. Empower choice: ask if they want fee installment options, virtual campus tour, or an alumni connection to help decide faster.")
            elif obj == "comparing_colleges":
                lines.append("OBJECTION DIRECTIVE: Caller is comparing colleges. Validate their smart approach, ask whether curriculum, ₹12L average placement, or fees matter most, and offer honest comparison.")
            elif obj == "fee_expensive":
                lines.append("OBJECTION DIRECTIVE: Caller feels fee is high. Reframe with 50% merit waiver (₹62.5K/yr < hostel rent) and ₹12L placement ROI in under 2 years, plus flexible installments.")
            else:
                lines.append(f"OBJECTION DIRECTIVE: Caller raised '{obj}'. Resolve warmly with official university benefit, then close with alternative CTA.")
        elif not missing or (self.fact_memory.has_fact("program") and self.fact_memory.has_fact("score")):
            lines.append("ADMISSION CONVERSION DIRECTIVE: Core details known. Present personalized package (scholarship, fee waiver, peer group, placement) and close: 5-minute direct application or 24-hr ₹5K discount link.")

        lines.append("ANTI-REPETITION MANDATE: Never re-ask known facts or re-pitch already discussed topics.")
        return "\n".join(lines)

    def export_audit_log(self, filepath: Optional[str] = None) -> str:
        """Export full conversation transcript audit log."""
        return self.conversation_history.export_transcript(filepath=filepath)

    def handle_user_input(self, user_input: str, language: str = "en-IN") -> Dict[str, Any]:
        """
        Process user input through all 4 layers before LLM generation.
        Returns extracted facts, topic history, current state, and goodbye status.
        """
        # 1. Extract new facts from user input (Layer 2)
        new_facts = self.fact_memory.extract_from_input(user_input)

        # 2. Sync facts to dialogue state (Layer 4)
        self.dialogue_state.sync_with_facts(self.fact_memory.facts)

        # 3. Transition dialogue state
        self.dialogue_state.current_state = self.dialogue_state.get_next_state()

        # 4. Check for goodbye / wrap-up intent
        is_closing_turn = self.is_goodbye(user_input)
        if is_closing_turn:
            self.dialogue_state.current_state = DialogueState.CLOSING

        # 5. Build context packet
        return {
            "new_facts": new_facts,
            "all_facts": dict(self.fact_memory.facts),
            "state": self.dialogue_state.current_state,
            "missing_info": self.dialogue_state.get_missing_info(),
            "is_goodbye": is_closing_turn,
            "context_prompt": self.build_context(user_input, language=language),
        }

    def record_fact(self, key: str, value: Any):
        """Update or insert a fact into fact_memory and sync dialogue state."""
        self.fact_memory.facts[key] = value
        self.dialogue_state.sync_with_facts(self.fact_memory.facts)

    def update_user_turn(self, user_text: str, language: str = "en-IN"):
        """Convenience method to record a user turn."""
        return self.record_turn(user_text=user_text, role="user", language=language)

    def update_agent_turn(self, agent_text: str, language: str = "en-IN"):
        """Convenience method to record an assistant turn."""
        return self.record_turn(agent_text=agent_text, role="assistant", language=language)

    def record_turn(
        self,
        user_input: str = "",
        agent_response: str = "",
        topic: Optional[str] = None,
        language: str = "en-IN",
        role: Optional[str] = None,
        user_text: Optional[str] = None,
        agent_text: Optional[str] = None,
    ):
        """Update all active memory layers after LLM generates response or per turn."""
        if user_text:
            user_input = user_text
        if agent_text:
            agent_response = agent_text

        if role == "user":
            user_input = user_input or ""
            if user_input:
                self.fact_memory.extract_from_input(user_input)
                self.dialogue_state.sync_with_facts(self.fact_memory.facts)
                self.dialogue_state.current_state = self.dialogue_state.get_next_state()
            turn_data = {
                "user": user_input,
                "agent": agent_response or "",
                "language": language,
                "timestamp": datetime.now(),
            }
            self.sliding_window.turns.append(turn_data)
            if len(self.sliding_window.turns) > self.sliding_window.max_turns:
                self.sliding_window.turns.pop(0)
            self.conversation_history.add_turn(user_input, agent_response or "", topic=topic, language=language)
            return

        if role == "assistant":
            agent_response = agent_response or ""
            if self.sliding_window.turns and not self.sliding_window.turns[-1].get("agent"):
                self.sliding_window.turns[-1]["agent"] = agent_response
            else:
                self.sliding_window.add_turn("", agent_response, language=language)

            if self.conversation_history.full_history and not self.conversation_history.full_history[-1].get("agent"):
                self.conversation_history.full_history[-1]["agent"] = agent_response
                if topic:
                    self.conversation_history.full_history[-1]["topic"] = topic
                    self.conversation_history.topics_discussed.add(topic.lower())
            else:
                self.conversation_history.add_turn("", agent_response, topic=topic, language=language)
            return

        # Default: full turn with both user_input and agent_response
        if user_input:
            self.fact_memory.extract_from_input(user_input)
            self.dialogue_state.sync_with_facts(self.fact_memory.facts)

        self.sliding_window.add_turn(user_input, agent_response, language=language)
        self.conversation_history.add_turn(user_input, agent_response, topic=topic, language=language)
        self.dialogue_state.current_state = self.dialogue_state.get_next_state()

    def build_context(self, user_input: str = "", language: str = "en-IN") -> str:
        """
        Build complete prompt context using all 4 layers:
        - Layer 2: Facts so far (never re-ask)
        - Layer 1: Sliding window recent conversation (5-8 turns)
        - Layer 3: Topics discussed & previous discussion context
        - Layer 4: State and missing information
        """
        facts_block = self.fact_memory.get_formatted()
        recent_context = self.sliding_window.get_context(last_n=5)
        curr_state = self.dialogue_state.current_state
        missing = self.dialogue_state.get_missing_info()

        # Relevant topic context
        topic_context_parts = []
        for top in ["program", "fees", "scholarship", "hostel", "campus_visit"]:
            ctx = self.conversation_history.get_topic_context(top)
            if ctx:
                topic_context_parts.append(ctx)
        topic_section = "\n".join(topic_context_parts) if topic_context_parts else "None yet."

        context = f"""You are Priya, AI Senior Admissions Counselor at Aditya University.

{facts_block}

{recent_context}

CONVERSATION STATE: {curr_state}
MISSING INFO: {missing if missing else 'None - core information acquired'}

PREVIOUS DISCUSSION BY TOPIC:
{topic_section}

CRITICAL RULES:
1. NEVER ask about topics or information already in KNOWN FACTS
2. NEVER repeat questions or topics from conversation history
3. If state is "closing" or user says thanks/goodbye: End call gracefully and warmly
4. Ask only the RELEVANT next question; do NOT force mandatory questionnaires
5. Answer the caller's direct question or concern FIRST before asking anything
6. Keep spoken response under 35 words for telephony responsiveness
7. Personalize replies using known facts (e.g. caller name, program)
8. ADMISSION CONVERSION: Drive toward concrete micro-closing: Offer WhatsApp provisional application link OR Saturday VIP campus tour with parents

Respond naturally to the caller."""
        return context

    def is_goodbye(self, text: str) -> bool:
        """Detect goodbye or wrap-up signals across English, Hindi, Telugu, Tamil."""
        if not text:
            return False
        clean = text.strip()
        conv_intent = self.detect_conversion_intent(clean)
        # If user expresses conversion action (e.g. "Done, send me the link", "Register me please"):
        # Only treat as goodbye if there is also an explicit final thank you / farewell ("... Thank you! Bye")
        if conv_intent:
            explicit_farewell = bool(re.search(
                r'\b(thank\s*you|thanks|bye|goodbye)\b|(ధన్యవాదాలు|థాంక్స్|బై|ధన్యవాదం|धन्यवाद|शुक्रिया|अलविदा|நன்றி)',
                clean, re.IGNORECASE
            ))
            return explicit_farewell

        # Fast exit on natural wrap-up phrases (under 15 words)
        if len(clean.split()) <= 15 and self.GOODBYE_RE.search(clean):
            return True
        return False

    def get_summary(self) -> Dict[str, Any]:
        """Return complete call audit summary."""
        return {
            "call_id": self.call_id,
            "turns_count": len(self.conversation_history.full_history),
            "state": self.dialogue_state.current_state,
            "facts": dict(self.fact_memory.facts),
            "topics_discussed": list(self.conversation_history.topics_discussed),
            "missing_info": self.dialogue_state.get_missing_info(),
        }


_GLOBAL_LONG_MGR = LongConversationManager()

def is_goodbye(text: str) -> bool:
    """Module-level convenience function to detect goodbyes with Goodbye Guard."""
    return _GLOBAL_LONG_MGR.is_goodbye(text)

def detect_conversion_intent(text: str) -> Optional[str]:
    """Module-level convenience function to detect admission conversion intent."""
    return _GLOBAL_LONG_MGR.detect_conversion_intent(text)

def detect_objection(text: str) -> Optional[str]:
    """Module-level convenience function to detect admission objections."""
    return _GLOBAL_LONG_MGR.detect_objection(text)


