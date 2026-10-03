# test_speaker_interruption.py
"""
Comprehensive Test Suite for Noise-Resistant Interruption & Speaker Verification System.
Validates:
  1. SpeakerVerifier:
     - Voice profile enrollment
     - Verified caller similarity match (>0.65)
     - Rejection of nearby / secondary speaker (<0.65)
  2. MediaDetector:
     - Differentiates clean voice from polyphonic background music / reels
  3. SemanticTurnValidator:
     - Suppresses passive backchannels ('hmm', 'uh-huh', 'yeah', 'ok', 'haan', 'sare') during assistant speech
     - Allows explicit barge-in keywords ('wait', 'stop', 'actually', 'no', 'ruko', 'aagandi')
     - Allows meaningful questions during assistant speech
     - Allows normal utterances when assistant is silent
     - Drops noise/silence artifacts
  4. InterruptionController:
     - Central multi-signal arbitration
     - Generates structured JSON audit logs
     - Rejects short bursts (<350ms)
     - Rejects media / music
     - Rejects nearby speakers
     - Rejects backchannels
     - Triggers TTS interruption ONLY on genuine caller barge-in
  5. AcousticPipeline Integration:
     - End-to-end caller enrollment and confirm_barge_in flow
"""

import unittest
import numpy as np
import json
from priya.audio.interruption_controller import (
    SpeakerVerifier,
    MediaDetector,
    SemanticTurnValidator,
    InterruptionController,
    InterruptionDecision,
)
from priya.audio.acoustic_pipeline import AcousticPipeline


def generate_synthetic_voice(
    duration_s: float = 1.0,
    sample_rate: int = 16000,
    f0: float = 140.0,
    formants: tuple = (500.0, 1500.0, 2500.0),
    noise_level: float = 0.02
) -> bytes:
    """Generates synthetic voiced speech with fundamental frequency and formant harmonics."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    signal = np.zeros_like(t)

    # Harmonics around fundamental frequency f0
    for h in range(1, 15):
        freq = h * f0
        if freq >= sample_rate / 2:
            break
        # Apply formant resonance weighting
        gain = 0.0
        for f_res in formants:
            bw = 100.0
            gain += np.exp(-((freq - f_res) ** 2) / (2 * (bw ** 2)))
        signal += (gain + 0.1 / h) * np.sin(2 * np.pi * freq * t)

    if noise_level > 0:
        signal += np.random.normal(0, noise_level, size=len(t))

    # Normalize to 16-bit PCM range
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = signal / max_val * 0.7
    pcm = (signal * 32767).astype(np.int16).tobytes()
    return pcm


def generate_synthetic_music(
    duration_s: float = 1.0,
    sample_rate: int = 16000
) -> bytes:
    """Generates synthetic polyphonic music / reel audio with dense high frequencies."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    # Dense multi-chord frequencies spanning wide band
    notes = [220, 277, 330, 440, 554, 659, 880, 1760, 3520, 4200, 5000]
    signal = np.zeros_like(t)
    for freq in notes:
        signal += 0.15 * np.sin(2 * np.pi * freq * t)
    # Add high-frequency dispersion
    signal += 0.08 * np.sin(2 * np.pi * 4500 * t)
    max_val = np.max(np.abs(signal))
    signal = signal / max_val * 0.7
    return (signal * 32767).astype(np.int16).tobytes()


