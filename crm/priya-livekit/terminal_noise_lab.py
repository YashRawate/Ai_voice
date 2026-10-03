#!/usr/bin/env python3
"""
terminal_noise_lab.py - test Priya's crosstalk / barge-in handling from the terminal.
No phone call needed.

It reproduces the decision layer that sits in front of the agent:
  VAD  ->  caller loudness gate  ->  barge-in policy  ->  "keep or drop this turn"
and prints every ACCEPT / REJECT decision, so you can tune the numbers in a noisy room.

MODES
  --mic                         live microphone
  --wav FILE                    replay a recording (any sample rate)
  --mix CALLER.wav CROWD.wav    mix a clean caller recording with a crowd recording.
                                Ground truth is known, so it reports true/false accepts.

INSTALL (PowerShell):
  py -m pip install numpy scipy sounddevice webrtcvad-wheels

EXAMPLES
  py terminal_noise_lab.py --mic --save mic_test.wav
  py terminal_noise_lab.py --wav mic_test.wav
  py terminal_noise_lab.py --mix caller.wav crowd.wav --crowd-db -6
  py terminal_noise_lab.py --demo            # synthetic test, checks the script itself

The agent is simulated: it "speaks" for --cycle SPEAK,LISTEN seconds (default 5,5) after calibration.
During the SPEAK windows the script tells you whether a barge-in would have been ACCEPTED.
"""
import argparse
import math
import queue
import sys
import time
import wave

import numpy as np

SR = 8000                       # telephony rate
FRAME_MS = 20
FRAME = SR * FRAME_MS // 1000   # 160 samples

try:
    import webrtcvad
except ImportError:             # falls back to a simple energy VAD
    webrtcvad = None


# --------------------------------------------------------------------------- audio helpers
def rms(x):
    x = x.astype(np.float32)
    return float(np.sqrt(np.mean(x * x)) + 1e-6)


