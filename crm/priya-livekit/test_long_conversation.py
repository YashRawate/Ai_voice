# test_long_conversation.py
"""
Comprehensive Verification Test Suite for the 4-Layer Long Conversation Management Architecture.

Tests:
1. Layer 1: Sliding Window (Active Context bounding & FIFO eviction)
2. Layer 2: Fact Memory (Permanent Slot retention across turns, multilingual extraction)
3. Layer 3: Conversation History (Full audit trail, topic tracking, anti-repetition)
4. Layer 4: Dialogue State Machine (Greeting -> Info -> Clarification -> Closing)
5. Spec Walkthrough: Exact 4-turn reference conversation from specification
6. Stress Test: 25+ turn call simulation (zero context loss, bounded LLM context, zero repetition)
7. Multilingual Goodbye Intent Detection (EN, HI, TE, TA)
"""

import sys
import unittest
from datetime import datetime
from long_conversation import (
    SlidingWindow,
    FactMemory,
    ConversationHistory,
    DialogueState,
    LongConversationManager,
)


class TestLayer1SlidingWindow(unittest.TestCase):
    """Layer 1: Sliding Window active context tests."""

    def test_window_retention_and_eviction(self):
        window = SlidingWindow(max_turns=5)
        for i in range(1, 9):
            window.add_turn(f"User utterance {i}", f"Agent utterance {i}")

        # Capacity should be capped at max_turns (5)
        self.assertEqual(len(window), 5)
        turns = window.get_turns()
        self.assertEqual(turns[0]["user"], "User utterance 4")
        self.assertEqual(turns[-1]["user"], "User utterance 8")

    def test_formatted_context(self):
        window = SlidingWindow(max_turns=5)
        # Empty context
        self.assertIn("First turn of conversation", window.get_context())

        # Context formatting with turns
        window.add_turn("Hi, I want B.Tech CSE", "Welcome! What is your 12th score?")
        window.add_turn("I scored 85%", "Great! You qualify for a 50% scholarship.")

        ctx = window.get_context(last_n=2)
        self.assertIn("Recent conversation:", ctx)
        self.assertIn("Turn 1:", ctx)
        self.assertIn("User: Hi, I want B.Tech CSE", ctx)
        self.assertIn("Turn 2:", ctx)
        self.assertIn("Agent: Great! You qualify for a 50% scholarship.", ctx)

    def test_token_and_character_boundedness(self):
        window = SlidingWindow(max_turns=8)
        for i in range(20):
            window.add_turn(f"Question {i} about admissions?", f"Answer {i} with concise information.")

        ctx = window.get_context(last_n=8)
        # Context should be well under 2,000 characters (~500 tokens)
        self.assertLess(len(ctx), 1500)


class TestLayer2FactMemory(unittest.TestCase):
    """Layer 2: Permanent Fact Memory extraction and persistence."""

    def setUp(self):
        self.memory = FactMemory()

    def test_extract_facts_english(self):
        facts = self.memory.extract_from_input("My name is Aditya Kumar and I scored 84% in CBSE from Delhi")
        self.assertEqual(facts.get("name"), "Aditya")
        self.assertEqual(facts.get("score"), "84%")
        self.assertEqual(facts.get("city"), "Delhi")

    def test_extract_program_and_exam(self):
        facts = self.memory.extract_from_input("I want to join B.Tech CSE and I appeared for JEE and AP EAPCET")
        self.assertEqual(facts.get("program"), "B.Tech CSE")
        self.assertIn("JEE", facts.get("exam", ""))
        self.assertIn("AP_EAPCET", facts.get("exam", ""))

    def test_multilingual_fact_extraction(self):
        # Telugu pattern
        mem_te = FactMemory()
        te_facts = mem_te.extract_from_input("నా పేరు Suresh, Hyderabad lo untamu, 88 percentage vachindi")
        self.assertEqual(te_facts.get("name"), "Suresh")
        self.assertEqual(te_facts.get("city"), "Hyderabad")
        self.assertEqual(te_facts.get("score"), "88%")

        # Hindi pattern
        mem_hi = FactMemory()
        hi_facts = mem_hi.extract_from_input("Mera naam Rahul hai, Mumbai se bol raha hoon, 91 percent marks hai")
        self.assertEqual(hi_facts.get("name"), "Rahul")
        self.assertEqual(hi_facts.get("city"), "Mumbai")
        self.assertEqual(hi_facts.get("score"), "91%")

    def test_permanent_persistence_and_formatting(self):
        self.memory.extract_from_input("I am Priya, looking for B.Tech AI/ML")
        self.memory.extract_from_input("I got 92% in 12th board")
        self.memory.update_fact("campus_visit", "Tomorrow at 10 AM")

        formatted = self.memory.get_formatted()
        self.assertIn("KNOWN FACTS ABOUT CALLER", formatted)
        self.assertIn("Name: Priya", formatted)
        self.assertIn("Program: B.Tech AI/ML", formatted)
        self.assertIn("Score: 92%", formatted)
        self.assertIn("Campus Visit: Tomorrow at 10 AM", formatted)
        self.assertIn("NEVER ask for details listed above", formatted)


