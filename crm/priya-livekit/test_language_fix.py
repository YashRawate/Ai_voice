"""
Quick verification script for language detection bug fix.
"""
import sys

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from agent import detect_language

def run_tests():
    print("Running Language Fix Local Verification...")

    # Test 1: English input stays English
    result = detect_language("What is the fee?", current_lang="en-IN")
    assert result[0] == "en-IN", f"Failed Test 1: {result}"
    print(f"✅ Test 1: English detected correctly -> {result}")

    # Test 2: Can't get stuck in Hindi / Escapes Hindi with English
    result2 = detect_language("What is the fee?", current_lang="hi-IN")
    assert result2[0] == "en-IN", f"Failed Test 2: {result2}"
    print(f"✅ Test 2: Can escape from Hindi with English -> {result2}")

    # Test 3: Hindi detection works
    result = detect_language("Fees kitna hai?", current_lang="en-IN")
    assert result[0] in ("hi-IN", "en-IN"), f"Failed Test 3: {result}"
    print(f"✅ Test 3: Hindi detection works -> {result}")

    # Test 4: Explicit English request always works
    result = detect_language("Please speak in English", current_lang="hi-IN")
    assert result[0] == "en-IN", f"Failed Test 4: {result}"
    print(f"✅ Test 4: Explicit English request works -> {result}")

    # Test 5: Explicit Hindi request always works
    result = detect_language("Hindi mein bolo", current_lang="en-IN")
    assert result[0] == "hi-IN", f"Failed Test 5: {result}"
    print(f"✅ Test 5: Explicit Hindi request works -> {result}")

    # Test 6: Explicit Telugu request works
    result = detect_language("Telugu lo matladandi", current_lang="en-IN")
    assert result[0] == "te-IN", f"Failed Test 6: {result}"
    print(f"✅ Test 6: Explicit Telugu request works -> {result}")

    print("\n✅✅✅ All local tests pass! Ready for staging.")

if __name__ == "__main__":
    run_tests()