def load_wav_8k(path):
    from scipy.io import wavfile
    from scipy.signal import resample_poly
    sr, data = wavfile.read(path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if data.dtype == np.int16:
        x = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        x = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        x = (data.astype(np.float32) - 128.0) / 128.0
    else:
        x = data.astype(np.float32)
    g = math.gcd(int(sr), SR)
    if sr != SR:
        x = resample_poly(x, SR // g, int(sr) // g)
    return (np.clip(x, -1, 1) * 32767).astype(np.int16)


def save_wav_8k(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(samples.astype(np.int16).tobytes())


def mix_tracks(caller, crowd, crowd_db):
    """Scale the crowd to `crowd_db` dB relative to the caller's RMS and add it (loops the crowd)."""
    if len(crowd) < len(caller):
        crowd = np.tile(crowd, int(math.ceil(len(caller) / max(len(crowd), 1))))
    crowd = crowd[: len(caller)].astype(np.float32)
    target = rms(caller) * (10 ** (crowd_db / 20.0))
    crowd *= target / rms(crowd)
    return np.clip(caller.astype(np.float32) + crowd, -32768, 32767).astype(np.int16)


def truth_mask(caller):
    """Per-frame ground truth: is the clean caller track speaking in this frame?"""
    n = len(caller) // FRAME
    r = np.array([rms(caller[i * FRAME:(i + 1) * FRAME]) for i in range(n)])
    thr = max(150.0, 0.15 * float(np.percentile(r, 90)))
    return r > thr


def runs_of(mask, max_gap_frames=10):
    """Merge True-runs separated by short gaps -> list of (start_idx, end_idx)."""
    out, start, gap = [], None, 0
    for i, v in enumerate(mask):
        if v:
            if start is None:
                start = i
            last, gap = i, 0
        elif start is not None:
            gap += 1
            if gap > max_gap_frames:
                out.append((start, last))
                start = None
    if start is not None:
        out.append((start, last))
    return out


# --------------------------------------------------------------------------- decision layer
class Vad:
    def __init__(self, aggressiveness):
        self.v = webrtcvad.Vad(aggressiveness) if webrtcvad else None

    def is_speech(self, frame_i16, noise_floor):
        if self.v is not None:
            return self.v.is_speech(frame_i16.tobytes(), SR)
        return rms(frame_i16) > max(250.0, noise_floor * 3.0)


class Gate:
    """Learns the caller's typical loudness (75th percentile of voiced frames during calibration)."""

    def __init__(self):
        self.noise = 150.0
        self.caller = None
        self.calib = []

    def update_noise(self, r):
        self.noise = 0.98 * self.noise + 0.02 * r

    def finish_calibration(self):
        if self.calib:
            self.caller = float(np.percentile(self.calib, 75))

    def loud_enough(self, r, factor):
        if self.caller is None:
            return r > self.noise * 3.0
        return r > self.caller * factor


class Lab:
    def __init__(self, a, truth=None):
        self.a = a
        self.vad = Vad(a.vad_agg)
        self.gate = Gate()
        self.truth = truth
        self.calibrated = False
        sp, ls = (float(v) for v in a.cycle.split(","))
        self.sp, self.ls = sp, ls
        self._reset_run()
        self.accepts = []             # (time_s, label or None)
        self.rejects = 0
        self.kept = 0
        self.dropped = 0
        self.log = []

    # -- simulated agent state
    def _pos(self, t):
        return (t - self.a.calib) % (self.sp + self.ls)

    def agent_speaking(self, t):
        return t >= self.a.calib and self._pos(t) < self.sp

    def speak_started(self, t):
        return t - self._pos(t)

    # -- run bookkeeping
    def _reset_run(self):
        self.run_frames = 0
        self.run_ok = 0
        self.run_start_idx = 0
        self.run_start_t = 0.0
        self.accepted_in_run = False

    def _say(self, t, msg):
        line = f"[{t:7.2f}s] {msg}"
        self.log.append(line)
        print("\n" + line if self.a.mic else line)

    def _label(self, idx):
        if self.truth is None:
            return None
        seg = self.truth[self.run_start_idx: idx + 1]
        return bool(len(seg) and seg.mean() >= 0.5)

    # -- per frame
    def process(self, frame, idx):
        a = self.a
        t = idx * FRAME_MS / 1000.0
        r = rms(frame)
        voiced = self.vad.is_speech(frame, self.gate.noise)

        if t >= a.calib and not self.calibrated:
            self.gate.finish_calibration()
            self.calibrated = True
            self._say(t, f"CALIBRATED  caller_rms={self.gate.caller}  noise_floor={self.gate.noise:.0f}"
                         f"  (agent now cycles {self.sp:.0f}s speak / {self.ls:.0f}s listen)")

        if not voiced:
            self.gate.update_noise(r)
            if self.run_frames:
                self.end_run(t)
            return r, voiced

        if self.run_frames == 0:
            self.run_start_idx, self.run_start_t = idx, t
        self.run_frames += 1
        if t < a.calib:
            self.gate.calib.append(r)
            return r, voiced
        loud = self.gate.loud_enough(r, a.factor)
        self.run_ok += int(loud)

        if self.agent_speaking(t) and not self.accepted_in_run:
            run_ms = self.run_frames * FRAME_MS
            ratio = self.run_ok / self.run_frames
            protected = (t - self.speak_started(t)) < a.protect
            if (not protected) and run_ms >= a.min_ms and ratio >= a.ratio:
                self.accepted_in_run = True
                lab = self._label(idx)
                self.accepts.append((t, lab))
                tag = "" if lab is None else ("  <-- TRUE (caller)" if lab else "  <-- FALSE (background!)")
                self._say(t, f"BARGE-IN ACCEPTED  voiced={run_ms}ms loud_ratio={ratio:.2f}{tag}")
        return r, voiced

    def end_run(self, t):
        a = self.a
        dur = self.run_frames * FRAME_MS
        ratio = self.run_ok / max(self.run_frames, 1)
        if self.run_start_t >= a.calib and dur >= 200:
            if self.agent_speaking(self.run_start_t):
                if not self.accepted_in_run:
                    self.rejects += 1
                    if dur < a.min_ms:
                        why = f"too short ({dur}ms < {a.min_ms}ms)"
                    elif ratio < a.ratio:
                        why = f"too quiet for caller (loud_ratio={ratio:.2f} < {a.ratio})"
                    else:
                        why = "inside protected window"
                    self._say(t, f"barge-in rejected: {why}")
            else:
                keep = dur >= 300 and ratio >= 0.6
                if keep:
                    self.kept += 1
                else:
                    self.dropped += 1
                self._say(t, f"turn candidate {'KEPT   ' if keep else 'DROPPED'} voiced={dur}ms loud_ratio={ratio:.2f}")
        self._reset_run()

    # -- summary
    def summary(self, total_frames):
        a = self.a
        print("\n" + "=" * 70)
        print("SUMMARY")
        print(f"  calibrated caller level : {self.gate.caller}")
        print(f"  final noise floor       : {self.gate.noise:.0f}")
        print(f"  barge-ins accepted      : {len(self.accepts)}")
        print(f"  barge-ins rejected      : {self.rejects}")
        print(f"  turn candidates kept    : {self.kept}   dropped: {self.dropped}")
        if self.truth is not None:
            false_acc = sum(1 for _, l in self.accepts if l is False)
            true_acc = sum(1 for _, l in self.accepts if l is True)
            n = min(len(self.truth), total_frames)
            callers = [(s, e) for s, e in runs_of(self.truth[:n])
                       if (e - s + 1) * FRAME_MS >= a.min_ms
                       and self.agent_speaking(s * FRAME_MS / 1000.0)]
            missed = 0
            for s, e in callers:
                lo, hi = s * FRAME_MS / 1000.0, (e + 10) * FRAME_MS / 1000.0
                if not any(lo <= at <= hi for at, _ in self.accepts):
                    missed += 1
            print(f"  TRUE accepts (caller)   : {true_acc}")
            print(f"  FALSE accepts (others)  : {false_acc}   <- these are the interruptions you want at 0")
            print(f"  missed real interrupts  : {missed} of {len(callers)} caller segments while agent spoke")
        print("-" * 70)
        print("Tuning hints:")
        print("  * Background voices still interrupt  -> raise --ratio / --min-ms / --factor, raise --vad-agg")
        print("  * Real caller is not accepted        -> lower --factor / --min-ms, re-calibrate closer to the mic")
        print("=" * 70)


# --------------------------------------------------------------------------- runners
def run_samples(lab, samples):
    n = len(samples) // FRAME
    for i in range(n):
        lab.process(samples[i * FRAME:(i + 1) * FRAME], i)
    lab.summary(n)


def run_mic(lab, a):
    try:
        import sounddevice as sd
    except ImportError:
        sys.exit("sounddevice missing: py -m pip install sounddevice")
    q = queue.Queue()
    in_sr = 16000
    block = in_sr * FRAME_MS // 1000

    def cb(indata, frames, t, status):
        q.put(indata[:, 0].copy())

    print(f"CALIBRATION: speak normally for {a.calib:.0f}s (say your name and a sentence). "
          f"Then stay quiet or let others talk to test false interruptions. Ctrl+C to stop.\n")
    frames_all, idx = [], 0
    try:
        with sd.InputStream(samplerate=in_sr, channels=1, dtype="int16", blocksize=block, callback=cb):
            while True:
                blk = q.get()
                frame = blk.reshape(-1, 2).mean(axis=1).astype(np.int16)   # 16k -> 8k (crude)
                r, voiced = lab.process(frame, idx)
                frames_all.append(frame)
                if idx % 25 == 0:
                    t = idx * FRAME_MS / 1000.0
                    st = "AGENT SPEAKING" if lab.agent_speaking(t) else "listening     "
                    print(f"\rt={t:6.1f}s  rms={r:6.0f}  noise={lab.gate.noise:5.0f}  "
                          f"voiced={'Y' if voiced else '.'}  {st}", end="", flush=True)
                idx += 1
    except KeyboardInterrupt:
        pass
    if a.save and frames_all:
        save_wav_8k(a.save, np.concatenate(frames_all))
        print(f"\nsaved raw mic audio to {a.save} (replay with --wav {a.save})")
    lab.summary(idx)


def demo_signals():
    """Synthetic caller + crowd so you can check the script runs end to end."""
    rng = np.random.default_rng(1)
    dur = 40
    t = np.arange(dur * SR) / SR

    def voice(f0, amp, bursts):
        x = np.zeros_like(t)
        for s, e in bursts:
            m = (t >= s) & (t < e)
            env = amp * (0.6 + 0.4 * np.sin(2 * np.pi * 4 * t[m]))
            sig = sum(np.sin(2 * np.pi * f0 * k * t[m]) / k for k in range(1, 8))
            x[m] = env * sig
        return x

    caller = voice(120, 2500, [(1, 5.5), (8.5, 10.5), (12.5, 14.5), (18.5, 20.5), (22, 24.5), (32, 35)])
    crowd = (voice(190, 1400, [(6.2, 8), (14.8, 17), (16, 18), (25, 29)]) +
             voice(240, 1200, [(6.5, 8.2), (21, 21.8), (26, 30)]) +
             voice(150, 1000, [(15, 18), (27, 31)]))
    caller += rng.normal(0, 40, caller.shape)
    return caller.astype(np.int16), crowd.astype(np.int16)


# --------------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description="Terminal lab for crosstalk / barge-in tuning")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--mic", action="store_true")
    src.add_argument("--wav")
    src.add_argument("--mix", nargs=2, metavar=("CALLER", "CROWD"))
    src.add_argument("--demo", action="store_true")
    p.add_argument("--crowd-db", type=float, default=-6.0, help="crowd level relative to caller (dB), for --mix")
    p.add_argument("--calib", type=float, default=6.0, help="calibration seconds (caller speaks alone)")
    p.add_argument("--cycle", default="5,5", help="simulated agent SPEAK,LISTEN seconds")
    p.add_argument("--protect", type=float, default=1.5, help="seconds after agent starts that cannot be interrupted")
    p.add_argument("--min-ms", type=int, default=700, help="continuous voiced ms needed for barge-in")
    p.add_argument("--ratio", type=float, default=0.7, help="share of voiced frames that must be caller-loud")
    p.add_argument("--factor", type=float, default=0.55, help="loud enough = RMS > caller_rms * factor")
    p.add_argument("--vad-agg", type=int, default=2, choices=[0, 1, 2, 3], help="webrtcvad aggressiveness")
    p.add_argument("--save", help="(--mic) save raw mic audio to this wav for replay")
    a = p.parse_args()

    if webrtcvad is None:
        print("note: webrtcvad not installed, using a simple energy VAD (py -m pip install webrtcvad-wheels)\n")

    if a.mic:
        run_mic(Lab(a), a)
        return
    if a.wav:
        run_samples(Lab(a), load_wav_8k(a.wav))
        return
    if a.demo:
        caller, crowd = demo_signals()
        a.crowd_db = -9.0
        print("DEMO: synthetic caller + 3 'background voices' (not real speech)\n")
    else:
        caller, crowd = load_wav_8k(a.mix[0]), load_wav_8k(a.mix[1])
    mixed = mix_tracks(caller, crowd, a.crowd_db)
    run_samples(Lab(a, truth_mask(caller)), mixed)


if __name__ == "__main__":
    main()