class TestLayer3ConversationHistory(unittest.TestCase):
    """Layer 3: Full history audit trail & topic discussion tracking."""

    def setUp(self):
        self.history = ConversationHistory(call_id="call_test_101")

    def test_full_history_never_evicted(self):
        for i in range(1, 26):
            self.history.add_turn(f"User message {i}", f"Agent message {i}")

        self.assertEqual(len(self.history.full_history), 25)
        self.assertEqual(self.history.full_history[0]["user"], "User message 1")
        self.assertEqual(self.history.full_history[-1]["user"], "User message 25")

    def test_topic_tracking_and_anti_repetition(self):
        self.assertTrue(self.history.should_ask_about("fees"))
        self.assertFalse(self.history.has_topic_been_discussed("fees"))

        # Add turn discussing fees
        self.history.add_turn("What is the fee structure for B.Tech CSE?", "It is 1.25 Lakhs per year.")
        self.assertTrue(self.history.has_topic_been_discussed("fees"))
        self.assertFalse(self.history.should_ask_about("fees"))

        # Topic context retrieval
        fee_context = self.history.get_topic_context("fees")
        self.assertIn("Previous discussion about fees", fee_context)
        self.assertIn("What is the fee structure", fee_context)

    def test_refusal_recording(self):
        self.assertFalse(self.history.is_refused("campus_visit"))
        self.history.record_refusal("campus_visit")
        self.assertTrue(self.history.is_refused("campus_visit"))

    def test_export_transcript(self):
        self.history.add_turn("Hi, I want admissions.", "Hello! Welcome to Aditya University.")
        transcript = self.history.get_full_transcript()
        self.assertIn("COMPLETE CALL TRANSCRIPT (call_test_101)", transcript)
        self.assertIn("Priya: Hello! Welcome to Aditya University.", transcript)


class TestLayer4DialogueState(unittest.TestCase):
    """Layer 4: Dialogue State Machine transitions and flow control."""

    def setUp(self):
        self.state = DialogueState()

    def test_initial_state_greeting(self):
        self.assertEqual(self.state.current_state, DialogueState.GREETING)
        self.assertIn("program", self.state.get_missing_info())
        self.assertIn("score", self.state.get_missing_info())

    def test_progression_to_info_gathering(self):
        self.state.mark_info_received("name")
        next_st = self.state.get_next_state()
        self.assertEqual(next_st, DialogueState.INFO_GATHERING)

    def test_progression_to_clarification_and_closing(self):
        self.state.mark_info_received("program")
        self.state.mark_info_received("score")
        next_st = self.state.get_next_state()
        # All core info acquired
        self.assertEqual(next_st, DialogueState.CLARIFICATION)
        self.state.current_state = next_st

        # Once city is also known
        self.state.mark_info_received("city")
        self.state.mark_info_received("name")
        self.assertEqual(self.state.get_next_state(), DialogueState.CLOSING)


