# run_tests_standalone.py

import asyncio
import numpy as np
import sys
import io

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


async def run_all_tests():
    print("=" * 60)
    print("RUNNING ADVANCED LANGUAGE DETECTION VERIFICATION SUITE")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Audio Quality Gate Tests
    # ---------------------------------------------------------
    print("\n[Layer 1: Audio Quality Gate]")
    gate = AudioQualityGate(sample_rate=16000)

    # Test 1.1: Silence rejection
    res = await gate.is_valid_speech(b'\x00' * 3200)
    assert not res.is_valid, "Silent audio should be rejected"
    print("  PASS: Silent audio rejected (Gate 1 blocked)")

    # Test 1.2: Clipped signal rejection
    loud = np.full(3200, 32767, dtype=np.int16).tobytes()
    res = await gate.is_valid_speech(loud)
    assert not res.is_valid, "Clipped audio should be rejected"
    print("  PASS: Clipped/distorted audio rejected")

    # Test 1.3: Synthetic speech structure
    t = np.linspace(0, 0.5, 8000)
    sine = 0.3 * np.sin(2 * np.pi * 300 * t) + 0.15 * np.sin(2 * np.pi * 600 * t)
    res = await gate.is_valid_speech((sine * 32767).astype(np.int16).tobytes())
    print(f"  PASS: Speech analyzed (SNR: {res.snr_db:.1f} dB, Noise level: {res.noise_level})")

    # ---------------------------------------------------------
    # 2. Conversation Context Tests
    # ---------------------------------------------------------
    print("\n[Layer 2: Conversation Context & Hysteresis]")
    ctx = ConversationContext(default_language="en-IN")
    assert ctx.get_expected_language()["expected_language"] == "en-IN"

    ctx.add_turn("user", "fees entha", "te-IN")
    ctx.add_turn("agent", "fees 1.25 lakhs", "te-IN")
    ctx.add_turn("user", "hostel undha", "te-IN")
    exp = ctx.get_expected_language()
    assert exp["expected_language"] == "te-IN"
    print("  PASS: Multi-turn hysteresis stabilized dominant language to te-IN")

    # ---------------------------------------------------------
    # 3. Explicit Switch Detector Tests
    # ---------------------------------------------------------
    print("\n[Layer 5: Explicit Switch Detector (100% Priority)]")
    explicit_det = ExplicitLanguageSwitchDetector()

    cases = [
        ("speak in English please", "en-IN"),
        ("hindi mein baat karo", "hi-IN"),
        ("telugu lo cheppandi", "te-IN"),
        ("tamil la sollunga", "ta-IN"),
        ("తెలుగులో మాట్లాడండి", "te-IN"),
        ("हिंदी में बोलिए", "hi-IN")
    ]
    for phrase, expected_lang in cases:
        r = explicit_det.detect_explicit_switch(phrase)
        assert r.is_explicit_switch and r.target_language == expected_lang, f"Failed on {phrase}"
        print(f"  PASS: '{phrase}' -> {r.target_language} (conf: {r.confidence})")

    no_switch_queries = [
        "What is the fee structure for CSE?",
        "Yes, 15000",
        "Can I get a scholarship?"
    ]
    for q in no_switch_queries:
        r = explicit_det.detect_explicit_switch(q)
        assert not r.is_explicit_switch
    print("  PASS: Normal queries produce 0 false-positive explicit switches")

    # ---------------------------------------------------------
    # 4. Multi-Signal Language Detector Tests
    # ---------------------------------------------------------
    print("\n[Layer 3: Multi-Signal Language Detection]")
    detector = LanguageDetector()

    res_script = await detector.detect_language_with_confidence("ఫీజు వివరాలు చెప్పండి")
    assert res_script.detected_language == "te-IN"
    print("  PASS: Native Telugu script correctly identified")

    res_mixed = await detector.detect_language_with_confidence("CSE mein kitna fees hai")
    assert res_mixed.detected_language == "hi-IN"
    print("  PASS: Code-mixed Romanized Hinglish identified")

    # ---------------------------------------------------------
    # 5. Switch Decision Logic (4 Gates)
    # ---------------------------------------------------------
    print("\n[Layer 4: Switch Decision 4-Gate Logic]")
    decider = LanguageSwitchDecider()

    # Gate 1: Bad audio
    d1 = await decider.should_switch_language(
        {"is_valid": False, "reason": "Noisy background"},
        {"expected_language": "en-IN", "required_switch_confidence": 0.85},
        {"detected_language": "te-IN", "confidence": 0.95}
    )
    assert not d1.should_switch
    print("  PASS: Gate 1 blocked switch on invalid audio")

    # Gate 3: Low confidence
    d3 = await decider.should_switch_language(
        {"is_valid": True, "confidence": 0.90},
        {"expected_language": "en-IN", "required_switch_confidence": 0.85},
        {"detected_language": "te-IN", "confidence": 0.65}
    )
    assert not d3.should_switch
    print("  PASS: Gate 3 blocked switch on low confidence (0.65 < 0.85)")

    # All Gates Pass
    d_pass = await decider.should_switch_language(
        {"is_valid": True, "confidence": 0.95},
        {"expected_language": "en-IN", "required_switch_confidence": 0.85},
        {"detected_language": "te-IN", "confidence": 0.92}
    )
    assert d_pass.should_switch and d_pass.target_language == "te-IN"
    print("  PASS: Verified strong signal passed all 4 gates -> switched to te-IN")

    # ---------------------------------------------------------
    # 6. Noise Resilience Handler Tests
    # ---------------------------------------------------------
    print("\n[Layer 6: Noise Resilience & Graceful Fallback]")
    handler = NoiseResilienceHandler()

    rec_noisy = await handler.handle_detection_failure(
        {"is_valid": False, "noise_level": "very_noisy"},
        current_language="te-IN"
    )
    assert rec_noisy.action == "ask_repeat"
    assert "క్షమించండి" in rec_noisy.message
    print("  PASS: Degraded audio triggers localized repeat request in Telugu")

    rec_ambiguous = await handler.handle_detection_failure(
        {"is_valid": True, "confidence": 0.5},
        current_language="en-IN",
        detection_result={"confidence": 0.2}
    )
    assert rec_ambiguous.action == "ask_clarification"
    print("  PASS: Ambiguous detection triggers graceful clarification prompt")

    print("\n" + "=" * 60)
    print("ALL 6 LAYERS VERIFIED SUCCESSFULLY (100% PASS RATE)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
