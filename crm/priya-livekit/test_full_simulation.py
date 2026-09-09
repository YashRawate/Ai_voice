# test_full_simulation.py

import sys
import io
import time
import asyncio
import numpy as np

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from audio_quality_gate import AudioQualityGate
from conversation_context import ConversationContext
from language_detector import LanguageDetector
from explicit_switch_detector import ExplicitLanguageSwitchDetector
from switch_decision import LanguageSwitchDecider
from noise_resilience_handler import NoiseResilienceHandler
from agent import detect_language, _LANG_DETECTOR, _EXPLICIT_DETECTOR


async def run_end_to_end_test_scenarios():
    print("=" * 70)
    print("ADVANCED LANGUAGE DETECTION SYSTEM: COMPREHENSIVE SIMULATION & BENCHMARKS")
    print("=" * 70)

    audio_gate = AudioQualityGate(sample_rate=16000)
    context = ConversationContext(default_language="en-IN")
    detector = LanguageDetector()
    explicit_detector = ExplicitLanguageSwitchDetector()
    decider = LanguageSwitchDecider(max_switches_per_call=5, allowed_languages={"en-IN", "te-IN", "hi-IN", "ta-IN"})
    noise_handler = NoiseResilienceHandler()

    # Synthetic Audio Generators
    def generate_clean_speech():
        t = np.linspace(0, 0.4, 6400)
        # Fundamental speech frequencies (200Hz + harmonics)
        sine = 0.3 * np.sin(2 * np.pi * 220 * t) + 0.2 * np.sin(2 * np.pi * 440 * t)
        return (sine * 32767).astype(np.int16).tobytes()

    def generate_paper_shuffle_noise():
        # High-frequency random noise with low SNR
        noise = np.random.randn(6400).astype(np.float32) * 0.005
        return (noise * 32767).astype(np.int16).tobytes()

    def generate_silence():
        return b'\x00' * 3200

    scenarios = [
        {
            "id": "SCENARIO 1",
            "name": "Noise Resilience (Paper rustling / background noise + Short Answer)",
            "audio_func": generate_paper_shuffle_noise,
            "transcript": "Yes, 15000",
            "current_lang": "en-IN",
            "stt_lang": "en-IN",
            "expected_decision": "stay",
            "expected_lang": "en-IN"
        },
        {
            "id": "SCENARIO 2",
            "name": "Code-Mixed Hinglish Question",
            "audio_func": generate_clean_speech,
            "transcript": "CSE branch mein kitna fees hai?",
            "current_lang": "en-IN",
            "stt_lang": "hi-IN",
            "expected_decision": "switch",
            "expected_lang": "hi-IN"
        },
        {
            "id": "SCENARIO 3",
            "name": "Code-Mixed Tenglish Question (Telugu + English)",
            "audio_func": generate_clean_speech,
            "transcript": "hostel facility ela undi campus lo?",
            "current_lang": "en-IN",
            "stt_lang": "te-IN",
            "expected_decision": "switch",
            "expected_lang": "te-IN"
        },
        {
            "id": "SCENARIO 4",
            "name": "Explicit Switch to Telugu (Romanized request)",
            "audio_func": generate_clean_speech,
            "transcript": "telugu lo cheppandi please",
            "current_lang": "en-IN",
            "stt_lang": "en-IN",
            "expected_decision": "explicit_switch",
            "expected_lang": "te-IN"
        },
        {
            "id": "SCENARIO 5",
            "name": "Explicit Switch to Hindi (Native Devanagari)",
            "audio_func": generate_clean_speech,
            "transcript": "हिंदी में बात कीजिए",
            "current_lang": "te-IN",
            "stt_lang": "hi-IN",
            "expected_decision": "explicit_switch",
            "expected_lang": "hi-IN"
        },
        {
            "id": "SCENARIO 6",
            "name": "English Reversion after Indic Turns",
            "audio_func": generate_clean_speech,
            "transcript": "Can you tell me about the scholarship eligibility criteria?",
            "current_lang": "hi-IN",
            "stt_lang": "en-IN",
            "expected_decision": "switch",
            "expected_lang": "en-IN"
        },
        {
            "id": "SCENARIO 7",
            "name": "Short Numeric Score in Telugu Context (Sticky Lock)",
            "audio_func": generate_clean_speech,
            "transcript": "12500 rank",
            "current_lang": "te-IN",
            "stt_lang": "en-IN",
            "expected_decision": "stay",
            "expected_lang": "te-IN"
        },
        {
            "id": "SCENARIO 8",
            "name": "Tamil Explicit Request in Tamil Script",
            "audio_func": generate_clean_speech,
            "transcript": "தமிழில் பேசுங்கள்",
            "current_lang": "en-IN",
            "stt_lang": "ta-IN",
            "expected_decision": "explicit_switch",
            "expected_lang": "ta-IN"
        }
    ]

    results = []
    latencies = []

    print("\nExecuting Test Scenarios...\n")

    for sc in scenarios:
        audio_bytes = sc["audio_func"]()
        transcript = sc["transcript"]
        cur_lang = sc["current_lang"]
        stt_lang = sc["stt_lang"]

        t0 = time.perf_counter()

        # Step 1: Layer 1 Audio Quality Check
        t_l1 = time.perf_counter()
        audio_quality = await audio_gate.is_valid_speech(audio_bytes)
        lat_l1 = (time.perf_counter() - t_l1) * 1000

        # Step 2: Layer 5 Explicit Switch Check
        t_l5 = time.perf_counter()
        explicit = explicit_detector.detect_explicit_switch(transcript)
        lat_l5 = (time.perf_counter() - t_l5) * 1000

        final_lang = cur_lang
        decision_action = "stay"

        if explicit.is_explicit_switch:
            final_lang = explicit.target_language
            decision_action = "explicit_switch"
            lat_l3 = 0.0
            lat_l4 = 0.0
        else:
            # Step 3: Layer 3 Multi-Signal Detection
            t_l3 = time.perf_counter()
            detection = await detector.detect_language_with_confidence(
                transcript=transcript,
                audio_bytes=audio_bytes,
                stt_language=stt_lang,
                stt_confidence=0.85
            )
            lat_l3 = (time.perf_counter() - t_l3) * 1000

            # Step 4: Layer 2 + Layer 4 Switch Decision
            t_l4 = time.perf_counter()
            context.state.current_language = cur_lang
            context.state.dominant_language = cur_lang
            ctx_exp = context.get_expected_language()

            # agent detect_language function call verification
            agent_detected, agent_reason = detect_language(transcript, current_lang=cur_lang, stt_lang=stt_lang)

            if audio_quality.is_valid:
                decision = await decider.should_switch_language(
                    audio_quality=audio_quality.__dict__,
                    context_expected=ctx_exp,
                    detected=detection.__dict__
                )
                if decision.should_switch:
                    final_lang = decision.target_language
                    decision_action = "switch"
                else:
                    final_lang = agent_detected
                    decision_action = "stay" if agent_detected == cur_lang else "switch"
            else:
                final_lang = cur_lang
                decision_action = "stay"
            lat_l4 = (time.perf_counter() - t_l4) * 1000

        total_lat = (time.perf_counter() - t0) * 1000
        latencies.append(total_lat)

        passed = (final_lang == sc["expected_lang"])
        results.append({
            "scenario": sc["id"],
            "name": sc["name"],
            "input": transcript,
            "from_lang": cur_lang,
            "to_lang": final_lang,
            "expected_lang": sc["expected_lang"],
            "action": decision_action,
            "latency_ms": total_lat,
            "passed": passed
        })

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{sc['id']}] {status} | Latency: {total_lat:.2f}ms")
        print(f"   Input:     \"{transcript}\"")
        print(f"   Language:  {cur_lang} -> {final_lang} (Action: {decision_action})")
        print(f"   Layer Latencies: L1={lat_l1:.2f}ms, L5={lat_l5:.2f}ms, L3={lat_l3:.2f}ms, L4={lat_l4:.2f}ms\n")

    print("=" * 70)
    print("TEST SUMMARY REPORT")
    print("=" * 70)
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["passed"])
    avg_latency = sum(latencies) / len(latencies)

    print(f"Total Scenarios Tested : {total_tests}")
    print(f"Passed                 : {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"Failed                 : {total_tests - passed_tests}")
    print(f"Average Pipeline Latency: {avg_latency:.2f} ms (Budget Target: < 15 ms)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_end_to_end_test_scenarios())
