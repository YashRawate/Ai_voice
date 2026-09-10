# crm/priya-livekit/priya/audio/delay_calibration.py
"""
Delay Calibration Module for Acoustic Echo Cancellation (AEC).

Computes the physical / buffer latency between Priya's TTS output stream and
the microphone capture using cross-correlation. This alignment ensures the
adaptive echo filter (NLMS) subtracts the echo at the exact sample offset.
"""

from __future__ import annotations

import logging
import numpy as np

logger = logging.getLogger("priya.delay_calibration")


def estimate_delay_samples(reference: np.ndarray, mic: np.ndarray) -> int:
    """
    Cross-correlate reference (TTS output) against mic input to find echo delay in samples.

    Args:
        reference: 1D float array of reference TTS samples.
        mic: 1D float array of microphone input samples.

    Returns:
        Lag in samples (>= 0). If correlation is degenerate or zero-energy, returns 0.
    """
    if len(reference) == 0 or len(mic) == 0:
        return 0

    ref_norm = np.linalg.norm(reference)
    mic_norm = np.linalg.norm(mic)

    if ref_norm < 1e-6 or mic_norm < 1e-6:
        # One or both signals are silent
        return 0

    try:
        # Cross-correlation via FFT for speed on larger buffers
        correlation = np.correlate(mic, reference, mode="full")
        # Optimal peak is at lag_samples
        lag_samples = int(np.argmax(correlation) - (len(reference) - 1))
        return max(lag_samples, 0)
    except Exception as e:
        logger.warning(f"Error computing cross-correlation delay: {e}")
        return 0


def estimate_delay_ms(reference: np.ndarray, mic: np.ndarray, sample_rate: int = 16000) -> float:
    """
    Cross-correlate reference against mic input to find echo delay in milliseconds.

    Args:
        reference: 1D float array of reference TTS samples.
        mic: 1D float array of microphone input samples.
        sample_rate: Sample rate in Hz (default 16000, or 8000 for telephony).

    Returns:
        Estimated delay in milliseconds.
    """
    lag_samples = estimate_delay_samples(reference, mic)
    return (lag_samples / sample_rate) * 1000.0
