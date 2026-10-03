# crm/priya-livekit/test_persistent_memory.py
"""
Test Suite for 2-Tier Persistent Memory System.
Verifies all 5 core requirements from the specification:
1. Multi-slot extraction in one sentence
2. Explicit boolean flags & monotonic progression
3. Information correction / priority overwrite
4. "I already told you" instant graceful recovery
5. Cross-call persistent memory (Call #1 -> Call #2)
"""

import sys
import os
import unittest
import uuid

from structured_memory import StructuredCallState, PersistentUserStore
from session_manager import DialogueSlotManager


class TestPersistentMemory(unittest.TestCase):

    def setUp(self):
        self.test_db = f"test_user_profiles_{uuid.uuid4().hex[:8]}.db"
        self.user_store = PersistentUserStore(db_path=self.test_db)

    def tearDown(self):
        try:
            if os.path.exists(self.test_db):
                os.remove(self.test_db)
        except Exception:
            pass

    def test_1_multiple_answers_in_one_sentence(self):
        """User gives name, course, and score in one turn."""
        user_utterance = "My name is Yash, I am looking for B.Tech CSE and I scored 85 percent in 12th"
        slots = DialogueSlotManager.extract_slots(user_utterance, {})

        self.assertEqual(slots.get("student_name"), "Yash")
        self.assertEqual(slots.get("program_of_interest"), "B.Tech CSE")
        self.assertEqual(slots.get("class_12_score"), "85.0%")

        state = StructuredCallState(call_id="call_001")
        state.merge_facts(slots)

        self.assertTrue(state.name_collected)
        self.assertTrue(state.program_collected)
        self.assertTrue(state.marks_collected)
        # Next missing field should skip name, program, marks and ask for city or college
        self.assertIn(state.determine_next_missing_step(), ["city", "college"])

    def test_2_correction_handling(self):
        """User corrects previously stated score and course."""
        initial_slots = {"student_name": "Yash", "program_of_interest": "B.Tech Mechanical", "class_12_score": "72.0%"}
        state = StructuredCallState(call_id="call_002")
        state.merge_facts(initial_slots)

        self.assertEqual(state.marks, "72.0%")
        self.assertEqual(state.program, "B.Tech Mechanical")

        # Caller issues correction
        correction_text = "Actually, sorry, my marks are 82% and I want to change to B.Tech CSE"
        updated_slots = DialogueSlotManager.extract_slots(correction_text, initial_slots)
        state.merge_facts(updated_slots, is_correction=True)

        self.assertEqual(state.marks, "82.0%")
        self.assertEqual(state.program, "B.Tech CSE")

    def test_3_already_told_you_interception(self):
        """Agent detects when user reminds about previously given info."""
        slots = {"student_name": "Yash", "program_of_interest": "B.Tech CSE", "class_12_score": "82.0%"}

        ack_name = DialogueSlotManager.detect_already_told("I already told you my name!", slots)
        self.assertIsNotNone(ack_name)
        self.assertIn("Yash", ack_name)

        ack_prog = DialogueSlotManager.detect_already_told("Maine already apna course bataya tha, CSE", slots)
        self.assertIsNotNone(ack_prog)
        self.assertIn("B.Tech CSE", ack_prog)

        ack_score = DialogueSlotManager.detect_already_told("I already gave you my marks", slots)
        self.assertIsNotNone(ack_score)
        self.assertIn("82.0%", ack_score)

    def test_4_cross_call_memory_persistence(self):
        """Call #1 collects facts and saves to store; Call #2 loads immediately."""
        phone = "+919876543210"

        # Call #1
        state_call_1 = StructuredCallState(call_id="call_101", phone_number=phone)
        slots_turn_1 = DialogueSlotManager.extract_slots("My name is Yash and I want B.Tech CSE", {})
        state_call_1.merge_facts(slots_turn_1)

        slots_turn_2 = DialogueSlotManager.extract_slots("I scored 88% in 12th board", state_call_1.to_dict())
        state_call_1.merge_facts(slots_turn_2)

        # Call #1 ends -> persist profile
        self.user_store.save_profile(phone, state_call_1.to_dict())

        # Call #2 (one week later)
        loaded_profile = self.user_store.get_profile(phone)
        self.assertIsNotNone(loaded_profile)
        self.assertEqual(loaded_profile.get("name"), "Yash")
        self.assertEqual(loaded_profile.get("program"), "B.Tech CSE")
        self.assertEqual(loaded_profile.get("marks"), "88.0%")

        # Seed Call #2 state
        state_call_2 = StructuredCallState(call_id="call_102", phone_number=phone)
        state_call_2.merge_facts(loaded_profile)

        # Name, program, and marks are already collected, so next step moves directly to city/visit!
        self.assertTrue(state_call_2.name_collected)
        self.assertTrue(state_call_2.program_collected)
        self.assertTrue(state_call_2.marks_collected)
        self.assertIn(state_call_2.determine_next_missing_step(), ["city", "college", "campus_visit"])


if __name__ == "__main__":
    unittest.main()
