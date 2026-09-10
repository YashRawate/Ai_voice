# scripts/calibrate_thresholds.py
"""
Threshold Calibration & Ambient Noise Logger for AdmitAI Priya Voice Agent.

Run this in your real test environment (same room, same background noise —
fan, traffic, whatever's actually present) for 30s with NO ONE TALKING.
Logs raw VAD probability and SNR per frame to calibration_log.csv so you can
pick real, data-driven thresholds (BARGE_IN_THRESHOLD and MIN_SNR_DB).
"""

from __future__ import annotations

import csv
import os
import sys
import time
from typing import Generator, List, Dict
import numpy as np

# Ensure parent directory is on sys.path so priya modules can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from priya.audio.acoustic_pipeline import AcousticPipeline, SNRGate, BargeInGate


def create_mock_ambient_stream(duration_s: float = 30.0, sample_rate: int = 16000, frame_duration_ms: int = 20) -> Generator[bytes, None, None]:
    """Generates realistic ambient background room frames (ceiling fan hum, AC rumble, thermal noise)."""
    samples_per_frame = int(sample_rate * (frame_duration_ms / 1000.0))
    total_frames = int(duration_s / (frame_duration_ms / 1000.0))
    t_frame = np.linspace(0, frame_duration_ms / 1000.0, samples_per_frame, endpoint=False)

    for frame_idx in range(total_frames):
        # Base ambient noise (thermal / room noise floor)
        noise = np.random.normal(0, 0.008, samples_per_frame)
        # Stationary 50Hz electrical hum + 120Hz fan blade harmonic
        fan_hum = 0.015 * np.sin(2 * np.pi * 50 * t_frame + frame_idx * 0.1)
        ac_rumble = 0.010 * np.sin(2 * np.pi * 120 * t_frame + frame_idx * 0.2)
        combined = noise + fan_hum + ac_rumble
        pcm16 = (np.clip(combined, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
        yield pcm16


def record_live_mic_stream(duration_s: float = 30.0, sample_rate: int = 16000, frame_duration_ms: int = 20) -> Generator[bytes, None, None]:
    """Records live microphone frames if sounddevice is installed and mic is available."""
    try:
        import sounddevice as sd  # type: ignore
        samples_per_frame = int(sample_rate * (frame_duration_ms / 1000.0))
        total_frames = int(duration_s / (frame_duration_ms / 1000.0))

        with sd.RawInputStream(samplerate=sample_rate, blocksize=samples_per_frame, channels=1, dtype='int16') as stream:
            for _ in range(total_frames):
                data, overflow = stream.read(samples_per_frame)
                yield bytes(data)
    except Exception as e:
        print(f"Live microphone capture unavailable ({e}) -> falling back to ambient room simulation stream")
        yield from create_mock_ambient_stream(duration_s=duration_s, sample_rate=sample_rate, frame_duration_ms=frame_duration_ms)


def log_calibration_session(
    pipeline: AcousticPipeline,
    mic_stream: Generator[bytes, None, None],
    duration_s: float = 30.0,
    out_path: str = "calibration_log.csv"
) -> Dict[str, float]:
    """
    Records VAD probability and SNR across frames during silence/ambient noise.
    Computes max and p95 thresholds to configure BARGE_IN_THRESHOLD and MIN_SNR_DB.
    """
    start = time.time()
    rows: List[Dict[str, float]] = []

    for frame in mic_stream:
        clean_frame, fired, vad_prob = pipeline.process_frame(frame)
        samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32768.0
        snr_db = pipeline.snr_gate.compute_snr_db(samples)

        elapsed = time.time() - start
        rows.append({"t": round(elapsed, 4), "vad_prob": round(vad_prob, 4), "snr_db": round(snr_db, 2)})

        if elapsed >= duration_s:
            break

    if not rows:
        raise RuntimeError("No frames recorded during calibration session")

    # Write calibration log
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["t", "vad_prob", "snr_db"])
        writer.writeheader()
        writer.writerows(rows)

    vad_probs = [r["vad_prob"] for r in rows]
    snr_vals = [r["snr_db"] for r in rows]

    sorted_vad = sorted(vad_probs)
    sorted_snr = sorted(snr_vals)
    n = len(rows)

    p95_idx = int(n * 0.95)
    stats = {
        "count": float(n),
        "vad_max": float(max(vad_probs)),
        "vad_p95": float(sorted_vad[p95_idx]),
        "snr_min": float(min(snr_vals)),
        "snr_p95": float(sorted_snr[p95_idx]),
    }

    print(f"\n=======================================================")
    print(f"Calibration Session Complete: {n} frames logged to {out_path}")
    print(f"VAD Prob — Max: {stats['vad_max']:.3f} | p95: {stats['vad_p95']:.3f}")
    print(f"SNR (dB) — Min: {stats['snr_min']:.1f} | p95: {stats['snr_p95']:.1f}")
    print(f"Recommended BARGE_IN_THRESHOLD: >= {max(0.75, stats['vad_p95'] + 0.1):.2f}")
    print(f"Recommended MIN_SNR_DB:         >= {max(8.0, stats['snr_p95'] + 1.0):.1f} dB")
    print(f"=======================================================\n")

    return stats


def main():
    pipeline = AcousticPipeline(sample_rate=16000)
    pipeline.set_assistant_speaking(True)
    out_file = os.path.join(parent_dir, "calibration_log.csv")

    print("Starting 30-second background noise calibration session...")
    stream = record_live_mic_stream(duration_s=30.0, sample_rate=16000)
    log_calibration_session(pipeline, stream, duration_s=30.0, out_path=out_file)


if __name__ == "__main__":
    main()