class TestSpecReferenceConversation(unittest.TestCase):
    """Verify the EXACT 4-turn reference conversation from user specification."""

    def test_four_turn_spec_walkthrough(self):
        manager = LongConversationManager(call_id="call_spec_4turn")

        # TURN 1: User introduces name and program choice
        # User: "Hi, I'm Aditya Kumar, want B.Tech CSE"
        t1_out = manager.handle_user_input("Hi, I'm Aditya Kumar, want B.Tech CSE")
        self.assertEqual(manager.fact_memory.get_fact("name"), "Aditya")
        self.assertEqual(manager.fact_memory.get_fact("program"), "B.Tech CSE")
        self.assertEqual(t1_out["state"], DialogueState.INFO_GATHERING)

        agent_t1 = "Welcome Aditya! What is your 12th board percentage or score?"
        manager.record_turn("Hi, I'm Aditya Kumar, want B.Tech CSE", agent_t1, topic="program")

        # Verify Layer 1 has 1 turn
        self.assertEqual(len(manager.sliding_window), 1)
        # Verify Layer 2 remembers Aditya & B.Tech CSE
        self.assertEqual(manager.fact_memory.get_fact("name"), "Aditya")
        self.assertEqual(manager.fact_memory.get_fact("program"), "B.Tech CSE")

        # TURN 2: User provides score and city
        # User: "I got 84% in CBSE from Delhi"
        t2_out = manager.handle_user_input("I got 84% in CBSE from Delhi")
        self.assertEqual(manager.fact_memory.get_fact("score"), "84%")
        self.assertEqual(manager.fact_memory.get_fact("city"), "Delhi")
        # All core facts now known
        self.assertTrue(manager.dialogue_state.info_needed["program"])
        self.assertTrue(manager.dialogue_state.info_needed["score"])

        agent_t2 = "Great! With 84%, you qualify for a 50% merit scholarship on tuition."
        manager.record_turn("I got 84% in CBSE from Delhi", agent_t2, topic="scholarship")

        # Verify context prompt includes facts and avoids re-asking
        prompt_ctx = manager.build_context()
        self.assertIn("Name: Aditya", prompt_ctx)
        self.assertIn("Program: B.Tech CSE", prompt_ctx)
        self.assertIn("Score: 84%", prompt_ctx)
        self.assertIn("City: Delhi", prompt_ctx)

        # TURN 3: User asks about hostel
        # User: "What about hostel facilities?"
        t3_out = manager.handle_user_input("What about hostel facilities?")
        self.assertFalse(t3_out["is_goodbye"])
        self.assertIn(t3_out["state"], [DialogueState.CLARIFICATION, DialogueState.CLOSING])

        agent_t3 = "Hostel fee is ₹30,000 per year with AC and Wi-Fi rooms. Would you like to reserve a seat?"
        manager.record_turn("What about hostel facilities?", agent_t3, topic="hostel")

        self.assertTrue(manager.conversation_history.has_topic_been_discussed("hostel"))
        self.assertFalse(manager.conversation_history.should_ask_about("hostel"))

        # TURN 4: User registers and signals goodbye
        # User: "Yes! Register me please. Thank you!"
        t4_out = manager.handle_user_input("Yes! Register me please. Thank you!")
        self.assertTrue(t4_out["is_goodbye"])
        self.assertEqual(t4_out["state"], DialogueState.CLOSING)

        agent_t4 = "Done, Aditya! We have registered your details and sent confirmation to your phone. Best of luck!"
        manager.record_turn("Yes! Register me please. Thank you!", agent_t4, topic="registration")

        # FINAL AUDIT
        summary = manager.get_summary()
        self.assertEqual(summary["turns_count"], 4)
        self.assertEqual(summary["state"], DialogueState.CLOSING)
        self.assertEqual(summary["facts"]["name"], "Aditya")
        self.assertEqual(summary["facts"]["program"], "B.Tech CSE")
        self.assertEqual(summary["facts"]["score"], "84%")
        self.assertEqual(summary["facts"]["city"], "Delhi")


