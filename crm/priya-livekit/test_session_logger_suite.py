# crm/priya-livekit/test_session_logger_suite.py
"""
Test Suite for YASH_TEST Logger.
Verifies that test sessions are saved inside crm/YASH_TEST/ as TEST_1, TEST_2, etc.
"""

import os
import unittest
import shutil
from pathlib import Path
from test_session_logger import TestSessionLogger


class TestSessionLoggerSuite(unittest.TestCase):

    def setUp(self):
        crm_dir = Path(__file__).resolve().parent.parent
        self.yash_test_dir = crm_dir / "YASH_TEST"
        os.makedirs(self.yash_test_dir, exist_ok=True)

    def test_yash_test_creation_and_sequencing(self):
        # ── Run 1 ────────────────────────────────────────────────────────────
        logger1 = TestSessionLogger(session_id="call_yash_001", console=True)
        test_id_1 = logger1.test_id
        self.assertTrue(test_id_1.startswith("TEST_"))

        logger1.log_session_init(reason="call_start", is_first_call=True)
        logger1.log_stt(text="my name is rahul", language="en-IN", confidence=0.94, raw_audio_snr=18.2)
        logger1.log_llm_reply(
            text="Nice to meet you Rahul! Which program are you interested in?",
            stage="PROGRAM",
            facts_snapshot={"name": "Rahul"}
        )
        logger1.log_language_switch(old_lang="en-IN", new_lang="hi-IN", confidence=0.91)
        logger1.log_llm_reply(
            text="Aap kaunse course mein interested hain, Rahul?",
            stage="PROGRAM"
        )
        logger1.log_interruption(reason="stt_socket_drop", detail="Connection reset by peer")
        logger1.log_reconnect(transport="stt_websocket", reason="Connection reset by peer")
        
        file1 = logger1.finalize(disposition="completed", notes="tested language switch mid-call")

        # Verify TEST_1.md exists
        self.assertTrue(os.path.exists(file1))
        with open(file1, "r", encoding="utf-8") as f:
            content1 = f.read()

        self.assertIn(f"# {test_id_1}", content1)
        self.assertIn("🎤 **Caller said**", content1)
        self.assertIn("🤖 **Priya replied**", content1)
        self.assertIn("🌐 **Language switch**", content1)
        self.assertIn(f"### Summary — {test_id_1}", content1)
        self.assertIn("| Session re-inits | 1 (✅ OK) |", content1)

        # ── Run 2 ────────────────────────────────────────────────────────────
        logger2 = TestSessionLogger(session_id="call_yash_002", console=True)
        test_id_2 = logger2.test_id
        
        idx1 = int(test_id_1.split("_")[1])
        idx2 = int(test_id_2.split("_")[1])
        self.assertEqual(idx2, idx1 + 1)

        logger2.log_session_init(reason="call_start", is_first_call=True)
        logger2.log_stt(text="B.Tech CSE fees kitni hai?", language="hi-IN", confidence=0.95)
        logger2.log_llm_reply(
            text="B.Tech CSE ki tuition fee ₹2,75,000 per year hai.",
            stage="CONSULT",
            facts_snapshot={"program": "B.Tech CSE"}
        )
        file2 = logger2.finalize(disposition="interested", notes="fee inquiry test")

        # Verify TEST_2.md exists
        self.assertTrue(os.path.exists(file2))
        with open(file2, "r", encoding="utf-8") as f:
            content2 = f.read()

        self.assertIn(f"# {test_id_2}", content2)
        self.assertIn(f"### Summary — {test_id_2}", content2)


if __name__ == "__main__":
    unittest.main()
