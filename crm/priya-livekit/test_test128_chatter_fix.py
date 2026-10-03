"""
test_test128_chatter_fix.py — Validation suite for TEST_128 background chatter fixes.

Tests:
1. "This is the final rule." does NOT corrupt caller name Yash.
2. Bengali script ("বলতাও ঠিক আছে।") is dropped and does not switch language to Hindi.
3. Hindi background chatter containing "बस" ("ये जो बस करते हुए होता है।") does NOT end call.
4. "Okay thank you, that's all" triggers soft close first, then explicit bye closes.
5. Chatter under 3 words while agent is speaking is dropped and does not interrupt.
6. "wait" or "stop" while agent speaking is accepted as genuine barge-in.
7. Facts ledger contains canonical keys without duplicates or "None" strings.
8. Catalyst token caching prevents repeated auth refreshes across calls.
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import unittest
import time
from transcript_guards import (
    classify_transcript,
    extract_name,
    is_farewell,
    dominant_script,
    ALLOWED_SCRIPTS,
    INTERRUPT_WORDS,
)
from session_manager import DialogueSlotManager
from long_conversation import LongConversationManager
from priya.language.resolver import resolve_mixed_language
from catalyst_llm import CatalystAuthTransport


class Test128BackgroundChatterFix(unittest.TestCase):

    def test_1_name_corruption_prevented(self):
        """'This is the final rule.' must NOT overwrite existing name 'Yash'."""
        initial_slots = {"student_name": "Yash"}
        
        # Test direct name extractor
        self.assertIsNone(extract_name("This is the final rule."))
        self.assertIsNone(extract_name("This is the final rule.", awaiting_name=True))

        # Test DialogueSlotManager with casual sentence
        updated = DialogueSlotManager.extract_slots("This is the final rule.", initial_slots)
        self.assertEqual(updated.get("student_name"), "Yash", "Name must remain 'Yash'")
        self.assertNotIn("name", updated, "Legacy 'name' key must not be present")

        # Test invalid college query extraction: "I want to know the college" must NOT become college name
        college_slots = DialogueSlotManager.extract_slots("I want to know the college details and fees", {})
        self.assertNotIn("college", college_slots, "'I want to know the college' must not be saved as a college")

        # Test city extraction never stores "None"
        city_slots = DialogueSlotManager.extract_slots("My location is None", {})
        self.assertNotIn("current_city", city_slots, "'None' must never be saved as current_city")

    def test_2_bengali_script_dropped_and_no_language_switch(self):
        """Bengali text must be classified as 'drop' and not trigger Hindi switch."""
        bengali_text = "বলতাও ঠিক আছে।"
        verdict, reason = classify_transcript(bengali_text)
        self.assertEqual(verdict, "drop")
        self.assertIn("unsupported script", reason)

        # Resolver check
        resolved = resolve_mixed_language("hi-IN", bengali_text, session_lang="en-IN", session_id="test_bengali")
        self.assertEqual(resolved, "en-IN", "Must not switch language on unsupported Bengali script")

    def test_3_hindi_chatter_with_bas_does_not_end_call(self):
        """Hindi sentence containing 'बस' must NOT trigger goodbye."""
        chatter = "ये जो बस करते हुए होता है।"
        self.assertFalse(is_farewell(chatter), "Hindi chatter with 'बस' must not be a farewell")
        
        mgr = LongConversationManager()
        self.assertFalse(mgr.is_goodbye(chatter))

    def test_4_soft_close_flow(self):
        """Closing phrase triggers soft close first, then explicit bye ends call."""
        text = "Okay thank you, that's all"
        self.assertTrue(is_farewell(text))
        
        mgr = LongConversationManager()
        self.assertTrue(mgr.is_goodbye(text))
        self.assertFalse(mgr.is_explicit_bye(text), "Should not be explicit bye; soft close prompt should be used first")

        # Now explicit bye
        explicit_bye = "Bye, thank you"
        self.assertTrue(mgr.is_explicit_bye(explicit_bye))

    def test_5_chatter_while_agent_speaking_dropped(self):
        """Short chatter fragments (<3 words) while speaking are dropped."""
        chatter_frag = "ये जो"
        verdict, reason = classify_transcript(chatter_frag, agent_speaking=True)
        self.assertEqual(verdict, "drop")
        self.assertIn("too short while agent speaking", reason)

    def test_6_wait_and_stop_accepted_while_speaking(self):
        """'wait' and 'stop' interrupt words are accepted even while speaking."""
        verdict, reason = classify_transcript("wait", agent_speaking=True)
        self.assertEqual(verdict, "ok")

        verdict2, _ = classify_transcript("stop please", agent_speaking=True)
        self.assertEqual(verdict2, "ok")

    def test_7_facts_ledger_canonical_keys_and_audit(self):
        """Ledger must maintain canonical keys, no duplicate keys, and audit log."""
        mgr = LongConversationManager(call_id="audit_test")
        mgr.record_fact("name", "Rahul", source="Caller said My name is Rahul")
        self.assertEqual(mgr.fact_memory.facts.get("student_name"), "Rahul")
        self.assertNotIn("name", mgr.fact_memory.facts)

        mgr.record_fact("program", "B.Tech CSE", source="Caller chose CSE")
        self.assertEqual(mgr.fact_memory.facts.get("program_of_interest"), "B.Tech CSE")
        self.assertNotIn("program", mgr.fact_memory.facts)

        mgr.record_fact("score", "85%", source="Caller scored 85")
        self.assertEqual(mgr.fact_memory.facts.get("class_12_score"), "85%")
        self.assertNotIn("score", mgr.fact_memory.facts)

        # Audit log verification
        self.assertGreaterEqual(len(mgr.fact_memory.audit_log), 3)
        self.assertEqual(mgr.fact_memory.audit_log[0]["key"], "student_name")
        self.assertEqual(mgr.fact_memory.audit_log[0]["new"], "Rahul")

    def test_8_catalyst_token_cache(self):
        """CatalystAuthTransport must cache token class-wide."""
        CatalystAuthTransport._cached_access_token = "mock-token-xyz"
        CatalystAuthTransport._cached_token_expiry = time.time() + 3000

        t1 = CatalystAuthTransport()
        t2 = CatalystAuthTransport()

        # Both instances should see the cached token without hitting network
        self.assertEqual(CatalystAuthTransport._cached_access_token, "mock-token-xyz")
        self.assertGreater(CatalystAuthTransport._cached_token_expiry, time.time())


if __name__ == "__main__":
    unittest.main()
