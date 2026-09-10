# test_acoustic_pipeline.py
"""
Unit and Integration Test Suite for AdmitAI Priya Acoustic Pipeline.
Tests:
1. AEC (Adaptive Echo Canceller)
2. Spectral Noise Suppressor
3. SNR Pre-Filter Gate (8 dB floor)
4. Two-Tier VAD & Debounce Gate (0.50 normal vs 0.75 speaking, 6-frame debounce)
5. Semantic Confirmation Gate (coughs, fillers vs genuine interruptions)
6. Integrated Pipeline End-to-End
"""

import unittest
import numpy as np
from priya.audio.acoustic_pipeline import (
    AdaptiveEchoCanceller,
    SpectralNoiseSuppressor,
    SNRGate,
    BargeInGate,
    SemanticConfirmationGate,
    AcousticPipeline,
)


class TestAcousticPipeline(unittest.TestCase):

    def setUp(self):
        self.sample_rate = 16000
        # 20ms frame at 16kHz = 320 samples (640 bytes)
        self.frame_len = 320

    def _generate_sine_frame(self, freq: float = 440.0, amplitude: float = 0.5) -> bytes:
        t = np.linspace(0, 0.02, self.frame_len, endpoint=False)
        sine = (np.sin(2 * np.pi * freq * t) * amplitude * 32767).astype(np.int16)
        return sine.tobytes()

    def _generate_noise_frame(self, amplitude: float = 0.02) -> bytes:
        noise = (np.random.normal(0, amplitude, self.frame_len) * 32767).astype(np.int16)
        return noise.tobytes()

    # ── 1. Acoustic Echo Cancellation (AEC) ──────────────────────────────────
    def test_aec_cancellation(self):
        aec = AdaptiveEchoCanceller(filter_length=64, mu=0.1)
        ref_frame = self._generate_sine_frame(freq=300.0, amplitude=0.6)
        
        # Feed reference signal
        for _ in range(10):
            aec.feed_reference(ref_frame)

        # Create simulated echo (reference attenuated by 0.5)
        echo_frame = (np.frombuffer(ref_frame, dtype=np.int16) * 0.5).astype(np.int16).tobytes()

        # Over multiple frames, NLMS should adapt and attenuate echo
        residuals = []
        for _ in range(30):
            clean = aec.cancel_echo(echo_frame)
            res_rms = np.sqrt(np.mean(np.frombuffer(clean, dtype=np.int16).astype(np.float32) ** 2))
            residuals.append(res_rms)

        # Verify filter adapts and residual error is lower than initial input
        initial_rms = np.sqrt(np.mean(np.frombuffer(echo_frame, dtype=np.int16).astype(np.float32) ** 2))
        self.assertLess(residuals[-1], initial_rms, "AEC should adapt and reduce echo residual energy")

    # ── 2. Spectral Noise Suppression ────────────────────────────────────────
    def test_spectral_noise_suppression(self):
        suppressor = SpectralNoiseSuppressor(sample_rate=self.sample_rate, alpha=2.0)
        noise_frame = self._generate_noise_frame(amplitude=0.03)

        # Train noise profile on silence/stationary noise
        for _ in range(10):
            suppressor.suppress_noise(noise_frame, is_speech=False)

        # Apply noise suppression
        clean = suppressor.suppress_noise(noise_frame, is_speech=True)
        raw_energy = np.mean(np.abs(np.frombuffer(noise_frame, dtype=np.int16)))
        clean_energy = np.mean(np.abs(np.frombuffer(clean, dtype=np.int16)))

        self.assertLess(clean_energy, raw_energy, "Spectral noise suppressor should attenuate background noise")

    # ── 3. SNR Pre-Filter Gate ───────────────────────────────────────────────
    def test_snr_gate(self):
        snr_gate = SNRGate()
        # Set realistic noise floor
        snr_gate.update_noise_floor(0.01)

        low_snr_frame = self._generate_noise_frame(amplitude=0.005)
        high_snr_frame = self._generate_sine_frame(freq=500.0, amplitude=0.4)

        self.assertFalse(snr_gate.passes_snr_gate(low_snr_frame), "Low-SNR frame (< 8dB) must be rejected")
        self.assertTrue(snr_gate.passes_snr_gate(high_snr_frame), "High-SNR speech frame must pass gate")

    # ── 4. Two-Tier VAD & Debounce Gate ──────────────────────────────────────
    def test_debounce_gate_requires_consecutive_frames(self):
        gate = BargeInGate()

        # 3 frames of speech followed by silence should NOT trigger
        for _ in range(3):
            self.assertFalse(gate.update(0.80, is_assistant_speaking=True))
        gate.update(0.10, is_assistant_speaking=True)  # silence resets counter
        self.assertEqual(gate.consecutive_speech, 0)

        # 6 consecutive frames of speech MUST trigger
        triggered = False
        for _ in range(6):
            if gate.update(0.80, is_assistant_speaking=True):
                triggered = True
        self.assertTrue(triggered, "Debounce gate must trigger on 6 consecutive frames")

    def test_two_tier_threshold(self):
        gate = BargeInGate()

        # VAD probability 0.60:
        # In normal turn-taking (assistant not speaking), 0.60 > 0.50 -> counts as speech
        for _ in range(5):
            gate.update(0.60, is_assistant_speaking=False)
        self.assertEqual(gate.consecutive_speech, 5)

        # Reset gate
        gate.reset()

        # While assistant IS speaking, threshold is 0.75 -> 0.60 is REJECTED
        for _ in range(6):
            fired = gate.update(0.60, is_assistant_speaking=True)
            self.assertFalse(fired, "VAD probability 0.60 must not trigger barge-in while assistant speaks")
        self.assertEqual(gate.consecutive_speech, 0)

    # ── 5. Semantic Confirmation Gate ────────────────────────────────────────
    def test_semantic_confirmation_gate(self):
        gate = SemanticConfirmationGate(min_chars=4)

        # Fillers and coughs must be rejected
        self.assertFalse(gate.is_confirmed_speech(""))
        self.assertFalse(gate.is_confirmed_speech("um"))
        self.assertFalse(gate.is_confirmed_speech("uh"))
        self.assertFalse(gate.is_confirmed_speech("hmm"))
        self.assertFalse(gate.is_confirmed_speech("cough"))
        self.assertFalse(gate.is_confirmed_speech("you"))
        self.assertFalse(gate.is_confirmed_speech("hi"))  # < 4 chars

        # Genuine questions must be accepted
        self.assertTrue(gate.is_confirmed_speech("Wait a second"))
        self.assertTrue(gate.is_confirmed_speech("What is the fee?"))
        self.assertTrue(gate.is_confirmed_speech("CSE details please"))

    # ── 6. Integrated Acoustic Pipeline ──────────────────────────────────────
    def test_full_acoustic_pipeline_end_to_end(self):
        pipeline = AcousticPipeline(sample_rate=self.sample_rate)
        pipeline.set_assistant_speaking(True)

        # Send low-level noise frame: should be filtered and not trigger barge-in
        noise = self._generate_noise_frame(amplitude=0.003)
        clean, fired, prob = pipeline.process_frame(noise)
        self.assertFalse(fired, "Ambient noise should not fire barge-in")

        # Send sustained speech signal (varying vocal pitch like human speech): should debounce and trigger
        fired_any = False
        for i in range(10):
            freq = 200.0 + i * 15.0  # Dynamic human vocal frequency
            t = np.linspace(0, 0.02, self.frame_len, endpoint=False)
            speech = (np.sin(2 * np.pi * freq * t) * 0.5 * 32767).astype(np.int16).tobytes()
            _, fired, _ = pipeline.process_frame(speech)
            if fired:
                fired_any = True

        self.assertTrue(fired_any, "Sustained speech must trigger debounced barge-in")
        # Semantic check
        self.assertFalse(pipeline.confirm_barge_in("um"))
        self.assertTrue(pipeline.confirm_barge_in("Tell me about scholarships"))


if __name__ == "__main__":
    unittest.main()
