# crm/priya-livekit/priya/audio/interruption_controller.py
"""
Centralized Multi-Signal Interruption & Speaker Verification Controller.
Prevents false barge-in from:
  1. Nearby persons / other voices (via acoustic Speaker Verification)
  2. Instagram/YouTube reels, TV, background music (via MediaDetector)
  3. Non-speech noise artifacts (via STT quality validation)
  4. Passive caller backchannels like "hmm", "uh-huh", "ok" (via SemanticTurnValidator)

Architecture:
  Incoming Audio
        ↓
  Preprocessing & Silero VAD (Speech Candidate)
        ↓
  Speech Duration Gate (>= 350-400ms)
        ↓
  Speaker Verification (Caller Voice Embedding & Cosine Similarity)
        ↓
  Media / Music / Reel Detection (Spectral Flatness & Harmonicity)
        ↓
  Transcript Quality Validation (Drop [noise], coughs, breathing)
        ↓
  Semantic Turn Check (Distinguish Backchannels vs Real Barge-in)
        ↓
  CENTRALIZED INTERRUPTION DECISION (Stop TTS only if caller speech confirmed)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Set
import numpy as np

logger = logging.getLogger("priya.interruption_controller")


@dataclass
class InterruptionDecision:
    should_interrupt: bool
    candidate_type: str  # "CALLER", "NON_CALLER_SPEAKER", "MEDIA", "BACKCHANNEL", "NOISE", "UNKNOWN"
    reason: str
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        payload = {
            "decision": "INTERRUPT" if self.should_interrupt else "IGNORE",
            "candidate_type": self.candidate_type,
            "reason": self.reason,
            "metrics": self.metrics,
        }
        return json.dumps(payload)


# ── 1. Acoustic Speaker Verifier ─────────────────────────────────────────────

class SpeakerVerifier:
    """
    Caller Voice Profiler & Speaker Verification Gate.
    Extracts a 32-dimensional normalized acoustic embedding:
      - 12 MFCC coefficients (Mel-frequency cepstral coefficients via DCT-II)
      - F0 fundamental frequency & pitch clarity via autocorrelation
      - Spectral Centroid, Rolloff, and Flux
      - Formant energy ratios (Low, Mid, High telephone bands)
    Enrolls caller during clean turns and compares barge-in candidate audio
    using cosine similarity to reject nearby speakers.
    """

    def __init__(self, sample_rate: int = 16000, similarity_threshold: float = 0.65):
        self.sample_rate = sample_rate
        self.similarity_threshold = float(os.getenv("SPEAKER_SIMILARITY_THRESHOLD", str(similarity_threshold)))
        self.caller_embedding: Optional[np.ndarray] = None
        self.enrollment_frames_count: int = 0
        self.alpha: float = 0.80  # Exponential moving average for profile adaptation

    def extract_embedding(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """Extract a 32-dimensional normalized acoustic embedding from raw PCM audio."""
        if not audio_bytes or len(audio_bytes) < 640:  # Need at least ~20-40ms
            return None

        try:
            samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            n = len(samples)
            if n < 320:
                return None

            # Apply Hann window to reduce spectral leakage
            windowed = samples * np.hanning(n)

            # FFT magnitude spectrum
            fft_mag = np.abs(np.fft.rfft(windowed))
            freqs = np.fft.rfftfreq(n, d=1.0 / self.sample_rate)
            total_energy = float(np.sum(fft_mag ** 2)) + 1e-12

            # 1. 16 Mel Filterbank Energies (Telephone band: 300Hz to min(sample_rate/2, 3800Hz))
            f_min, f_max = 300.0, min(self.sample_rate / 2.0 - 100.0, 3800.0)
            mel_min = 2595.0 * np.log10(1.0 + f_min / 700.0)
            mel_max = 2595.0 * np.log10(1.0 + f_max / 700.0)
            mel_points = np.linspace(mel_min, mel_max, 18)
            hz_points = 700.0 * (10.0 ** (mel_points / 2595.0) - 1.0)

            filterbank_energies = []
            for m in range(1, 17):
                f_left, f_center, f_right = hz_points[m - 1], hz_points[m], hz_points[m + 1]
                # Triangular filter
                weights = np.maximum(0.0, np.minimum(
                    (freqs - f_left) / max(1e-6, f_center - f_left),
                    (f_right - freqs) / max(1e-6, f_right - f_center)
                ))
                energy = float(np.sum(fft_mag * weights))
                filterbank_energies.append(np.log(max(energy, 1e-5)))

            fb = np.array(filterbank_energies, dtype=np.float32)

            # 2. 12 MFCCs via DCT-II (matrix DCT in pure numpy)
            N = len(fb)
            M = np.cos(np.pi / N * (np.arange(N) + 0.5) * np.arange(N)[:, None])
            M[0, :] *= 1.0 / np.sqrt(N)
            M[1:, :] *= np.sqrt(2.0 / N)
            mfcc = (M @ fb)[1:13]  # Discard DC component index 0, take 12 cepstral coefficients

            # 3. Pitch / Fundamental Frequency F0 estimation via autocorrelation
            corr = np.correlate(samples, samples, mode='full')
            corr = corr[len(corr) // 2:]
            # Search pitch lags corresponding to 70 Hz - 350 Hz (human vocal range)
            lag_min = int(self.sample_rate / 350.0)
            lag_max = int(self.sample_rate / 70.0)
            if lag_max < len(corr) and lag_min < lag_max:
                pitch_slice = corr[lag_min:lag_max]
                best_lag = lag_min + int(np.argmax(pitch_slice))
                norm_corr = float(pitch_slice[best_lag - lag_min]) / max(1e-6, float(corr[0]))
                estimated_f0 = float(self.sample_rate / best_lag)
            else:
                estimated_f0 = 150.0
                norm_corr = 0.5

            f0_feat = (estimated_f0 - 150.0) / 100.0
            pitch_strength = np.clip(norm_corr, 0.0, 1.0)

            # 4. Formant Energy Ratios:
            # Low: 300 - 800 Hz (F1 vowel openness)
            # Mid: 800 - 2500 Hz (F2 vowel placement)
            # High: 2500 - 4000 Hz (F3 speaker identity)
            low_e = float(np.sum(fft_mag[(freqs >= 300) & (freqs < 800)] ** 2)) / total_energy
            mid_e = float(np.sum(fft_mag[(freqs >= 800) & (freqs < 2500)] ** 2)) / total_energy
            high_e = float(np.sum(fft_mag[(freqs >= 2500) & (freqs < 4000)] ** 2)) / total_energy

            # 5. Spectral Centroid and Rolloff
            spectral_centroid = float(np.sum(freqs * fft_mag) / (np.sum(fft_mag) + 1e-12))
            centroid_norm = np.clip(spectral_centroid / (self.sample_rate / 2.0), 0.0, 1.0)

            cum_energy = np.cumsum(fft_mag ** 2)
            rolloff_idx = np.searchsorted(cum_energy, 0.85 * total_energy)
            rolloff_freq = float(freqs[min(rolloff_idx, len(freqs) - 1)])
            rolloff_norm = np.clip(rolloff_freq / (self.sample_rate / 2.0), 0.0, 1.0)

            # Assemble 32-dimensional feature vector
            features = list(mfcc)  # 12 features
            features.extend([
                f0_feat * 2.0,        # 13: F0 pitch shift
                pitch_strength,       # 14: pitch clarity
                centroid_norm,        # 15: spectral centroid
                rolloff_norm,         # 16: spectral rolloff
                low_e * 2.0,          # 17: F1 energy ratio
                mid_e * 2.0,          # 18: F2 energy ratio
                high_e * 2.0,         # 19: F3 energy ratio
            ])
            # Delta MFCC features
            delta_mfcc = np.diff(mfcc[:10])  # 9 features -> total 28
            features.extend(list(delta_mfcc))
            # Additional spectral features
            spread = float(np.sqrt(np.sum(((freqs - spectral_centroid) ** 2) * fft_mag) / (np.sum(fft_mag) + 1e-12)))
            features.extend([spread / 2000.0, low_e - mid_e, mid_e - high_e, float(np.std(mfcc))])  # 28 + 4 = 32

            vec = np.array(features[:32], dtype=np.float32)
            # L2 normalize to unit vector for fast cosine similarity
            norm = np.linalg.norm(vec)
            if norm > 1e-6:
                vec = vec / norm
            return vec
        except Exception as e:
            logger.debug(f"[SPEAKER_VERIFIER] Embedding extraction failed: {e}")
            return None

    def enroll_caller(self, audio_bytes: bytes):
        """Enroll or update the caller's voice profile using clean caller speech."""
        vec = self.extract_embedding(audio_bytes)
        if vec is None:
            return

        if self.caller_embedding is None:
            self.caller_embedding = vec
            self.enrollment_frames_count = 1
            logger.info(f"[SPEAKER_VERIFIER] Initialized caller voice profile (frame count=1)")
        else:
            # Exponential moving average adaptation
            self.caller_embedding = self.alpha * self.caller_embedding + (1.0 - self.alpha) * vec
            norm = np.linalg.norm(self.caller_embedding)
            if norm > 1e-6:
                self.caller_embedding = self.caller_embedding / norm
            self.enrollment_frames_count += 1
            if self.enrollment_frames_count % 10 == 0:
                logger.debug(f"[SPEAKER_VERIFIER] Updated caller profile (frames={self.enrollment_frames_count})")

    def verify_speaker(self, candidate_audio: bytes) -> float:
        """
        Calculates cosine similarity between candidate audio and the enrolled caller profile.
        Returns similarity score (0.0 to 1.0).
        If caller is not yet enrolled, returns 1.0 so early turns are never blocked.
        """
        if self.caller_embedding is None:
            return 1.0  # Trust caller before enrollment

        cand_vec = self.extract_embedding(candidate_audio)
        if cand_vec is None:
            return 0.5  # Neutral fallback

        raw_dot = float(np.dot(self.caller_embedding, cand_vec))
        # Map cosine range [-1.0, 1.0] to [0.0, 1.0]
        similarity = float(np.clip(0.5 * (raw_dot + 1.0), 0.0, 1.0))
        return similarity

    @property
    def is_enrolled(self) -> bool:
        return self.caller_embedding is not None


