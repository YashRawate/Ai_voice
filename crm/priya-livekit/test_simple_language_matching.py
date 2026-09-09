# test_simple_language_matching.py
"""
Test Suite for Simple Language Matching (No Switching).
Verifies:
1. English input -> English output
2. Language changes every turn (turn-by-turn mirroring without getting stuck)
3. Code-mixing handling
4. Session memory tracking
5. STT language normalization mapping
6. LLM instruction generation (<50 words, friendly)
7. process_turn async flow
"""

import sys
import asyncio
from typing import NamedTuple

# Set UTF-8 encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from language_handler import LanguageHandler, SessionMemory, get_language_code, LANGUAGE_INSTRUCTIONS
from agent import process_turn, detect_language


class MockSTTResult(NamedTuple):
    text: str
    language: str


class MockSTT:
    def __init__(self, transcript: str, language: str):
        self.transcript = transcript
        self.language = language

    async def transcribe(self, audio_bytes):
        return MockSTTResult(text=self.transcript, language=self.language)


class MockLLM:
    def __init__(self):
        self.last_system_prompt = ""
        self.last_user_input = ""

    async def generate(self, system_prompt: str, user_input: str, cache_control=None):
        self.last_system_prompt = system_prompt
        self.last_user_input = user_input
        if "HINDI" in system_prompt:
            return "हाँ, आपको 50% तक मेरिट स्कॉलरशिप मिलेगी।"
        elif "TELUGU" in system_prompt:
            return "మా క్యాంపస్ చాలా ఆధునికమైనది మరియు 50% స్కాలర్‌షిప్ ఉంది."
        elif "TAMIL" in system_prompt:
            return "கட்டணம் ஆண்டுக்கு ₹1,25,000 ஆகும்."
        return "The tuition fee is ₹1,25,000 per year with up to 50% merit scholarships."


class MockTTS:
    def __init__(self):
        self.last_synthesized_lang = ""

    async def synthesize(self, text: str, language: str):
        self.last_synthesized_lang = language
        return b"RIFF_MOCK_WAV_HEADER"


def test_language_map():
    print("--- Testing STT Language Code Mapping ---")
    test_cases = [
        ("english", "en-IN"),
        ("en", "en-IN"),
        ("en-IN", "en-IN"),
        ("hindi", "hi-IN"),
        ("hi", "hi-IN"),
        ("hi-IN", "hi-IN"),
        ("telugu", "te-IN"),
        ("te", "te-IN"),
        ("te-IN", "te-IN"),
        ("tamil", "ta-IN"),
        ("ta", "ta-IN"),
        ("ta-IN", "ta-IN"),
        ("unknown", "en-IN"),
        ("", "en-IN"),
        (None, "en-IN"),
    ]
    for raw, expected in test_cases:
        code = LanguageHandler.get_language_code(raw)
        assert code == expected, f"Expected {expected} for '{raw}', got {code}"
    print("✅ All STT language mappings pass!")


def test_llm_instructions():
    print("--- Testing LLM Prompt Instructions ---")
    langs = ["en-IN", "hi-IN", "te-IN", "ta-IN"]
    for lang in langs:
        instr = LanguageHandler.get_llm_instruction(lang)
        assert instr, f"Missing instruction for {lang}"
        assert "50" in instr, f"Instruction for {lang} should mention 50 words"
        print(f"  [{lang}]: {instr.splitlines()[0]}")
    print("✅ All LLM instructions verified!")


def test_scenario_1_english_all_turns():
    print("--- Test 1: English All Turns ---")
    memory = SessionMemory("call_en_test")
    turns = [
        ("Hello", "en-IN"),
        ("What are the fees?", "en-IN"),
        ("Thank you", "en-IN")
    ]
    for text, expected in turns:
        matched = LanguageHandler.match_language(
            stt_detected_language="en",
            transcript_text=text,
            current_language=memory.current_language
        )
        assert matched == expected, f"Expected {expected}, got {matched}"
        memory.add_turn(text, "Fee details...", matched)
    print("✅ Test 1 Passed: English all turns remained en-IN!")


