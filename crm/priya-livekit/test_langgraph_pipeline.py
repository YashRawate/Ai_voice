# crm/priya-livekit/test_langgraph_pipeline.py
"""
Test suite for LangGraph & LangChain StateGraph Pipeline in AdmitAI Priya Voice Agent.
Verifies:
1. Multi-turn state preservation and slot extraction (name, program, 12th marks, entrance exam).
2. Mid-call language switch (English -> Hindi -> Telugu -> English) preserves facts ledger.
3. Checkpoint restoration across turns using thread_id.
"""

import unittest
from graph import build_call_graph
from langgraph.checkpoint.memory import MemorySaver


class TestLangGraphPipeline(unittest.TestCase):

    def setUp(self):
        self.memory = MemorySaver()
        self.graph = build_call_graph(checkpointer=self.memory)

    def test_multi_turn_flow_and_slot_extraction(self):
        thread_id = "test-call-session-001"
        config = {"configurable": {"thread_id": thread_id}}

        # Turn 1: Initial greeting and name introduction
        turn1_input = {
            "session_id": thread_id,
            "last_user_text": "Hi Priya, my name is Rahul",
            "language_code": "en-IN",
            "facts": {},
            "messages": [],
            "stage": "GREETING",
            "next_field": "student_name",
        }
        res1 = self.graph.invoke(turn1_input, config=config)

        self.assertIn("student_name", res1["facts"])
        self.assertEqual(res1["facts"]["student_name"], "Rahul")
        self.assertEqual(res1["stage"], "PROGRAM")
        self.assertEqual(res1["next_field"], "program")

        # Turn 2: State program interest
        res2 = self.graph.invoke(
            {"last_user_text": "I am looking for B.Tech in CSE with AI and ML"},
            config=config,
        )
        self.assertEqual(res2["facts"]["student_name"], "Rahul")
        self.assertIn(res2["facts"]["program"], ["B.Tech CSE", "B.Tech AI/ML"])
        self.assertEqual(res2["stage"], "ELIGIBILITY")
        self.assertEqual(res2["next_field"], "marks_12")

        # Turn 3: 12th Marks
        res3 = self.graph.invoke(
            {"last_user_text": "I scored 94% in my 12th CBSE boards"},
            config=config,
        )
        self.assertEqual(res3["facts"]["marks_12"], "94%")
        self.assertEqual(res3["facts"]["student_name"], "Rahul")
        self.assertEqual(res3["next_field"], "entrance_exam")

    def test_language_switch_preserves_facts_and_history(self):
        thread_id = "test-call-session-lang-switch-002"
        config = {"configurable": {"thread_id": thread_id}}

        # Step 1: English intro with name and course
        self.graph.invoke(
            {
                "session_id": thread_id,
                "last_user_text": "Hello, my name is Sneha and I am interested in B.Tech ECE.",
                "language_code": "en-IN",
                "facts": {},
                "messages": [],
                "stage": "GREETING",
                "next_field": "student_name",
            },
            config=config,
        )

        # Verify state after step 1
        state_after_step1 = self.graph.get_state(config)
        self.assertEqual(state_after_step1.values["facts"].get("student_name"), "Sneha")
        self.assertEqual(state_after_step1.values["facts"].get("program"), "B.Tech ECE")

        # Step 2: Mid-call switch to Hindi
        res_hi = self.graph.invoke(
            {"last_user_text": "Kya aap Hindi mein baat kar sakte hain? Fees kitni hai?"},
            config=config,
        )
        self.assertEqual(res_hi["language_code"], "hi-IN")
        # Ensure facts were NOT wiped out by language switch
        self.assertEqual(res_hi["facts"].get("student_name"), "Sneha")
        self.assertEqual(res_hi["facts"].get("program"), "B.Tech ECE")

        # Step 3: Mid-call switch to Telugu
        res_te = self.graph.invoke(
            {"last_user_text": "Hostel gurinchi cheppandi, AC rooms unnaya?"},
            config=config,
        )
        self.assertEqual(res_te["language_code"], "te-IN")
        self.assertEqual(res_te["facts"].get("student_name"), "Sneha")
        self.assertEqual(res_te["facts"].get("program"), "B.Tech ECE")

        # Step 4: Switch back to English for booking
        res_en = self.graph.invoke(
            {"last_user_text": "Yes, please schedule our campus visit for Saturday."},
            config=config,
        )
        self.assertEqual(res_en["facts"].get("student_name"), "Sneha")
        self.assertEqual(res_en["facts"].get("program"), "B.Tech ECE")
        self.assertGreater(len(res_en["messages"]), 4)

    def test_yash_test_2_dialogue_zero_repetition(self):
        """Replay exact dialogue from TEST_2.md and verify zero question repetition."""
        thread_id = "test-call-yash-dialogue-003"
        config = {"configurable": {"thread_id": thread_id}}

        # Turn 1: Caller introduces name
        r1 = self.graph.invoke(
            {
                "session_id": thread_id,
                "last_user_text": "My name is Yash",
                "language_code": "en-IN",
                "facts": {},
                "messages": [],
                "stage": "GREETING",
                "next_field": "student_name",
            },
            config=config,
        )
        self.assertEqual(r1["facts"].get("student_name"), "Yash")
        self.assertNotIn("May I know your name", r1["messages"][-1].content)

        # Turn 2: Program of interest
        r2 = self.graph.invoke(
            {"last_user_text": "B.Tech Computer Science"},
            config=config,
        )
        self.assertEqual(r2["facts"].get("student_name"), "Yash")
        self.assertIn("CSE", r2["facts"].get("program", ""))
        self.assertNotIn("May I know your name", r2["messages"][-1].content)

        # Turn 3: 12th score and JEE rank
        r3 = self.graph.invoke(
            {"last_user_text": "In 12th I got 90% and in JEE I got 82 rank."},
            config=config,
        )
        self.assertEqual(r3["facts"].get("marks_12"), "90%")
        self.assertEqual(r3["facts"].get("entrance_exam"), "JEE Main")
        self.assertEqual(r3["stage"], "CONVERT")
        self.assertNotIn("May I know your name", r3["messages"][-1].content)

        # Turn 4: Declined booking
        r4 = self.graph.invoke(
            {"last_user_text": "No, not now."},
            config=config,
        )
        self.assertNotIn("May I know your name", r4["messages"][-1].content)
        self.assertNotIn("Which program", r4["messages"][-1].content)

        # Turn 5: Language switch to Hindi asking about college
        r5 = self.graph.invoke(
            {"last_user_text": "आप मुझे कॉलेज के बारे में बता सकते हो?"},
            config=config,
        )
        self.assertEqual(r5["language_code"], "hi-IN")
        self.assertEqual(r5["facts"].get("student_name"), "Yash")
        self.assertNotIn("नाम", r5["messages"][-1].content)
        self.assertNotIn("12वीं", r5["messages"][-1].content)

        # Turn 6: Asked about hostel in Hindi
        r6 = self.graph.invoke(
            {"last_user_text": "आप हॉस्टल फी के बारे में बताइए।"},
            config=config,
        )
        self.assertEqual(r6["facts"].get("student_name"), "Yash")
        self.assertNotIn("नाम", r6["messages"][-1].content)

        # Turn 7: Mid-call Telugu switch
        r7 = self.graph.invoke(
            {"last_user_text": "Hostel gurinchi cheppandi"},
            config=config,
        )
        self.assertEqual(r7["language_code"], "te-IN")
        self.assertEqual(r7["facts"].get("student_name"), "Yash")
        self.assertNotIn("Mee peru", r7["messages"][-1].content)
        self.assertNotIn("May I know your name", r7["messages"][-1].content)


if __name__ == "__main__":
    unittest.main()