# ── 2. Media / Music / Reel Detector ──────────────────────────────────────────

class MediaDetector:
    """
    Detects audio coming from TV, background music, or Instagram/YouTube reels.
    Acoustic signatures of media vs telephone voice:
      - Media / Music: Wideband high-frequency dispersion (> 3400 Hz), dense polyphonic
        inharmonicity across musical chords, sustained backing track sound.
      - Telephone Voice: Bounded telephone bandwidth (< 3400 Hz), monophonic integer
        harmonics from a single vocal tract, dynamic syllabic pauses.
    """

    def __init__(self, sample_rate: int = 16000, media_threshold: float = 0.55):
        self.sample_rate = sample_rate
        self.media_threshold = float(os.getenv("MEDIA_DETECTION_THRESHOLD", str(media_threshold)))

    def detect_media_probability(self, audio_bytes: bytes) -> float:
        """Calculates probability (0.0 to 1.0) that audio is media, video, or background music."""
        if not audio_bytes or len(audio_bytes) < 640:
            return 0.0

        try:
            samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            n = len(samples)
            if n < 320:
                return 0.0

            # FFT magnitude
            fft_mag = np.abs(np.fft.rfft(samples * np.hanning(n)))
            power = fft_mag ** 2 + 1e-12
            freqs = np.fft.rfftfreq(n, d=1.0 / self.sample_rate)

            # 1. High-Frequency Dispersion (> 3400 Hz telephony cutoff)
            hf_energy = float(np.sum(power[freqs > 3400.0]) / np.sum(power))

            # 2. Inharmonicity / Polyphonic Chord Structure
            corr = np.correlate(samples, samples, mode='full')
            corr = corr[len(corr) // 2:]
            lag_min = int(self.sample_rate / 350.0)
            lag_max = int(self.sample_rate / 70.0)
            best_lag = lag_min + int(np.argmax(corr[lag_min:lag_max])) if len(corr) > lag_max else lag_min
            f0 = float(self.sample_rate / max(1, best_lag))

            harmonic_mask = np.zeros_like(freqs, dtype=bool)
            for h in range(1, 15):
                harmonic_mask |= (np.abs(freqs - h * f0) < 30.0)
            inharmonic_ratio = float(np.sum(power[~harmonic_mask]) / np.sum(power))

            # Compute composite media score
            media_score = 0.0
            if hf_energy > 0.15:
                media_score += 0.50
            if inharmonic_ratio > 0.35:
                media_score += 0.35
            if hf_energy > 0.25:
                media_score += 0.25

            return float(np.clip(media_score, 0.0, 1.0))
        except Exception as e:
            logger.debug(f"[MEDIA_DETECTOR] Computation error: {e}")
            return 0.0


# ── 3. Semantic Turn & Backchannel Validator ──────────────────────────────────

class SemanticTurnValidator:
    """
    Distinguishes passive backchannels from intentional conversational barge-ins.
    Backchannels ('hmm', 'uh-huh', 'yeah', 'ok', 'right') should NOT interrupt Priya
    when she is explaining course details or answering questions.
    """

    BACKCHANNEL_WORDS: Set[str] = {
        "hmm", "hm", "mhm", "uh-huh", "uhuh", "yeah", "ok", "okay", "right",
        "sure", "haan", "ha", "achha", "accha", "theek", "theek hai",
        "sare", "avunu", "aa", "oh", "got it", "i see", "understood"
    }

    NOISE_PATTERNS: Set[str] = {
        "[noise]", "[music]", "[silence]", "[cough]", "[laughter]",
        "[applause]", "[sigh]", "[snort]", "[pant]", "[throat-clearing]",
        "...", ".", "..", "?", "!", "-", "--", "---", "*", "_"
    }

    BARGE_IN_TRIGGER_KEYWORDS: Set[str] = {
        "wait", "stop", "hold on", "listen", "no", "actually", "excuse me",
        "sorry", "not", "ruko", "aagandi", "suno", "aaga", "wait a minute",
        "wait please", "just wait", "cancel", "wrong", "change", "lekapothe"
    }

    def is_meaningful_turn(self, transcript: str, is_assistant_speaking: bool) -> Tuple[bool, str]:
        """
        Determines whether the transcribed utterance represents a legitimate interruption.
        Returns: (should_interrupt, reason)
        """
        if not transcript or not transcript.strip():
            return False, "EMPTY_TRANSCRIPT"

        clean = transcript.strip().lower()

        # Reject non-speech noise patterns and bracketed STT artifacts
        if clean in self.NOISE_PATTERNS:
            return False, "NOISE_ARTIFACT"
        if not re.search(r'[a-zA-Z0-9\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF]', clean):
            return False, "NON_SPEECH_NOISE"

        clean_words = [w.strip(".,!?:;\"'") for w in clean.split()]
        clean_words = [w for w in clean_words if w and w not in self.NOISE_PATTERNS]

        if not clean_words:
            return False, "EMPTY_TRANSCRIPT"

        # If assistant is NOT speaking, any valid speech is naturally accepted
        if not is_assistant_speaking:
            return True, "NORMAL_USER_TURN"

        # If assistant IS speaking (barge-in scenario):
        # 1. Explicit barge-in trigger word present -> ALWAYS interrupt
        if any(w in self.BARGE_IN_TRIGGER_KEYWORDS for w in clean_words) or any(phrase in clean for phrase in self.BARGE_IN_TRIGGER_KEYWORDS):
            return True, "EXPLICIT_BARGE_IN_KEYWORD"

        # 2. Questions with interrogation mark or question words -> intentional interruption
        if "?" in transcript or any(w in clean_words for w in ["what", "which", "how", "why", "where", "enti", "kya"]):
            return True, "MEANINGFUL_INTERRUPTION"

        # 3. Pure backchannel -> DO NOT interrupt! Assistant continues speaking
        if len(clean_words) <= 2 and all(w in self.BACKCHANNEL_WORDS for w in clean_words):
            return False, "BACKCHANNEL_REJECTED"

        # 4. Multi-word complete statement (>= 3 words) not composed of pure backchannels -> legitimate interruption
        if len(clean_words) >= 3 and not all(w in self.BACKCHANNEL_WORDS for w in clean_words):
            return True, "MEANINGFUL_INTERRUPTION"

        # Short single word not in backchannels or barge-ins -> cautious accept
        if len(clean_words) == 1 and clean_words[0] not in self.BACKCHANNEL_WORDS:
            return True, "CONFIRMED_SHORT_WORD"

        return False, "BACKCHANNEL_REJECTED"


# ── 4. Centralized Interruption Controller ────────────────────────────────────

class InterruptionController:
    """
    Centralized Authority for All Interruption & Barge-in Decisions.
    Enforces the core rule: VAD MUST NEVER DIRECTLY STOP TTS.
    Only the final evaluated decision from this controller is permitted to cancel TTS.
    """

    def __init__(self, sample_rate: int = 16000, call_id: str = "default_call"):
        self.call_id = call_id
        self.sample_rate = sample_rate
        self.speaker_verifier = SpeakerVerifier(sample_rate=sample_rate)
        self.media_detector = MediaDetector(sample_rate=sample_rate)
        self.turn_validator = SemanticTurnValidator()

        # State tracking
        self.state: str = "IDLE"  # "IDLE", "USER_SPEAKING", "AI_SPEAKING", "POSSIBLE_INTERRUPTION", "INTERRUPTED"
        self.interruption_in_progress: bool = False
        self.is_assistant_speaking: bool = False

    def set_assistant_speaking(self, speaking: bool):
        """Notifies the controller whether Priya is currently outputting speech."""
        self.is_assistant_speaking = speaking
        self.interruption_in_progress = False
        self.state = "AI_SPEAKING" if speaking else "IDLE"

    def enroll_caller_turn(self, clean_audio_bytes: bytes):
        """Enrolls verified caller audio to strengthen caller voice profile."""
        self.speaker_verifier.enroll_caller(clean_audio_bytes)

    def evaluate(
        self,
        audio_bytes: bytes,
        transcript: str,
        speech_duration_ms: float = 400.0,
        vad_probability: float = 0.90
    ) -> InterruptionDecision:
        """
        Executes multi-signal evaluation to make the final interruption decision.
        """
        # If assistant is not speaking, this is just normal turn-taking, not an interruption
        if not self.is_assistant_speaking:
            return InterruptionDecision(
                should_interrupt=False,
                candidate_type="NORMAL_TURN",
                reason="ASSISTANT_NOT_SPEAKING",
                metrics={"vad_probability": vad_probability}
            )

        # Guard against double-interruption triggers
        if self.interruption_in_progress:
            return InterruptionDecision(
                should_interrupt=False,
                candidate_type="IN_PROGRESS",
                reason="INTERRUPTION_ALREADY_IN_PROGRESS"
            )

        # 1. Minimum Speech Duration Gate (>= 350ms)
        min_speech_ms = float(os.getenv("MIN_INTERRUPTION_DURATION_MS", "350"))
        if speech_duration_ms < min_speech_ms:
            decision = InterruptionDecision(
                should_interrupt=False,
                candidate_type="NOISE",
                reason="SPEECH_DURATION_TOO_SHORT",
                metrics={"speech_duration_ms": speech_duration_ms, "min_required": min_speech_ms}
            )
            self._log_decision(decision)
            return decision

        # 2. Media / Reel / Music Check
        media_prob = self.media_detector.detect_media_probability(audio_bytes)
        if media_prob >= self.media_detector.media_threshold:
            decision = InterruptionDecision(
                should_interrupt=False,
                candidate_type="MEDIA",
                reason="MEDIA_OR_MUSIC_DETECTED",
                metrics={"media_probability": round(media_prob, 2), "threshold": self.media_detector.media_threshold}
            )
            self._log_decision(decision)
            return decision

        # 3. Speaker Verification Check
        speaker_sim = self.speaker_verifier.verify_speaker(audio_bytes)
        if self.speaker_verifier.is_enrolled and speaker_sim < self.speaker_verifier.similarity_threshold:
            decision = InterruptionDecision(
                should_interrupt=False,
                candidate_type="NON_CALLER_SPEAKER",
                reason="SPEAKER_MISMATCH_NEARBY_PERSON",
                metrics={"speaker_similarity": round(speaker_sim, 2), "threshold": self.speaker_verifier.similarity_threshold}
            )
            self._log_decision(decision)
            return decision

        # 4. Semantic Turn & Backchannel Check
        is_meaningful, turn_reason = self.turn_validator.is_meaningful_turn(
            transcript, is_assistant_speaking=self.is_assistant_speaking
        )
        if not is_meaningful:
            decision = InterruptionDecision(
                should_interrupt=False,
                candidate_type="BACKCHANNEL",
                reason=turn_reason,
                metrics={
                    "transcript": transcript,
                    "speaker_similarity": round(speaker_sim, 2),
                    "media_probability": round(media_prob, 2),
                }
            )
            self._log_decision(decision)
            return decision

        # All Gates Passed: Genuine Caller Interruption Confirmed!
        self.interruption_in_progress = True
        self.state = "INTERRUPTED"
        decision = InterruptionDecision(
            should_interrupt=True,
            candidate_type="CALLER",
            reason=turn_reason,
            metrics={
                "call_id": self.call_id,
                "vad_detected": True,
                "speech_duration_ms": speech_duration_ms,
                "speaker_similarity": round(speaker_sim, 2),
                "media_probability": round(media_prob, 2),
                "transcript": transcript,
            }
        )
        self._log_decision(decision)
        return decision

    def _log_decision(self, decision: InterruptionDecision):
        """Emits structured JSON audit log for every barge-in decision."""
        log_payload = {
            "call_id": self.call_id,
            "decision": "INTERRUPT" if decision.should_interrupt else "IGNORE",
            "candidate_type": decision.candidate_type,
            "reason": decision.reason,
            "metrics": decision.metrics,
        }
        if decision.should_interrupt:
            logger.info(f"[INTERRUPTION_DECISION] {json.dumps(log_payload)}")
        else:
            logger.info(f"[INTERRUPTION_REJECTED] {json.dumps(log_payload)}")
