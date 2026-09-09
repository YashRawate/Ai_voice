# test_midcall_language_switch_memory.py
"""
Regression Test Suite: Mid-Call Language Switch Context & Memory Preservation
Verifies that switching between English, Hindi, Telugu, and Tamil mid-call
retains 100% of the caller's name, program, scores, and conversation history.
"""

import asyncio
import sys
import unittest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from language_handler import LanguageHandler, SessionMemory, LANGUAGE_STYLE_BLOCKS
from agent import process_turn


class TestMidCallLanguageSwitchMemory(unittest.TestCase):

    def setUp(self):
        self.session_id = "test_call_101"
        self.memory = SessionMemory(self.session_id)

    def test_session_memory_keyed_by_session_id(self):
        """Test that memory is keyed strictly by session_id and independent of language."""
        self.assertEqual(self.memory.session_id, "test_call_101")
        self.memory.set_fact("student_name", "Rahul")
        self.memory.set_fact("program", "B.Tech CSE")

        # Verify facts ledger formatting
        ledger = self.memory.get_facts_ledger_str()
        self.assertIn("student_name: Rahul", ledger)
        self.assertIn("program: B.Tech CSE", ledger)

    def test_unified_prompt_substitutes_language_without_wiping_facts(self):
        """Test that build_unified_prompt preserves facts ledger across all languages."""
        self.memory.set_fact("student_name", "Rahul")
        self.memory.set_fact("program", "B.Tech CSE")
        self.memory.set_fact("marks_12", "88%")
        facts = self.memory.get_facts_ledger_str()

        # Prompt in English
        prompt_en = LanguageHandler.build_unified_prompt(
            facts_ledger=facts,
            stage="Stage 3: Eligibility",
            next_field="entrance_exam",
            language_code="en-IN",
            conversation_history="Turn 1: Caller: 'I am Rahul' -> Priya: 'Hello Rahul!'"
        )
        self.assertIn("student_name: Rahul", prompt_en)
        self.assertIn("program: B.Tech CSE", prompt_en)
        self.assertIn("marks_12: 88%", prompt_en)
        self.assertIn(LANGUAGE_STYLE_BLOCKS["en-IN"], prompt_en)

        # Prompt in Hindi (Language switch)
        prompt_hi = LanguageHandler.build_unified_prompt(
            facts_ledger=facts,
            stage="Stage 3: Eligibility",
            next_field="entrance_exam",
            language_code="hi-IN",
            conversation_history="Turn 1: Caller: 'I am Rahul' -> Priya: 'Hello Rahul!'"
        )
        # CRITICAL ASSERTIONS: Facts are 100% preserved
        self.assertIn("student_name: Rahul", prompt_hi)
        self.assertIn("program: B.Tech CSE", prompt_hi)
        self.assertIn("marks_12: 88%", prompt_hi)
        self.assertIn(LANGUAGE_STYLE_BLOCKS["hi-IN"], prompt_hi)

        # Prompt in Telugu (Language switch)
        prompt_te = LanguageHandler.build_unified_prompt(
            facts_ledger=facts,
            stage="Stage 3: Eligibility",
            next_field="entrance_exam",
            language_code="te-IN",
            conversation_history="Turn 1: Caller: 'I am Rahul' -> Priya: 'Hello Rahul!'"
        )
        self.assertIn("student_name: Rahul", prompt_te)
        self.assertIn("program: B.Tech CSE", prompt_te)
        self.assertIn("marks_12: 88%", prompt_te)
        self.assertIn(LANGUAGE_STYLE_BLOCKS["te-IN"], prompt_te)

    def test_multi_turn_midcall_switch_flow(self):
        """Simulate real multi-turn conversation with 3 mid-call language switches."""
        async def run_simulation():
            # Turn 1: English - Name and program stated
            t1 = "Hello, my name is Rahul and I want to join B.Tech CSE."
            res1 = await process_turn(audio_bytes=t1, memory=self.memory, turn_number=1)
            self.assertEqual(self.memory.get_fact("student_name"), "Rahul")
            self.assertEqual(self.memory.get_fact("program"), "B.Tech CSE")
            self.assertEqual(self.memory.current_language, "en-IN")

            # Turn 2: Caller switches to Hindi mid-call and asks fee
            t2 = "Hindi mein baat kariye, B.Tech CSE ki fees kitni hai?"
            res2 = await process_turn(audio_bytes=t2, memory=self.memory, turn_number=2)
            # Memory must NOT be wiped!
            self.assertEqual(self.memory.get_fact("student_name"), "Rahul")
            self.assertEqual(self.memory.get_fact("program"), "B.Tech CSE")
            self.assertEqual(self.memory.current_language, "hi-IN")
            self.assertIn("2,75,000", res2["response"] if isinstance(res2, dict) else str(res2))

            # Turn 3: Caller gives score in Hindi
            t3 = "Mujhe 12th board mein 92% mila hai."
            res3 = await process_turn(audio_bytes=t3, memory=self.memory, turn_number=3)
            self.assertEqual(self.memory.get_fact("marks_12"), "92%")
            self.assertEqual(self.memory.get_fact("student_name"), "Rahul")

            # Turn 4: Caller switches to Telugu mid-call and asks about hostels
            t4 = "Aditya lo hostels unnaaya andi?"
            res4 = await process_turn(audio_bytes=t4, memory=self.memory, turn_number=4)
            self.assertEqual(self.memory.current_language, "te-IN")
            self.assertEqual(self.memory.get_fact("student_name"), "Rahul")
            self.assertEqual(self.memory.get_fact("program"), "B.Tech CSE")
            self.assertEqual(self.memory.get_fact("marks_12"), "92%")

            # Turn 5: Caller switches back to English
            t5 = "Can I book a campus visit for this Saturday?"
            res5 = await process_turn(audio_bytes=t5, memory=self.memory, turn_number=5)
            self.assertEqual(self.memory.current_language, "en-IN")
            self.assertEqual(self.memory.get_fact("student_name"), "Rahul")
            self.assertEqual(len(self.memory.conversation_history), 5)

        asyncio.run(run_simulation())


if __name__ == "__main__":
    unittest.main()