class TestSpeakerInterruption(unittest.TestCase):

    def setUp(self):
        self.sample_rate = 16000
        # Caller synthetic voice (f0 = 130 Hz, typical male/pitch profile)
        self.caller_audio = generate_synthetic_voice(
            duration_s=1.0, sample_rate=self.sample_rate, f0=130.0, formants=(500, 1500, 2500)
        )
        # Secondary nearby person voice (f0 = 240 Hz, distinct female/child pitch profile)
        self.nearby_person_audio = generate_synthetic_voice(
            duration_s=1.0, sample_rate=self.sample_rate, f0=240.0, formants=(800, 1900, 3100)
        )
        # Background music / reels audio
        self.music_audio = generate_synthetic_music(
            duration_s=1.0, sample_rate=self.sample_rate
        )

    # ── Test 1: SpeakerVerifier Profile & Similarity ──────────────────────────
    def test_speaker_verifier_profile_match_and_mismatch(self):
        verifier = SpeakerVerifier(sample_rate=self.sample_rate, similarity_threshold=0.65)
        self.assertFalse(verifier.is_enrolled)

        # Before enrollment, caller similarity returns 1.0 (safe fallback)
        self.assertEqual(verifier.verify_speaker(self.caller_audio), 1.0)

        # Enroll caller turn
        verifier.enroll_caller(self.caller_audio)
        self.assertTrue(verifier.is_enrolled)

        # Caller speaking again should produce very high similarity (> 0.85)
        caller_sim = verifier.verify_speaker(self.caller_audio)
        self.assertGreater(caller_sim, 0.85, f"Expected high caller similarity, got {caller_sim}")

        # Nearby person speaking should produce lower similarity (< 0.65)
        nearby_sim = verifier.verify_speaker(self.nearby_person_audio)
        self.assertLess(nearby_sim, 0.65, f"Expected nearby speaker rejected, got {nearby_sim}")

    # ── Test 2: MediaDetector Differentiates Voice from Music ────────────────
    def test_media_detector_music_vs_voice(self):
        detector = MediaDetector(sample_rate=self.sample_rate, media_threshold=0.55)

        voice_prob = detector.detect_media_probability(self.caller_audio)
        music_prob = detector.detect_media_probability(self.music_audio)

        self.assertLess(voice_prob, 0.55, f"Expected low media prob for voice, got {voice_prob}")
        self.assertGreaterEqual(music_prob, 0.55, f"Expected high media prob for music/reel, got {music_prob}")

    # ── Test 3: SemanticTurnValidator Backchannel vs Barge-In ─────────────────
    def test_semantic_turn_validator(self):
        validator = SemanticTurnValidator()

        # When assistant is speaking:
        # Passive backchannels should NOT interrupt
        for backchannel in ["hmm", "uh-huh", "yeah", "ok", "haan", "theek hai", "sare", "mhm"]:
            should_interrupt, reason = validator.is_meaningful_turn(backchannel, is_assistant_speaking=True)
            self.assertFalse(should_interrupt, f"Backchannel '{backchannel}' should not interrupt")
            self.assertEqual(reason, "BACKCHANNEL_REJECTED")

        # Explicit barge-in keywords should ALWAYS interrupt
        for trigger in ["wait", "stop", "hold on", "actually", "no", "ruko", "aagandi"]:
            should_interrupt, reason = validator.is_meaningful_turn(trigger, is_assistant_speaking=True)
            self.assertTrue(should_interrupt, f"Trigger '{trigger}' should interrupt")
            self.assertEqual(reason, "EXPLICIT_BARGE_IN_KEYWORD")

        # Intentional questions should interrupt
        question = "What is the fee for Computer Science?"
        should_interrupt, reason = validator.is_meaningful_turn(question, is_assistant_speaking=True)
        self.assertTrue(should_interrupt)
        self.assertEqual(reason, "MEANINGFUL_INTERRUPTION")

        # Empty / Noise transcripts should never interrupt
        for junk in ["", "   ", "...", "[noise]", "[cough]"]:
            should_interrupt, _ = validator.is_meaningful_turn(junk, is_assistant_speaking=True)
            self.assertFalse(should_interrupt)

        # When assistant is NOT speaking, normal speech is accepted
        should_interrupt, reason = validator.is_meaningful_turn("Yeah, my name is Rahul", is_assistant_speaking=False)
        self.assertTrue(should_interrupt)
        self.assertEqual(reason, "NORMAL_USER_TURN")

    # ── Test 4: InterruptionController End-to-End Decision Matrix ────────────
    def test_interruption_controller_scenarios(self):
        controller = InterruptionController(sample_rate=self.sample_rate)

        # Enroll caller voice
        controller.enroll_caller_turn(self.caller_audio)

        # Scenario A: Assistant NOT speaking -> should_interrupt is False
        controller.set_assistant_speaking(False)
        decision = controller.evaluate(
            audio_bytes=self.caller_audio, transcript="Hello", speech_duration_ms=500.0
        )
        self.assertFalse(decision.should_interrupt)
        self.assertEqual(decision.candidate_type, "NORMAL_TURN")

        # Assistant starts speaking
        controller.set_assistant_speaking(True)

        # Scenario B: Noise burst / short duration (< 350ms) -> REJECT
        decision_short = controller.evaluate(
            audio_bytes=self.caller_audio[:1600],  # 50ms
            transcript="Wait",
            speech_duration_ms=50.0
        )
        self.assertFalse(decision_short.should_interrupt)
        self.assertEqual(decision_short.candidate_type, "NOISE")
        self.assertEqual(decision_short.reason, "SPEECH_DURATION_TOO_SHORT")

        # Scenario C: Instagram / YouTube Reel / TV Music -> REJECT
        decision_media = controller.evaluate(
            audio_bytes=self.music_audio,
            transcript="music audio",
            speech_duration_ms=600.0
        )
        self.assertFalse(decision_media.should_interrupt)
        self.assertEqual(decision_media.candidate_type, "MEDIA")
        self.assertEqual(decision_media.reason, "MEDIA_OR_MUSIC_DETECTED")

        # Scenario D: Nearby Person Speaking (Different voice profile) -> REJECT
        decision_nearby = controller.evaluate(
            audio_bytes=self.nearby_person_audio,
            transcript="Tell me the fee",
            speech_duration_ms=500.0
        )
        self.assertFalse(decision_nearby.should_interrupt)
        self.assertEqual(decision_nearby.candidate_type, "NON_CALLER_SPEAKER")
        self.assertEqual(decision_nearby.reason, "SPEAKER_MISMATCH_NEARBY_PERSON")

        # Scenario E: Passive Caller Backchannel ("hmm", "uh-huh") -> REJECT
        decision_backchannel = controller.evaluate(
            audio_bytes=self.caller_audio,
            transcript="hmm",
            speech_duration_ms=450.0
        )
        self.assertFalse(decision_backchannel.should_interrupt)
        self.assertEqual(decision_backchannel.candidate_type, "BACKCHANNEL")
        self.assertEqual(decision_backchannel.reason, "BACKCHANNEL_REJECTED")

        # Scenario F: Caller Genuine Barge-In ("Wait, tell me the fee") -> INTERRUPT!
        decision_caller = controller.evaluate(
            audio_bytes=self.caller_audio,
            transcript="Wait, tell me about CSE fee",
            speech_duration_ms=500.0
        )
        self.assertTrue(decision_caller.should_interrupt)
        self.assertEqual(decision_caller.candidate_type, "CALLER")

        # Verify JSON audit log contains all required fields
        json_log = json.loads(decision_caller.to_json())
        self.assertEqual(json_log["decision"], "INTERRUPT")
        self.assertEqual(json_log["candidate_type"], "CALLER")
        self.assertIn("speaker_similarity", json_log["metrics"])
        self.assertIn("media_probability", json_log["metrics"])

    # ── Test 5: AcousticPipeline Integrated Barge-In Flow ────────────────────
    def test_acoustic_pipeline_confirm_barge_in(self):
        pipeline = AcousticPipeline(sample_rate=self.sample_rate)

        # Feed caller audio into pipeline when assistant is NOT speaking
        pipeline.set_assistant_speaking(False)
        frame_size = 320 * 2  # 20ms at 16kHz
        for i in range(0, len(self.caller_audio), frame_size):
            chunk = self.caller_audio[i:i + frame_size]
            pipeline.process_frame(chunk)

        # Caller turn ends, enroll caller
        pipeline.enroll_caller()
        self.assertTrue(pipeline.interruption_controller.speaker_verifier.is_enrolled)

        # Assistant speaks
        pipeline.set_assistant_speaking(True)

        # 1. Nearby person speaking over assistant -> confirm_barge_in returns False
        barge_in_nearby = pipeline.confirm_barge_in(
            partial_stt_text="What is the fee",
            audio_bytes=self.nearby_person_audio
        )
        self.assertFalse(barge_in_nearby, "Nearby person speech should be rejected")

        # Reset state after test
        pipeline.set_assistant_speaking(True)

        # 2. Backchannel "hmm" by caller -> confirm_barge_in returns False
        barge_in_backchannel = pipeline.confirm_barge_in(
            partial_stt_text="hmm",
            audio_bytes=self.caller_audio
        )
        self.assertFalse(barge_in_backchannel, "Backchannel 'hmm' should not interrupt TTS")

        # Reset state after test
        pipeline.set_assistant_speaking(True)

        # 3. Caller explicit barge-in "Wait, listen" -> confirm_barge_in returns True
        barge_in_caller = pipeline.confirm_barge_in(
            partial_stt_text="Wait, listen please",
            audio_bytes=self.caller_audio
        )
        self.assertTrue(barge_in_caller, "Legitimate caller barge-in should interrupt TTS")


if __name__ == "__main__":
    unittest.main()
