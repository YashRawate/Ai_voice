# audio_quality_gate.py

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("priya.audio_quality")

# Optional imports with robust fallbacks
try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


@dataclass
class AudioQualityResult:
    is_valid: bool
    confidence: float
    noise_level: str  # "clean", "moderate", "noisy", "silent", "clipped", "invalid"
    snr_db: float     # Signal-to-noise ratio in dB
    reason: str
    has_speech: bool


class AudioQualityGate:
    """
    Gate 1: Validates audio before language detection
    Filters out noise, background chatter, silence, and clipped signals.
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.vad = None
        if WEBRTCVAD_AVAILABLE:
            try:
                self.vad = webrtcvad.Vad(2)  # Aggressiveness 0-3 (2 is balanced)
            except Exception as e:
                logger.warning(f"Failed to initialize webrtcvad: {e}")
                self.vad = None

        # Energy & SNR thresholds
        self.ENERGY_MIN = 0.001  # Minimum RMS energy (reject silence)
        self.ENERGY_MAX = 0.85   # Maximum RMS energy (reject clipped/distorted noise)
        self.SNR_MIN = 3.0       # Minimum acceptable SNR in dB
        self.SNR_GOOD = 8.0      # SNR threshold for "clean" speech

        # Prewarm JIT compilers (Librosa/Numba) so first turn latency is < 5ms
        self.warmup()

    def warmup(self):
        """Warm up spectral JIT compilers on empty/dummy frames during startup."""
        try:
            dummy = (np.sin(np.linspace(0, 0.1, 1600)) * 1000).astype(np.int16).tobytes()
            self.estimate_snr(dummy)
            self.calculate_energy(dummy)
            self.has_voice_activity(dummy)
        except Exception:
            pass

    def calculate_energy(self, audio_bytes: bytes) -> float:
        """Calculate normalized RMS energy of audio (range 0.0 to 1.0)."""
        if not audio_bytes:
            return 0.0
        try:
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            if len(audio) == 0:
                return 0.0
            audio = audio / 32768.0
            rms = float(np.sqrt(np.mean(audio ** 2)))
            return rms
        except Exception as e:
            logger.debug(f"calculate_energy error: {e}")
            return 0.0

    def estimate_snr(self, audio_bytes: bytes) -> float:
        """
        Estimate Signal-to-Noise Ratio (SNR) in dB.
        Uses spectral centroid/energy distribution if librosa is available,
        or numpy FFT spectral power estimation fallback.
        """
        if not audio_bytes:
            return 0.0

        try:
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            if len(audio) < 160:
                return 0.0
            audio = audio / 32768.0

            if LIBROSA_AVAILABLE:
                try:
                    n_fft = min(2048, max(256, len(audio)))
                    spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate, n_fft=n_fft)
                    signal_power = float(np.mean(spectral_centroids))
                    noise_power = float(np.std(spectral_centroids))
                    if noise_power < 1e-10:
                        return 20.0  # Clean audio
                    snr_db = 10.0 * np.log10(max(1e-5, signal_power / noise_power))
                    return float(np.clip(snr_db, 0.0, 40.0))
                except Exception as e:
                    logger.debug(f"librosa spectral centroid failed, falling back to FFT: {e}")

            # Robust Pure-NumPy spectral fallback
            fft_vals = np.abs(np.fft.rfft(audio))
            freqs = np.fft.rfftfreq(len(audio), 1.0 / self.sample_rate)

            # Speech band (300 Hz - 3400 Hz) vs Out-of-band noise
            speech_mask = (freqs >= 300) & (freqs <= 3400)
            noise_mask = ~speech_mask

            speech_energy = np.mean(fft_vals[speech_mask] ** 2) if np.any(speech_mask) else 1e-5
            noise_energy = np.mean(fft_vals[noise_mask] ** 2) if np.any(noise_mask) else 1e-5

            if noise_energy < 1e-10:
                return 20.0
            snr_db = 10.0 * np.log10(max(1e-5, speech_energy / noise_energy))
            return float(np.clip(snr_db, 0.0, 40.0))
        except Exception as e:
            logger.debug(f"estimate_snr error: {e}")
            return 10.0

    def has_voice_activity(self, audio_bytes: bytes) -> bool:
        """
        Detect if audio contains speech frames.
        Uses WebRTC VAD if available, or energy + zero-crossing rate fallback.
        """
        if not audio_bytes:
            return False

        try:
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            if len(audio) == 0:
                return False

            if self.vad is not None and self.sample_rate in (8000, 16000, 32000, 48000):
                # VAD requires frames of exactly 10, 20, or 30ms (for 16kHz, 20ms = 320 samples = 640 bytes)
                frame_samples = (self.sample_rate * 20) // 1000
                frame_bytes_len = frame_samples * 2
                speech_frames = 0
                total_frames = 0

                for i in range(0, len(audio) - frame_samples + 1, frame_samples):
                    frame = audio[i:i + frame_samples]
                    total_frames += 1
                    try:
                        if self.vad.is_speech(frame.tobytes(), self.sample_rate):
                            speech_frames += 1
                    except Exception:
                        continue

                if total_frames > 0 and (speech_frames / total_frames) >= 0.15:
                    return True
                return False

            # Fallback: Energy + Zero-Crossing Rate analysis
            norm_audio = audio.astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(norm_audio ** 2))
            zcr = np.mean(np.abs(np.diff(np.signbit(norm_audio))))

            # Speech generally has moderate energy and moderate zero crossing rate
            if rms >= self.ENERGY_MIN and 0.02 <= zcr <= 0.6:
                return True
            return False
        except Exception as e:
            logger.debug(f"has_voice_activity error: {e}")
            return True

    async def is_valid_speech(self, audio_bytes: bytes) -> AudioQualityResult:
        """
        Main gate function: Evaluates audio validity across Energy, VAD, and SNR.
        """
        if not audio_bytes or len(audio_bytes) < 100:
            return AudioQualityResult(
                is_valid=False,
                confidence=0.0,
                noise_level="invalid",
                snr_db=0.0,
                reason="Audio too short or empty",
                has_speech=False
            )

        # 1. Energy checks
        energy = self.calculate_energy(audio_bytes)
        if energy < self.ENERGY_MIN:
            return AudioQualityResult(
                is_valid=False,
                confidence=0.0,
                noise_level="silent",
                snr_db=0.0,
                reason=f"Audio too quiet (RMS energy: {energy:.5f} < {self.ENERGY_MIN})",
                has_speech=False
            )

        if energy > self.ENERGY_MAX:
            return AudioQualityResult(
                is_valid=False,
                confidence=0.2,
                noise_level="clipped",
                snr_db=0.0,
                reason=f"Audio clipped or excessively loud (energy: {energy:.3f})",
                has_speech=False
            )

        # 2. Voice Activity Detection
        has_speech = self.has_voice_activity(audio_bytes)
        if not has_speech:
            return AudioQualityResult(
                is_valid=False,
                confidence=0.1,
                noise_level="noisy",
                snr_db=0.0,
                reason="No voice activity detected in audio frames",
                has_speech=False
            )

        # 3. SNR estimation
        snr_db = self.estimate_snr(audio_bytes)
        if snr_db < self.SNR_MIN:
            return AudioQualityResult(
                is_valid=False,
                confidence=0.3,
                noise_level="very_noisy",
                snr_db=snr_db,
                reason=f"SNR too low ({snr_db:.1f} dB < {self.SNR_MIN} dB)",
                has_speech=False
            )

        # Determine noise classification and confidence
        if snr_db >= self.SNR_GOOD:
            noise_level = "clean"
            confidence = min(1.0, 0.75 + (snr_db - self.SNR_GOOD) / 25.0)
        else:
            noise_level = "moderate"
            confidence = 0.50 + ((snr_db - self.SNR_MIN) / max(1.0, self.SNR_GOOD - self.SNR_MIN)) * 0.25

        return AudioQualityResult(
            is_valid=True,
            confidence=float(confidence),
            noise_level=noise_level,
            snr_db=float(snr_db),
            reason=f"Valid speech detected ({noise_level}, SNR: {snr_db:.1f} dB)",
            has_speech=True
        )
