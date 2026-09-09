# noise_resilience_handler.py

from dataclasses import dataclass
from typing import Dict, Optional, Any


@dataclass
class RecoveryAction:
    action: str  # "ask_repeat", "ask_clarification", "stay", "confirm"
    message: Optional[str] = None
    stay_in_language: str = "en-IN"
    reason: str = ""


class NoiseResilienceHandler:
    """
    Layer 6: Graceful failure and noise resilience.
    Instead of hallucinating a random language switch, this handler triggers
    a localized clarification or repeat prompt in the caller's active language.
    """

    def __init__(self):
        self.recovery_messages = {
            "ask_repeat": {
                "en-IN": "I couldn't hear you clearly. Could you please repeat that?",
                "hi-IN": "माफ़ कीजिए, आपकी आवाज़ साफ़ नहीं आई। कृपया दोबारा बोलेंगे?",
                "te-IN": "క్షమించండి, మీ మాట స్పష్టంగా వినిపించలేదు. దయచేసి మళ్లీ చెప్పగలరా?",
                "ta-IN": "மன்னிக்கவும், உங்கள் குரல் தெளிவாகக் கேட்கவில்லை. மீண்டும் சொல்ல முடியுமா?"
            },

            "ask_clarification": {
                "en-IN": "Should I continue in English or would you prefer another language like Telugu or Hindi?",
                "hi-IN": "क्या मैं हिंदी में बात जारी रखूँ या आप किसी अन्य भाषा में बात करना चाहेंगे?",
                "te-IN": "నేను తెలుగులో మాట్లాడటం కొనసాగించాలా లేక ఇతర భాషలో మాట్లాడాలా?",
                "ta-IN": "நான் தமிழிலேயே பேசவா அல்லது வேறு மொழியில் தொடரவா?"
            },

            "confirm_language": {
                "en-IN": "I noticed you might want to switch languages. Should we switch to {language}?",
                "hi-IN": "क्या आप {language} में बात करना चाहते हैं?",
                "te-IN": "మీరు {language} కి మారాలనుకుంటున్నారా?",
                "ta-IN": "நீங்கள் {language} க்கு மாற விரும்புகிறீர்களா?"
            }
        }

    async def handle_detection_failure(
        self,
        audio_quality: Dict[str, Any],
        current_language: str = "en-IN",
        detection_result: Optional[Dict[str, Any]] = None
    ) -> RecoveryAction:
        """
        Evaluate failure severity and return appropriate localized recovery prompt.
        """
        lang = current_language if current_language in self.recovery_messages["ask_repeat"] else "en-IN"
        noise_level = audio_quality.get("noise_level", "unknown")
        is_valid = audio_quality.get("is_valid", True)
        confidence = float(audio_quality.get("confidence", 0.0))

        # Case 1: Audio is too noisy or clipped -> ask to repeat
        if not is_valid or noise_level in ["noisy", "very_noisy", "clipped"]:
            msg = self.recovery_messages["ask_repeat"].get(lang, self.recovery_messages["ask_repeat"]["en-IN"])
            return RecoveryAction(
                action="ask_repeat",
                message=msg,
                stay_in_language=lang,
                reason=f"Degraded audio quality ({noise_level})"
            )

        # Case 2: Audio is valid, but language detection confidence is critically low (< 0.40)
        if detection_result is not None:
            det_conf = float(detection_result.get("confidence", 0.0))
            if det_conf < 0.40:
                msg = self.recovery_messages["ask_clarification"].get(lang, self.recovery_messages["ask_clarification"]["en-IN"])
                return RecoveryAction(
                    action="ask_clarification",
                    message=msg,
                    stay_in_language=lang,
                    reason=f"Ambiguous language signal (confidence: {det_conf:.2f})"
                )

        # Default fallback: Stay in current language safely
        return RecoveryAction(
            action="stay",
            stay_in_language=lang,
            reason="Preserving active conversation language"
        )