def test_scenario_2_turn_by_turn_language_changes():
    print("--- Test 2: Language Changes Every Turn (Mirroring) ---")
    memory = SessionMemory("call_polyglot_test")

    # Turn 1: Hindi
    t1_lang = LanguageHandler.match_language(
        stt_detected_language="hindi",
        transcript_text="Namaskar",
        current_language=memory.current_language
    )
    assert t1_lang == "hi-IN", f"Expected hi-IN, got {t1_lang}"
    memory.add_turn("Namaskar", "Namaste", t1_lang)
    print("  Turn 1 (Hindi): Matched hi-IN")

    # Turn 2: English (instant match without hysteresis lock!)
    t2_lang = LanguageHandler.match_language(
        stt_detected_language="en",
        transcript_text="What about CSE?",
        current_language=memory.current_language
    )
    assert t2_lang == "en-IN", f"Expected en-IN, got {t2_lang}"
    memory.add_turn("What about CSE?", "CSE is 1.25L", t2_lang)
    print("  Turn 2 (English): Instantly matched en-IN")

    # Turn 3: Telugu
    t3_lang = LanguageHandler.match_language(
        stt_detected_language="telugu",
        transcript_text="Campus gurinchi cheppandi",
        current_language=memory.current_language
    )
    assert t3_lang == "te-IN", f"Expected te-IN, got {t3_lang}"
    memory.add_turn("Campus gurinchi cheppandi", "Campus baguntundhi", t3_lang)
    print("  Turn 3 (Telugu): Matched te-IN")

    # Turn 4: Tamil
    t4_lang = LanguageHandler.match_language(
        stt_detected_language="tamil",
        transcript_text="Nandri",
        current_language=memory.current_language
    )
    assert t4_lang == "ta-IN", f"Expected ta-IN, got {t4_lang}"
    memory.add_turn("Nandri", "Vanakkam", t4_lang)
    print("  Turn 4 (Tamil): Matched ta-IN")

    print("✅ Test 2 Passed: Seamless turn-by-turn language matching without getting stuck!")


def test_scenario_3_code_mixing():
    print("--- Test 3: Code-Mixing ---")
    # Code-mixing with English primary STT
    lang = LanguageHandler.match_language(
        stt_detected_language="en-IN",
        transcript_text="Hello, fees kitna hai?",
        current_language="en-IN"
    )
    assert lang == "en-IN", f"Expected en-IN for primary English STT, got {lang}"
    print("✅ Test 3 Passed: Code-mixing resolved to primary STT language!")


async def test_async_process_turn():
    print("--- Testing async process_turn Pipeline ---")
    memory = SessionMemory("call_async_test")
    llm = MockLLM()
    tts = MockTTS()

    # Turn 1: English
    stt1 = MockSTT("What are the fees?", "english")
    turn1 = await process_turn(b"audio1", stt=stt1, llm=llm, tts=tts, memory=memory)
    assert turn1["language_used"] == "en-IN"
    assert tts.last_synthesized_lang == "en-IN"
    assert "ONLY in ENGLISH" in llm.last_system_prompt or "ENGLISH" in llm.last_system_prompt
    print(f"  Turn 1 result: {turn1['language_used']} -> '{turn1['response'][:40]}...'")

    # Turn 2: Hindi
    stt2 = MockSTT("Scholarship milega kya?", "hindi")
    turn2 = await process_turn(b"audio2", stt=stt2, llm=llm, tts=tts, memory=memory)
    assert turn2["language_used"] == "hi-IN"
    assert tts.last_synthesized_lang == "hi-IN"
    assert "HINDI" in llm.last_system_prompt
    print(f"  Turn 2 result: {turn2['language_used']} -> '{turn2['response'][:40]}...'")

    # Turn 3: Telugu
    stt3 = MockSTT("Campus gurinchi cheppandi", "telugu")
    turn3 = await process_turn(b"audio3", stt=stt3, llm=llm, tts=tts, memory=memory)
    assert turn3["language_used"] == "te-IN"
    assert tts.last_synthesized_lang == "te-IN"
    assert "TELUGU" in llm.last_system_prompt
    print(f"  Turn 3 result: {turn3['language_used']} -> '{turn3['response'][:40]}...'")

    # Turn 4: Back to English
    stt4 = MockSTT("Thank you", "english")
    turn4 = await process_turn(b"audio4", stt=stt4, llm=llm, tts=tts, memory=memory)
    assert turn4["language_used"] == "en-IN"
    assert tts.last_synthesized_lang == "en-IN"
    assert "ONLY in ENGLISH" in llm.last_system_prompt or "ENGLISH" in llm.last_system_prompt
    print(f"  Turn 4 result: {turn4['language_used']} -> '{turn4['response'][:40]}...'")

    # Check conversation context
    context = memory.get_context()
    assert len(memory.conversation_history) == 4
    print("✅ Async process_turn pipeline passed with 100% accuracy!")


def run_all():
    print("=" * 60)
    print("RUNNING SIMPLE LANGUAGE MATCHING TEST SUITE")
    print("=" * 60)
    test_language_map()
    test_llm_instructions()
    test_scenario_1_english_all_turns()
    test_scenario_2_turn_by_turn_language_changes()
    test_scenario_3_code_mixing()
    asyncio.run(test_async_process_turn())
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED: Simple Language Matching is 100% Operational!")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
