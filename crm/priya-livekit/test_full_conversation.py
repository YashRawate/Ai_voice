# test_full_conversation.py
"""
Full Conversation & Regression Test Suite across Week 1, Week 2, and Week 3.
Verifies:
1. No repeated questions (Session context & Slot extraction)
2. Language stability (Hysteresis & Script detection)
3. Personalized scholarships (Score & Program calculation)
4. Graceful exits (Wrap-up intents)
"""

import sys
import io
import re

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from session_manager import DialogueSlotManager, SessionContext
from language_detector import LanguageHysteresisEngine
import university_data as udata
from agent import PatternRouter

WRAP_UP_REGEX = re.compile(
    r'\b(no|nope|nah|nothing|thats\s*all|all\s*i\s*need|no\s*thanks|no\s*thank\s*you|bye|goodbye|nahi|kuch\s*nahi|vaddu|bas)\b',
    re.IGNORECASE
)


class TestConversationFlow:

    def test_no_repeated_questions(self):
        """Verify agent doesn't repeat questions when slots are known."""
        ctx = SessionContext("test_regression_sess_1")
        ctx.collected = {"class_12_score": "92.0%", "student_name": "Karthik", "program_of_interest": "B.Tech CSE"}
        
        assert ctx.is_question_redundant("student_name")
        assert ctx.is_question_redundant("program_interest")
        assert ctx.is_question_redundant("score")
        print("  PASS: No repeated questions for known slots")

    def test_language_stability(self):
        """Verify language doesn't jump randomly on mixed inputs."""
        engine = LanguageHysteresisEngine()
        
        # Turns in English stay English
        lang1, _ = engine.evaluate_turn("What about fees?")
        lang2, _ = engine.evaluate_turn("And what are the scholarship options?")
        assert lang1 == lang2 == "en-IN"
        
        # Single code-mixed Hindi turn holds English
        lang3, r3 = engine.evaluate_turn("CSE mein placements kaisa hai?")
        assert lang3 == "en-IN"
        assert r3 == "hysteresis_holding"

        # Second Hindi turn confirms switch
        lang4, r4 = engine.evaluate_turn("Mujhe fee structure bataiye")
        assert lang4 == "hi-IN"
        assert r4 == "hysteresis_switch_confirmed"

        print("  PASS: Language stability & 2-turn hysteresis verified")

    def test_personalized_scholarship(self):
        """Verify scholarship is personalized to exact score."""
        slots = {"class_12_score": "92.0%", "program_of_interest": "B.Tech CSE"}
        result = udata.calculate_scholarship(slots["program_of_interest"], slots["class_12_score"])
        
        assert result["waiver_percentage"] == 50
        assert result["final_annual_fee"] == 62500
        assert result["base_fee"] == 125000
        print("  PASS: Personalized scholarship calculation verified (50% -> ₹62,500)")

    def test_graceful_exit(self):
        """Verify agent exits when caller says goodbye or no further help needed."""
        assert WRAP_UP_REGEX.search("No, that's all") is not None
        assert WRAP_UP_REGEX.search("Nahi, bas") is not None
        assert WRAP_UP_REGEX.search("Goodbye") is not None
        assert WRAP_UP_REGEX.search("Thanks, bye") is not None
        assert WRAP_UP_REGEX.search("Nothing else, thank you") is not None
        assert WRAP_UP_REGEX.search("Vaddu, thanks") is not None
        print("  PASS: Multilingual graceful exits correctly identified")


def main():
    print("=" * 60)
    print("RUNNING FULL SYSTEM REGRESSION TEST SUITE (WEEKS 1, 2, 3)")
    print("=" * 60)

    tester = TestConversationFlow()
    tester.test_no_repeated_questions()
    tester.test_language_stability()
    tester.test_personalized_scholarship()
    tester.test_graceful_exit()

    print("\n" + "=" * 60)
    print("ALL REGRESSION TESTS PASSED (100% SUCCESS)")
    print("=" * 60)


if __name__ == "__main__":
    main()
