# crm/priya-livekit/test_noise_interruption.py
"""
Test Suite for Noise-Resistant Interruption and Turn Detection.
Verifies:
1. Rejection of background noise artifacts ([noise], coughs, breathing, dots)
2. Acceptance of legitimate short interjections ('Wait', 'Stop', 'Yes', 'No')
3. Multilingual genuine speech preservation ('Haan', 'Sare', 'Nahi')
4. Environment variable configuration for VAD and interruption duration
5. Two-tier debounced barge-in gate behavior
"""

import os
import unittest
from dotenv import load_dotenv

load_dotenv()

from session_manager import is_valid_user_speech
from priya.audio.acoustic_pipeline import BargeInGate


class TestNoiseResistantInterruption(unittest.TestCase):

    def test_1_reject_noise_artifacts(self):
        """Noise artifacts and non-speech sounds MUST be rejected."""
        noise_samples = [
            "",
            "   ",
            "[noise]",
            "[music]",
            "[silence]",
            "[cough]",
            "[laughter]",
            "[applause]",
            "[sigh]",
            "...",
            ".",
            "?",
            "---",
            "*",
            "um",
            "uh",
        ]
        for sample in noise_samples:
            self.assertFalse(
                is_valid_user_speech(sample),
                f"Expected '{sample}' to be rejected as noise artifact."
            )

    def test_2_accept_legitimate_short_interjections(self):
        """Short legitimate speech interjections MUST be accepted for barge-in."""
        legit_words = [
            "Wait",
            "Stop",
            "Yes",
            "No",
            "Hello",
            "Actually",
            "Listen",
            "Wait please",
        ]
        for word in legit_words:
            self.assertTrue(
                is_valid_user_speech(word),
                f"Expected '{word}' to be accepted as genuine speech."
            )

    def test_3_accept_multilingual_interjections(self):
        """Hindi, Telugu, and Tamil speech interjections MUST be accepted."""
        multilingual_words = [
            "हाँ",       # Haan (Hindi)
            "नहीं",      # Nahi (Hindi)
            "रुको",      # Ruko (Hindi)
            "సరే",       # Sare (Telugu)
            "ఆగండి",     # Aagandi / Wait (Telugu)
            "అవును",     # Avunu (Telugu)
            "நன்றி",     # Nandri (Tamil)
        ]
        for word in multilingual_words:
            self.assertTrue(
                is_valid_user_speech(word),
                f"Expected multilingual speech '{word}' to be accepted."
            )

    def test_4_environment_variable_configuration(self):
        """Verify that recommended noise-resistant parameters are configured."""
        min_interruption_ms = float(os.getenv("MIN_INTERRUPTION_DURATION_MS", "0"))
        vad_speech_thresh = float(os.getenv("VAD_SPEECH_THRESHOLD", "0"))
        user_vad_thresh = float(os.getenv("USER_VAD_THRESHOLD", "0"))
        min_words = int(os.getenv("INTERRUPTION_MIN_WORDS", "0"))

        self.assertGreaterEqual(min_interruption_ms, 300.0, "Interruption duration must be >= 300ms")
        self.assertGreaterEqual(vad_speech_thresh, 0.70, "VAD speech threshold must be >= 0.70")
        self.assertGreaterEqual(user_vad_thresh, 0.60, "User VAD threshold must be >= 0.60")
        self.assertGreaterEqual(min_words, 1, "Interruption min_words must be >= 1")

    def test_5_barge_in_gate_debounce(self):
        """Verify that single-frame noise bursts are rejected by BargeInGate."""
        gate = BargeInGate()

        # Frame 1 with high probability (e.g. mic pop or fan spike)
        self.assertFalse(gate.update(0.95, is_assistant_speaking=True))

        # Noise disappears on frame 2
        self.assertFalse(gate.update(0.30, is_assistant_speaking=True))
        self.assertEqual(gate.consecutive_speech, 0, "Consecutive counter should reset on low prob")

        # Now simulate continuous speech across 6 consecutive frames
        for _ in range(5):
            self.assertFalse(gate.update(0.90, is_assistant_speaking=True))

        # 6th frame fires confirmed barge-in
        self.assertTrue(gate.update(0.90, is_assistant_speaking=True))


if __name__ == "__main__":
    unittest.main()
