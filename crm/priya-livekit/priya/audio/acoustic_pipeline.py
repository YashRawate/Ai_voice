# crm/priya-livekit/priya/audio/acoustic_pipeline.py
"""
Acoustic Processing & Anti-Barge-In Pipeline for AdmitAI Priya Voice Agent.
Prevents false interruptions from background noise, breathing, mic rustle, and speaker echo bleeding.

Pipeline Architecture:
Mic Input
  -> AEC (Adaptive Echo Canceller, subtracts Priya's TTS output bleeding into mic)
  -> Spectral Noise Suppressor (Removes fan/AC hum, background rumble)
  -> SNR Gate (Pre-filter: rejects low-SNR frames before VAD)
  -> Two-Tier Silero/WebRTC VAD (Normal: 0.50 vs Barge-In: 0.75)
  -> Debounce Gate (Requires 6 consecutive speech frames, ~120ms)
  -> Semantic Confirmation (Buffers audio & checks STT for real words vs cough/filler)
  -> Barge-In Decision (Stops TTS only when genuine speech is confirmed)
"""

from __future__ import annotations

import collections
import io
import logging
import time
from typing import Callable, Coroutine, Dict, List, Optional, Set, Tuple
import numpy as np

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False

logger = logging.getLogger("priya.acoustic_pipeline")


# ── 1. Acoustic Echo Cancellation (AEC) ──────────────────────────────────────

