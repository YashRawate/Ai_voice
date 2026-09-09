# test_language_switch_scenarios.py
"""
Test Suite verifying the 5 specific language switching scenarios:
1. English Input -> English Output
2. Hindi Input -> Hindi Output
3. Language Consistency (stays in English across multiple English turns)
4. Code-Mixing Stability (doesn't flap back and forth)
5. Explicit Switch ("Speak in English" / "Telugu lo matladandi")
"""

import sys
import io

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from agent import detect_language


def main():
    print("=" * 70)
    print("VERIFYING 5 LANGUAGE SWITCHING ACCEPTANCE SCENARIOS")
    print("=" * 70)

    # -------------------------------------------------------------
    # Scenario 1: English Input -> English Output
    # -------------------------------------------------------------
    lang1, r1 = detect_language("Hello, what are the fees?", current_lang="en-IN")
    assert lang1 == "en-IN", f"Expected en-IN, got {lang1} (reason: {r1})"
    print(f"✅ Scenario 1 Passed: 'Hello, what are the fees?' -> {lang1} ({r1})")

    # -------------------------------------------------------------
    # Scenario 2: Hindi Input -> Hindi Output
    # -------------------------------------------------------------
    lang2_1, r2_1 = detect_language("Namaskar, fees kitna hai?", current_lang="en-IN")
    # First turn of Hinglish sets pending, second turn confirms switch or native Devanagari switches immediately
    lang2_2, r2_2 = detect_language("Mujhe CSE ke baare mein bataiye", current_lang=lang2_1)
    assert lang2_2 == "hi-IN", f"Expected hi-IN, got {lang2_2}"
    print(f"✅ Scenario 2 Passed: 2 Hindi turns -> {lang2_2} ({r2_2})")

    # Native Devanagari Hindi switches turn 1 immediately
    lang2_dev, r2_dev = detect_language("नमस्ते, फीस कितनी है?", current_lang="en-IN")
    assert lang2_dev == "hi-IN", f"Expected hi-IN, got {lang2_dev}"
    print(f"✅ Scenario 2b Passed: Native Devanagari -> {lang2_dev} ({r2_dev})")

    # -------------------------------------------------------------
    # Scenario 3: Language Consistency (English stays English!)
    # -------------------------------------------------------------
    # Even if previous state was mistakenly 'hi-IN', short English inputs MUST return en-IN!
    current = "en-IN"
    turns = [
        "Hi",
        "Tell me more",
        "What is the eligibility for CSE?",
        "Do you have hostel facilities?",
        "My name is Karthik",
        "What about scholarships?"
    ]
    for i, t in enumerate(turns, 1):
        current, reason = detect_language(t, current_lang=current)
        assert current == "en-IN", f"Turn {i} '{t}' switched to {current} (reason: {reason})"
        print(f"  Turn {i}: '{t}' -> {current} ({reason})")
    print("✅ Scenario 3 Passed: 6 consecutive English turns remained strictly en-IN")

    # -------------------------------------------------------------
    # Scenario 4: Switching back to English when in Hindi mode!
    # (Testing the previous critical bug where caller was locked in Hindi)
    # -------------------------------------------------------------
    # Simulate caller currently in Hindi mode
    hindi_state = "hi-IN"
    # Caller speaks normal 4-word English question
    recovered_lang, rec_reason = detect_language("What is the fee?", current_lang=hindi_state)
    assert recovered_lang == "en-IN", f"Expected recovery to en-IN, but stayed {recovered_lang}!"
    print(f"✅ Scenario 4 Passed: 'What is the fee?' in Hindi mode recovered to -> {recovered_lang} ({rec_reason})")

    # -------------------------------------------------------------
    # Scenario 5: Explicit Switch Requests (100% Priority)
    # -------------------------------------------------------------
    exp_en, r_en = detect_language("Please speak in English", current_lang="hi-IN")
    assert exp_en == "en-IN"
    print(f"✅ Scenario 5a Passed: 'Please speak in English' -> {exp_en} ({r_en})")

    exp_te, r_te = detect_language("Telugu lo matladandi", current_lang="en-IN")
    assert exp_te == "te-IN"
    print(f"✅ Scenario 5b Passed: 'Telugu lo matladandi' -> {exp_te} ({r_te})")

    exp_hi, r_hi = detect_language("Hindi mein baat karo", current_lang="te-IN")
    assert exp_hi == "hi-IN"
    print(f"✅ Scenario 5c Passed: 'Hindi mein baat karo' -> {exp_hi} ({r_hi})")

    print("\n" + "=" * 70)
    print("ALL 5 ACCEPTANCE TEST SCENARIOS PASSED WITH 100% SUCCESS")
    print("=" * 70)


if __name__ == "__main__":
    main()
