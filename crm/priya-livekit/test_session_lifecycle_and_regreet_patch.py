# crm/priya-livekit/test_session_lifecycle_and_regreet_patch.py
"""
Test Suite for Session Lifecycle and Re-Greeting Bug Patch.
Verifies:
1. [SESSION_INIT] fires exactly once per call.
2. Mid-call affirmations and background noise acknowledgements do NOT trigger opening greeting or ask for name again.
3. Mid-call language switches (en -> hi -> te -> en) do not trigger re-greeting or wipe facts ledger.
4. Transport reconnection preserves existing session_id, context, and facts without re-greeting.
"""

import unittest
import logging
from session_lifecycle import start_new_call, reconnect_transport, apply_language_switch, get_existing_session, end_call_session
from agent import PatternRouter


class TestSessionLifecycleAndRegreetPatch(unittest.TestCase):

    def setUp(self):
        self.session_id = "test-call-patch-001"
        self.phone = "+919876543210"

    def tearDown(self):
        end_call_session(self.session_id)

    def test_session_init_called_exactly_once(self):
        """Step 1 & 2: start_new_call called once; duplicate calls return existing context without resetting."""
        ctx1 = start_new_call(phone=self.phone, session_id=self.session_id, initial_language="en-IN")
        self.assertEqual(ctx1.session_id, self.session_id)
        self.assertEqual(ctx1.active_language, "en-IN")

        # Mutate context with collected facts
        ctx1.collected["student_name"] = "Karthik"
        ctx1.collected["program"] = "B.Tech CSE"

        # Attempt duplicate init (e.g. from reconnect event)
        ctx2 = start_new_call(phone=self.phone, session_id=self.session_id)
        self.assertIs(ctx1, ctx2)
        self.assertEqual(ctx2.collected.get("student_name"), "Karthik")
        self.assertEqual(ctx2.collected.get("program"), "B.Tech CSE")

    def test_pattern_router_does_not_regreet_or_ask_name_midcall(self):
        """Step 2: Affirmations/short words ('ok', 'haan', 'yes', 'sare') mid-call must NOT re-ask name."""
        collected = {"_name_asked": True, "program_of_interest": "B.Tech CSE"}

        # Mid-call affirmation in English
        resp_en = PatternRouter.match("Yes", collected, lang="en-IN")
        self.assertNotIn("May I know your name", resp_en)
        self.assertIn("Sure!", resp_en)

        # Mid-call affirmation in Hindi
        resp_hi = PatternRouter.match("Haan", collected, lang="hi-IN")
        self.assertNotIn("naam", resp_hi)
        self.assertIn("ज़रूर!", resp_hi)

        # Mid-call affirmation in Telugu
        resp_te = PatternRouter.match("Avunu", collected, lang="te-IN")
        self.assertNotIn("peru", resp_te)
        self.assertIn("ఖచ్చితంగా", resp_te)

    def test_language_switch_does_not_reset_facts_or_history(self):
        """Step 2 & 5: Language switch modifies language_code ONLY."""
        ctx = start_new_call(phone=self.phone, session_id=self.session_id, initial_language="en-IN")
        ctx.collected["student_name"] = "Sneha"
        ctx.collected["marks_12"] = "92%"

        # Switch to Hindi
        apply_language_switch(ctx, "hi-IN", reason="caller_requested_hindi")
        self.assertEqual(ctx.active_language, "hi-IN")
        self.assertEqual(ctx.collected.get("student_name"), "Sneha")
        self.assertEqual(ctx.collected.get("marks_12"), "92%")

        # Switch to Telugu
        apply_language_switch(ctx, "te-IN", reason="caller_requested_telugu")
        self.assertEqual(ctx.active_language, "te-IN")
        self.assertEqual(ctx.collected.get("student_name"), "Sneha")
        self.assertEqual(ctx.collected.get("marks_12"), "92%")

    def test_transport_reconnect_preserves_session_identity(self):
        """Step 3 & 5: Transport reconnect carries original session_id and facts forward."""
        ctx = start_new_call(phone=self.phone, session_id=self.session_id, initial_language="en-IN")
        ctx.collected["student_name"] = "Venkatesh"
        ctx.collected["program_of_interest"] = "B.Tech AI/ML"

        # Simulate network drop & socket reconnection
        reconnect_transport(ctx, reason="websocket_packet_loss_reconnect")

        # Verify session state remains intact
        retrieved_ctx = get_existing_session(self.session_id)
        self.assertIsNotNone(retrieved_ctx)
        self.assertEqual(retrieved_ctx.session_id, self.session_id)
        self.assertEqual(retrieved_ctx.collected.get("student_name"), "Venkatesh")
        self.assertEqual(retrieved_ctx.collected.get("program_of_interest"), "B.Tech AI/ML")


if __name__ == "__main__":
    unittest.main()
