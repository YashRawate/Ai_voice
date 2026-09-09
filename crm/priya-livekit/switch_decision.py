# switch_decision.py

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any


@dataclass
class SwitchDecision:
    should_switch: bool
    target_language: Optional[str] = None
    reason: str = ""
    confidence: float = 0.0
    action: str = "stay"  # "switch", "stay", "ask_clarification", "ask_repeat"


class LanguageSwitchDecider:
    """
    Layer 4: Decision logic for language switching.
    Enforces a 4-gate verification process to eliminate erratic flips.
    """

    def __init__(self, max_switches_per_call: int = 5, allowed_languages: Optional[set] = None):
        self.switch_history: List[Dict[str, Any]] = []
        self.max_switches_per_call = max_switches_per_call
        self.allowed_languages = allowed_languages or {"en-IN", "te-IN", "hi-IN", "ta-IN"}

    async def should_switch_language(
        self,
        audio_quality: Dict[str, Any],
        context_expected: Dict[str, Any],
        detected: Dict[str, Any]
    ) -> SwitchDecision:
        """
        Evaluate candidate language against 4 sequential gates:
        Gate 1: Audio Quality Gate
        Gate 2: Stability / Switch Quota Gate
        Gate 3: Confidence Threshold Gate
        Gate 4: Actual Differential & Allowlist Gate
        """
        # ===== GATE 1: Audio Quality Gate =====
        if not audio_quality.get("is_valid", False):
            reason_str = audio_quality.get("reason", "Invalid audio quality")
            return SwitchDecision(
                should_switch=False,
                reason=f"Gate 1 Blocked (Audio): {reason_str}",
                action="stay",
                confidence=0.0
            )

        # ===== GATE 2: Excessive Switching Gate =====
        if len(self.switch_history) >= self.max_switches_per_call:
            return SwitchDecision(
                should_switch=False,
                reason=f"Gate 2 Blocked (Stability): Max switches reached ({len(self.switch_history)}/{self.max_switches_per_call})",
                action="stay",
                confidence=0.0
            )

        # ===== GATE 3: Confidence Threshold Gate =====
        required_confidence = float(context_expected.get("required_switch_confidence", 0.85))
        detected_confidence = float(detected.get("confidence", 0.0))

        if detected_confidence < required_confidence:
            return SwitchDecision(
                should_switch=False,
                reason=f"Gate 3 Blocked (Confidence): {detected_confidence:.2f} < required {required_confidence:.2f}",
                action="stay",
                confidence=detected_confidence
            )

        # ===== GATE 4: Language Mismatch & Allowlist Gate =====
        detected_language = detected.get("detected_language", "en-IN")
        expected_language = context_expected.get("expected_language", "en-IN")

        if detected_language not in self.allowed_languages:
            return SwitchDecision(
                should_switch=False,
                reason=f"Gate 4 Blocked (Allowlist): {detected_language} not in {self.allowed_languages}",
                action="stay",
                confidence=detected_confidence
            )

        if detected_language == expected_language:
            return SwitchDecision(
                should_switch=False,
                reason=f"Gate 4 Passed (No-op): Already in expected language {expected_language}",
                action="stay",
                confidence=detected_confidence
            )

        # All 4 gates passed: Strong verified signal
        self.switch_history.append({
            "from": expected_language,
            "to": detected_language,
            "confidence": detected_confidence
        })

        return SwitchDecision(
            should_switch=True,
            target_language=detected_language,
            reason=f"All gates passed: switching {expected_language} -> {detected_language} (conf: {detected_confidence:.2f})",
            confidence=detected_confidence,
            action="switch"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Return runtime statistics."""
        return {
            "total_switches": len(self.switch_history),
            "switch_history": self.switch_history
        }