class TestLongCallSimulation25Turns(unittest.TestCase):
    """Simulate long conversation (25+ turns, 30-minute call scenario)."""

    def test_25_turns_memory_retention_and_anti_repetition(self):
        manager = LongConversationManager(call_id="call_long_25_turns", max_window_turns=8)

        # Turn 1: User introduces name and score
        manager.handle_user_input("Hello, I am Vikram and I got 91% in 12th board.")
        manager.record_turn(
            "Hello, I am Vikram and I got 91% in 12th board.",
            "Welcome Vikram! With 91%, you qualify for our top scholarship. What course are you looking for?",
            topic="scholarship",
        )

        # Turn 2: User states program
        manager.handle_user_input("I am looking for B.Tech AI/ML.")
        manager.record_turn(
            "I am looking for B.Tech AI/ML.",
            "Excellent choice! Our AI/ML department has top tier lab facilities.",
            topic="program",
        )

        # Turns 3 to 24: User asks 22 distinct questions on various campus topics
        topics_sequence = [
            ("What are the total fees for AI/ML?", "fees"),
            ("Can you tell me about the campus placement packages?", "placements"),
            ("Which top companies recruit on campus?", "placements"),
            ("Are there internships provided in the 3rd year?", "internships"),
            ("What are the hostel room sharing options?", "hostel"),
            ("Is mess food included in the hostel fee?", "hostel"),
            ("Do you have Wi-Fi across the campus?", "infrastructure"),
            ("What sports facilities and grounds do you have?", "sports"),
            ("Is there a gym available for students?", "sports"),
            ("Where is the campus located exactly?", "location"),
            ("Are college bus services available across the city?", "transport"),
            ("What are the library timings on weekends?", "library"),
            ("Do students need to follow a dress code or uniform?", "dress_code"),
            ("Are semester exams conducted on autonomous syllabus?", "academics"),
            ("Can I apply for government scholarships too?", "scholarships"),
            ("What is the average package for CSE and AI?", "placements"),
            ("Are there coding clubs or hackathons?", "clubs"),
            ("Can parents visit the campus on Saturday?", "campus_visit"),
            ("Do you provide loan assistance documents for SBI?", "loans"),
            ("What documents should I bring during admission?", "documents"),
            ("When does the academic batch start?", "dates"),
            ("Can I pay fees in two installments?", "fees"),
        ]

        for user_q, topic in topics_sequence:
            manager.handle_user_input(user_q)
            manager.record_turn(user_q, f"Priya answer for {topic}.", topic=topic)

        # Turn 25: Closing turn
        closing_input = "Thank you so much Priya, that covers everything!"
        t25_out = manager.handle_user_input(closing_input)
        manager.record_turn(closing_input, "You're most welcome, Vikram! All the best!", topic="closing")

        # ── VERIFY CRITICAL GUARANTEES ──

        # 1. Total turns in Layer 3 (Full History) must be exactly 25
        self.assertEqual(len(manager.conversation_history.full_history), 25)

        # 2. Layer 1 (Sliding Window) must hold ONLY the last 8 turns (bounded context)
        self.assertEqual(len(manager.sliding_window), 8)

        # 3. Layer 2 (Permanent Facts) must STILL retain Turn 1 facts (survived sliding window drops)
        self.assertEqual(manager.fact_memory.get_fact("name"), "Vikram")
        self.assertEqual(manager.fact_memory.get_fact("score"), "91%")
        self.assertEqual(manager.fact_memory.get_fact("program"), "B.Tech AI/ML")

        # 4. Layer 3 Anti-repetition: Topics discussed must NOT be re-asked
        self.assertFalse(manager.conversation_history.should_ask_about("fees"))
        self.assertFalse(manager.conversation_history.should_ask_about("placements"))
        self.assertFalse(manager.conversation_history.should_ask_about("hostel"))
        self.assertFalse(manager.conversation_history.should_ask_about("scholarships"))
        self.assertTrue(manager.conversation_history.has_topic_been_discussed("hostel"))

        # 5. Layer 4 Goodbye recognized
        self.assertTrue(t25_out["is_goodbye"])
        self.assertEqual(manager.dialogue_state.current_state, DialogueState.CLOSING)

        # 6. Context prompt check: contains known facts and sliding window context
        ctx = manager.build_context()
        self.assertIn("Name: Vikram", ctx)
        self.assertIn("Program: B.Tech AI/ML", ctx)
        self.assertIn("Score: 91%", ctx)
        self.assertIn("CONVERSATION STATE: closing", ctx)


class TestMultilingualGoodbyeDetection(unittest.TestCase):
    """Test goodbye detection across supported languages."""

    def setUp(self):
        self.manager = LongConversationManager(call_id="call_goodbye")

    def test_english_goodbyes(self):
        for phrase in ["thank you", "thanks Priya", "bye bye", "goodbye", "that is all", "that's it"]:
            self.assertTrue(self.manager.is_goodbye(phrase), f"Failed on: {phrase}")

    def test_hindi_goodbyes(self):
        for phrase in ["धन्यवाद", "शुक्रिया", "बस इतना ही", "ठीक है शुक्रिया", "बाय"]:
            self.assertTrue(self.manager.is_goodbye(phrase), f"Failed on: {phrase}")

    def test_telugu_goodbyes(self):
        for phrase in ["ధన్యవాదాలు", "చాలు", "ఇక చాలు", "సరే థాంక్స్", "థాంక్స్"]:
            self.assertTrue(self.manager.is_goodbye(phrase), f"Failed on: {phrase}")

    def test_tamil_goodbyes(self):
        for phrase in ["நன்றி", "போதும்", "வணக்கம்"]:
            self.assertTrue(self.manager.is_goodbye(phrase), f"Failed on: {phrase}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
