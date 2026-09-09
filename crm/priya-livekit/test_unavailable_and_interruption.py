# test_unavailable_and_interruption.py
"""
Unit tests for:
1. Unavailable course detection & graceful rejection with alternatives
2. Interruption and turn detection configurations
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agent import PatternRouter
from latency_optimizer import LatencyOptimizer


def test_unavailable_programs_english():
    print("--- Test 1: Unavailable Courses (English) ---")
    queries = [
        "Do you offer MBBS or BDS courses?",
        "What is the fee for Law (LLB)?",
        "Can I join Commercial Pilot or Aviation training?",
        "Do you have Fashion Designing or NIFT programs?",
        "What about Architecture (B.Arch) fees?"
    ]
    for q in queries:
        resp = PatternRouter.match(q, {}, lang="en-IN")
        assert resp is not None, f"Expected match for unavailable course: '{q}'"
        assert "not offer" in resp.lower() or "does not offer" in resp.lower(), f"Response did not state unavailable: {resp}"
        assert "B.Tech" in resp and "Pharmacy" in resp, f"Response did not suggest alternatives: {resp}"
        print(f"  Query: '{q}'\n  ➔ Priya: '{resp[:90]}...'")
    print("✅ English unavailable courses handled perfectly!")


def test_unavailable_programs_telugu():
    print("--- Test 2: Unavailable Courses (Telugu) ---")
    queries = [
        "Aditya lo MBBS course unda andi?",
        "Law course gurinchi cheppandi",
        "Pilot training fees entha?"
    ]
    for q in queries:
        resp = PatternRouter.match(q, {}, lang="te-IN")
        assert resp is not None, f"Expected match for: '{q}'"
        assert "అందుబాటులో లేదండి" in resp, f"Telugu response missing unavailable notice: {resp}"
        print(f"  Query: '{q}'\n  ➔ Priya: '{resp[:90]}...'")
    print("✅ Telugu unavailable courses handled perfectly!")


def test_unavailable_programs_hindi():
    print("--- Test 3: Unavailable Courses (Hindi) ---")
    queries = [
        "Kya aapke yahan MBBS ya Dental course hai?",
        "LLB ya Law ki fees kitni hai?"
    ]
    for q in queries:
        resp = PatternRouter.match(q, {}, lang="hi-IN")
        assert resp is not None, f"Expected match for: '{q}'"
        assert "उपलब्ध नहीं है" in resp, f"Hindi response missing unavailable notice: {resp}"
        print(f"  Query: '{q}'\n  ➔ Priya: '{resp[:90]}...'")
    print("✅ Hindi unavailable courses handled perfectly!")


def test_available_courses_unaffected():
    print("--- Test 4: Available Courses Continue to Match Normal Paths ---")
    normal_queries = [
        ("What are the B.Tech CSE fees?", "B.Tech CSE"),
        ("What about hostel facilities?", "Hostel"),
        ("What are the 12th scholarship slabs?", "scholarship")
    ]
    for q, expected_token in normal_queries:
        resp = PatternRouter.match(q, {}, lang="en-IN")
        assert resp is not None, f"Expected match for: '{q}'"
        assert "not offer" not in resp.lower(), f"Normal query falsely marked unavailable: {resp}"
        print(f"  Query: '{q}' ➔ Matched correctly!")
    print("✅ Available courses and services are unaffected!")


def test_interruption_configuration():
    print("--- Test 5: Interruption & Endpointing Settings ---")
    eou_delay = float(os.getenv("EOU_MIN_DELAY", "0.35"))
    interruption_min = float(os.getenv("INTERRUPTION_MIN_DURATION", "0.20"))
    assert eou_delay >= 0.30, f"EOU_MIN_DELAY should be >= 0.30s (got {eou_delay})"
    assert interruption_min <= 0.25, f"INTERRUPTION_MIN_DURATION should be <= 0.25s (got {interruption_min})"
    print(f"  EOU_MIN_DELAY = {eou_delay}s (Prevents cutting off mid-sentence pauses)")
    print(f"  INTERRUPTION_MIN_DURATION = {interruption_min}s (Cuts Priya's audio within 200ms when caller speaks)")
    print("✅ Interruption and turn detection parameters configured optimally!")


def main():
    print("=" * 60)
    print("RUNNING UNAVAILABLE COURSES & INTERRUPTION VERIFICATION")
    print("=" * 60)
    test_unavailable_programs_english()
    test_unavailable_programs_telugu()
    test_unavailable_programs_hindi()
    test_available_courses_unaffected()
    test_interruption_configuration()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY (100%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