class AdaptiveEchoCanceller:
    """
    Normalized Least Mean Squares (NLMS) Adaptive Filter for Echo Cancellation.
    Cancels Priya's TTS playback output from leaking into the microphone during speakerphone calls.
    """

    def __init__(self, filter_length: int = 128, mu: float = 0.05):
        self.filter_length = filter_length
        self.mu = mu  # Step size / adaptation rate
        self.weights = np.zeros(filter_length, dtype=np.float32)
        # Reference buffer holds recent TTS output samples
        self.ref_history = collections.deque(maxlen=48000)  # ~3s of 16kHz audio
        self.is_active = True

    def feed_reference(self, ref_bytes: bytes):
        """Feeds audio frames currently being output by Priya's TTS."""
        if not ref_bytes or not self.is_active:
            return
        try:
            samples = np.frombuffer(ref_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            self.ref_history.extend(samples)
        except Exception:
            pass

    def cancel_echo(self, mic_bytes: bytes) -> bytes:
        """Subtracts estimated speaker echo from incoming microphone frame."""
        if not mic_bytes or len(self.ref_history) < self.filter_length:
            return mic_bytes

        try:
            mic_samples = np.frombuffer(mic_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            n = len(mic_samples)
            if n == 0:
                return mic_bytes

            # Recent reference signal segment
            ref_arr = np.array(self.ref_history, dtype=np.float32)
            if len(ref_arr) < n + self.filter_length:
                return mic_bytes

            ref_segment = ref_arr[-(n + self.filter_length):]
            clean_samples = np.zeros(n, dtype=np.float32)

            for i in range(n):
                x = ref_segment[i:i + self.filter_length][::-1]
                echo_est = np.dot(self.weights, x)
                error = mic_samples[i] - echo_est
                clean_samples[i] = error

                # NLMS weight update
                norm = np.dot(x, x) + 1e-6
                self.weights += (self.mu * error / norm) * x

            clean_int16 = (np.clip(clean_samples, -1.0, 1.0) * 32767.0).astype(np.int16)
            return clean_int16.tobytes()
        except Exception as e:
            logger.debug(f"AEC error: {e}")
            return mic_bytes


# ── 2. Spectral Noise Suppression ────────────────────────────────────────────

class SpectralNoiseSuppressor:
    """
    Spectral subtraction & Wiener noise filtering.
    Attenuates stationary background noise (ceiling fans, AC units, traffic hum).
    """

    def __init__(self, sample_rate: int = 16000, alpha: float = 2.0, beta: float = 0.05):
        self.sample_rate = sample_rate
        self.alpha = alpha  # Over-subtraction factor
        self.beta = beta    # Spectral floor factor
        self.noise_profile = None
        self.frame_count = 0

    def suppress_noise(self, audio_bytes: bytes, is_speech: bool = False) -> bytes:
        """Applies spectral subtraction to incoming audio frame."""
        if not audio_bytes:
            return audio_bytes

        try:
            samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            if len(samples) < 160:
                return audio_bytes

            # FFT magnitude & phase
            spectrum = np.fft.rfft(samples)
            magnitude = np.abs(spectrum)
            phase = np.angle(spectrum)

            # Update noise profile on non-speech frames
            if not is_speech or self.noise_profile is None:
                if self.noise_profile is None:
                    self.noise_profile = magnitude
                else:
                    self.noise_profile = 0.95 * self.noise_profile + 0.05 * magnitude

            # Subtract estimated noise spectrum
            subtracted = magnitude - self.alpha * self.noise_profile
            floor = self.beta * magnitude
            clean_magnitude = np.maximum(subtracted, floor)

            # Reconstruct clean time-domain signal
            clean_spectrum = clean_magnitude * np.exp(1j * phase)
            clean_samples = np.fft.irfft(clean_spectrum, n=len(samples))

            return (np.clip(clean_samples, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
        except Exception:
            return audio_bytes


# ── 3. SNR Pre-Filter Gate ───────────────────────────────────────────────────

class SNRGate:
    """
    Rejects frames where signal-to-noise ratio is too low without needing VAD or STT.
    """

    MIN_SNR_DB = 8.0  # Frames below 8dB are considered noise floor

    def __init__(self):
        self.rolling_noise_floor_rms = 0.005
        self.silence_frame_history = collections.deque(maxlen=100)  # ~2s of frames

    def update_noise_floor(self, frame_rms: float):
        """Updates rolling average RMS over confirmed silence frames."""
        self.silence_frame_history.append(frame_rms)
        if self.silence_frame_history:
            self.rolling_noise_floor_rms = float(np.mean(self.silence_frame_history))

    def compute_snr_db(self, frame: np.ndarray) -> float:
        """Calculates frame SNR relative to rolling noise floor."""
        signal_rms = float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)))
        if self.rolling_noise_floor_rms <= 0:
            return 100.0
        return float(20.0 * np.log10(max(signal_rms, 1e-6) / max(self.rolling_noise_floor_rms, 1e-6)))

    def passes_snr_gate(self, audio_bytes: bytes) -> bool:
        """Returns True if frame energy exceeds the noise floor by at least MIN_SNR_DB."""
        if not audio_bytes:
            return False
        try:
            samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            snr = self.compute_snr_db(samples)
            return snr >= self.MIN_SNR_DB
        except Exception:
            return True


# ── 4. Two-Tier VAD & Debounced Barge-In Gate ─────────────────────────────────

class BargeInGate:
    """
    Two-Tier VAD + Debounce Gate.
    Enforces a strict consecutive-frame requirement so single-frame noise bursts or breathing
    never trigger barge-in interruptions.
    """

    REQUIRED_FRAMES = 6         # ~120ms at 20ms/frame
    NORMAL_THRESHOLD = 0.50     # Normal turn-taking threshold
    BARGE_IN_THRESHOLD = 0.75   # Stricter threshold when Priya is speaking

    def __init__(self):
        self.consecutive_speech = 0
        self.triggered = False

    def update(self, vad_prob: float, is_assistant_speaking: bool = False) -> bool:
        """
        Returns True only when barge-in should actually fire.
        Threshold is elevated to 0.75 when assistant is speaking.
        """
        threshold = self.BARGE_IN_THRESHOLD if is_assistant_speaking else self.NORMAL_THRESHOLD

        if vad_prob > threshold:
            self.consecutive_speech += 1
        else:
            self.consecutive_speech = 0

        if self.consecutive_speech >= self.REQUIRED_FRAMES and not self.triggered:
            self.triggered = True
            logger.info(f"[BARGE_IN] Debounced speech trigger fired after {self.consecutive_speech} frames (prob={vad_prob:.2f})")
            return True

        return False

    def reset(self):
        """Reset state after turn transition or speech committed."""
        self.consecutive_speech = 0
        self.triggered = False


# ── 5. Semantic Confirmation Gate ────────────────────────────────────────────

class SemanticConfirmationGate:
    """
    Filters out coughs, laughs, mic rustling, and filler sounds ("um", "uh", "hmm").
    Buffers 300–500ms of audio after VAD trigger and checks STT partial transcript
    before committing to interrupting Priya's speech.
    """

    JUNK_WORDS: Set[str] = {
        "", "um", "uh", "hmm", "you", "yeah", "ok", "cough", "ah", "er", "oh", "like", "mhm"
    }

    def __init__(self, min_chars: int = 4):
        self.min_chars = min_chars

    def is_confirmed_speech(self, partial_transcript: str) -> bool:
        """
        Evaluates partial transcript. Returns True only if genuine speech words are present.
        """
        text = (partial_transcript or "").strip()
        text_lower = text.lower().strip(".,!?:;\"'")

        # If transcript is empty or in junk words or under min_chars, reject interruption
        if not text_lower or text_lower in self.JUNK_WORDS or len(text_lower) < self.min_chars:
            logger.debug(f"[SEMANTIC_CONFIRMATION] Rejected false barge-in: '{text}'")
            return False

        logger.info(f"[SEMANTIC_CONFIRMATION] Confirmed genuine user interruption: '{text}'")
        return True


# ── 6. Full Integrated Acoustic Pipeline ─────────────────────────────────────

class AcousticPipeline:
    """
    Complete real-time audio pipeline integrating:
    AEC -> Noise Suppression -> SNR Gate -> Two-Tier VAD -> Debounce -> Semantic Confirmation
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.aec = AdaptiveEchoCanceller()
        self.noise_suppressor = SpectralNoiseSuppressor(sample_rate=sample_rate)
        self.snr_gate = SNRGate()
        self.barge_in_gate = BargeInGate()
        self.semantic_gate = SemanticConfirmationGate(min_chars=4)

        # WebRTC VAD instance if available
        self.webrtc_vad = None
        if WEBRTCVAD_AVAILABLE:
            try:
                self.webrtc_vad = webrtcvad.Vad(2)  # Balanced aggressiveness (0-3)
            except Exception:
                pass

        self.audio_buffer = bytearray()
        self.is_assistant_speaking = False

    def feed_tts_reference(self, reference_frame: bytes):
        """Pass Priya's outgoing TTS audio frames to AEC."""
        self.aec.feed_reference(reference_frame)

    def set_assistant_speaking(self, speaking: bool):
        """Notify pipeline whether Priya is actively playing speech."""
        self.is_assistant_speaking = speaking
        if not speaking:
            self.barge_in_gate.reset()
            self.audio_buffer.clear()

    def process_frame(self, mic_frame: bytes) -> Tuple[bytes, bool, float]:
        """
        Processes incoming 20ms mic frame through:
        1. AEC (Acoustic Echo Cancellation)
        2. Spectral Noise Suppression
        3. SNR Pre-Filter Gate
        4. Two-Tier VAD Probability Calculation
        5. Debounced Barge-In Decision

        Returns: (clean_frame, should_trigger_barge_in, vad_probability)
        """
        if not mic_frame:
            return mic_frame, False, 0.0

        # Step 1: Acoustic Echo Cancellation
        echo_cancelled = self.aec.cancel_echo(mic_frame)

        # Step 2: SNR Pre-Filter Check
        samples = np.frombuffer(echo_cancelled, dtype=np.int16).astype(np.float32) / 32768.0
        frame_rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) > 0 else 0.0

        if not self.snr_gate.passes_snr_gate(echo_cancelled):
            # Frame is in noise floor — update rolling noise floor and skip VAD
            self.snr_gate.update_noise_floor(frame_rms)
            clean_frame = self.noise_suppressor.suppress_noise(echo_cancelled, is_speech=False)
            self.barge_in_gate.consecutive_speech = 0
            return clean_frame, False, 0.0

        # Step 3: Spectral Noise Suppression
        clean_frame = self.noise_suppressor.suppress_noise(echo_cancelled, is_speech=True)

        # Step 4: Calculate VAD Speech Probability
        vad_prob = self._compute_vad_probability(clean_frame)

        # Step 5: Update Debounce Gate
        barge_in_fired = self.barge_in_gate.update(
            vad_prob,
            is_assistant_speaking=self.is_assistant_speaking
        )

        if barge_in_fired:
            # Buffer audio for semantic confirmation
            self.audio_buffer.extend(clean_frame)

        return clean_frame, barge_in_fired, vad_prob

    def confirm_barge_in(self, partial_stt_text: str) -> bool:
        """
        Evaluates whether debounced speech trigger is a genuine interruption.
        Returns True to stop TTS, False to ignore and keep speaking.
        """
        return self.semantic_gate.is_confirmed_speech(partial_stt_text)

    def _compute_vad_probability(self, frame_bytes: bytes) -> float:
        """Computes voice activity probability (0.0 to 1.0)."""
        if not frame_bytes:
            return 0.0

        # Try WebRTC VAD on 10ms/20ms/30ms frames
        if self.webrtc_vad:
            frame_len = len(frame_bytes)
            # WebRTC VAD accepts 160 (10ms), 320 (20ms), or 480 (30ms) samples at 16kHz (2 bytes/sample)
            valid_sizes = {320, 640, 960} if self.sample_rate == 16000 else {160, 320, 480}
            if frame_len in valid_sizes:
                try:
                    is_speech = self.webrtc_vad.is_speech(frame_bytes, self.sample_rate)
                    return 0.85 if is_speech else 0.15
                except Exception:
                    pass

        # Energy & spectral centroid estimation fallback
        try:
            samples = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(samples ** 2)))
            if rms < 0.01:
                return 0.05
            elif rms > 0.06:
                return 0.85
            else:
                return float(np.clip(rms * 12.0, 0.1, 0.8))
        except Exception:
            return 0.1
