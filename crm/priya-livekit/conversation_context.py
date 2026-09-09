# conversation_context.py

from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConversationState:
    current_language: str = "en-IN"
    dominant_language: str = "en-IN"
    language_confidence: float = 0.7
    explicit_language_stated: bool = False
    turn_count: int = 0

    # User profile (persistent)
    user_profile: Dict[str, Any] = field(default_factory=dict)

    # Turn history: [{speaker, text, language, explicit_switch, timestamp, turn_number}]
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # CRM slot tracking: {slot_name: {value, turn, language}}
    slots: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class ConversationContext:
    """
    Layer 2: Maintains conversation state and context hysteresis.
    Prevents random mid-conversation language flips and enforces stability.
    """

    def __init__(self, default_language: str = "en-IN"):
        self.state = ConversationState(
            current_language=default_language,
            dominant_language=default_language
        )
        self.language_switch_history: List[Dict[str, Any]] = []

    def add_turn(self, speaker: str, text: str, language: str, explicit_switch: bool = False):
        """Add a turn to conversation history and update state."""
        self.state.conversation_history.append({
            "speaker": speaker,
            "text": text,
            "language": language,
            "explicit_switch": explicit_switch,
            "timestamp": datetime.now().isoformat(),
            "turn_number": self.state.turn_count
        })

        self.state.turn_count += 1
        self.state.current_language = language

        if explicit_switch:
            self.state.dominant_language = language
            self.state.explicit_language_stated = True
            self.language_switch_history.append({
                "from": self.state.dominant_language,
                "to": language,
                "turn": self.state.turn_count,
                "type": "explicit"
            })
        else:
            # Check for dominant language update over recent turns (e.g. 3 turns in same language)
            user_turns = [t for t in self.state.conversation_history if t.get("speaker") == "user"]
            if len(user_turns) >= 2:
                recent_langs = [t["language"] for t in user_turns[-3:]]
                if recent_langs.count(language) >= 2 and language != self.state.dominant_language:
                    self.update_dominant_language(language)

    def set_user_profile(self, profile: Dict[str, Any]):
        """Set user profile (e.g., student preferences, historic preferred language)."""
        self.state.user_profile.update(profile)
        if "preferred_language" in profile:
            self.state.dominant_language = profile["preferred_language"]
            self.state.language_confidence = 0.85

    def get_expected_language(self) -> Dict[str, Any]:
        """
        Determine expected language based on conversation state.
        Returns expected language and required confidence threshold to switch away.
        """
        # Rule 1: Explicit switch always takes highest precedence
        if self.state.conversation_history:
            for turn in reversed(self.state.conversation_history[-4:]):
                if turn.get("explicit_switch"):
                    return {
                        "expected_language": turn["language"],
                        "confidence": 0.98,
                        "reason": "Recent explicit switch request",
                        "required_switch_confidence": 0.95,  # Needs near certainty to deviate
                        "weight": 0.95
                    }

        # Rule 2: Conversation dominance (sticky language once stabilized)
        if self.state.dominant_language:
            return {
                "expected_language": self.state.dominant_language,
                "confidence": 0.85,
                "reason": f"Conversation active in {self.state.dominant_language}",
                "required_switch_confidence": 0.88,  # Needs strong signal (88%+) to switch
                "weight": 0.85
            }

        # Rule 3: User's historical profile preference
        if self.state.user_profile.get("preferred_language"):
            return {
                "expected_language": self.state.user_profile["preferred_language"],
                "confidence": 0.75,
                "reason": "User profile preference",
                "required_switch_confidence": 0.82,
                "weight": 0.75
            }

        # Rule 4: Default fallback language
        return {
            "expected_language": self.state.current_language or "en-IN",
            "confidence": 0.50,
            "reason": "Default language",
            "required_switch_confidence": 0.80,
            "weight": 0.50
        }

    def update_dominant_language(self, language: str):
        """Update the dominant language for the active session."""
        if language != self.state.dominant_language:
            old = self.state.dominant_language
            self.state.dominant_language = language
            self.language_switch_history.append({
                "from": old,
                "to": language,
                "turn": self.state.turn_count,
                "type": "detected"
            })

    def record_crm_slot(self, slot_name: str, value: str):
        """Record collected information (e.g. name, rank, program)."""
        self.state.slots[slot_name] = {
            "value": value,
            "turn": self.state.turn_count,
            "language": self.state.current_language
        }

    def get_slot(self, slot_name: str) -> Optional[str]:
        """Retrieve stored slot value."""
        slot_data = self.state.slots.get(slot_name)
        if slot_data:
            return slot_data.get("value")
        return None

    def is_slot_filled(self, slot_name: str) -> bool:
        """Check if a slot has been populated."""
        return slot_name in self.state.slots

    def get_summary(self) -> Dict[str, Any]:
        """Return diagnostic state summary."""
        return {
            "current_language": self.state.current_language,
            "dominant_language": self.state.dominant_language,
            "turn_count": self.state.turn_count,
            "total_switches": len(self.language_switch_history),
            "explicit_switches": sum(1 for s in self.language_switch_history if s.get("type") == "explicit"),
            "detected_switches": sum(1 for s in self.language_switch_history if s.get("type") == "detected"),
            "filled_slots": list(self.state.slots.keys()),
            "user_profile": self.state.user_profile
        }
