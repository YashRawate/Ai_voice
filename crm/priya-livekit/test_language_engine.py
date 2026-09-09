# test_language_engine.py
"""
Unit tests for LanguageHysteresisEngine (Week 2 of implementation plan).
"""

import sys
import io

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from language_detector import LanguageHysteresisEngine


def main():
    print("=" * 60)
    print("RUNNING LANGUAGE HYSTERESIS ENGINE TEST SUITE")
    print("=" * 60)

    engine = LanguageHysteresisEngine(default_lang="en-IN")

    # Test 1: English question
    lang, reason = engine.evaluate_turn("What are the fee details?")
    assert lang == "en-IN", f"Expected en-IN, got {lang}"
    print("  PASS: Test 1: English stays in English")

    # Test 2: Hindi with English (Hinglish) - should stay English (no 2-turn confirmation yet)
    lang, reason = engine.evaluate_turn("Fees kitna hai CSE mein?")
    assert lang == "en-IN", f"Expected en-IN on turn 1, got {lang}"
    print(f"  PASS: Test 2: Hinglish turn 1/2 held in English (reason: {reason})")

    # Test 3: Second Hindi sentence - NOW it switches to Hindi
    lang, reason = engine.evaluate_turn("Scholarship ke baare mein bataiye")
    assert lang == "hi-IN", f"Expected hi-IN on turn 2, got {lang}"
    print(f"  PASS: Test 3: Second Hindi sentence triggers 2-turn switch (reason: {reason})")

    # Test 4: Explicit switch works immediately
    lang, reason = engine.evaluate_turn("Speak in Telugu please")
    assert lang == "te-IN", f"Expected te-IN, got {lang}"
    print(f"  PASS: Test 4: Explicit switch works immediately (reason: {reason})")

    # Test 5: Native script switch works immediately
    lang, reason = engine.evaluate_turn("నాకు కంప్యూటర్ సైన్స్ కావాలి")
    assert lang == "te-IN", f"Expected te-IN, got {lang}"
    print(f"  PASS: Test 5: Native Telugu script switches immediately (reason: {reason})")

    lang, reason = engine.evaluate_turn("मुझे फीस की जानकारी चाहिए")
    assert lang == "hi-IN", f"Expected hi-IN, got {lang}"
    print(f"  PASS: Test 6: Native Devanagari script switches immediately (reason: {reason})")

    print("\n" + "=" * 60)
    print("ALL LANGUAGE HYSTERESIS TESTS PASSED (100%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
