# test_admission_conversion.py
"""
Test Suite for Priya's Admission Conversion Strategies:
1. Conversion Intent Detection (WhatsApp Link, VIP Campus Visit, ASAT Exam, Seat Reservation).
2. Admission Objection Detection & Directives (Fee, Parent, Exam waiting, Hostel safety).
3. Goodbye Guard against conversion affirmations ("Done, send link" != goodbye).
4. Fast-Path Pattern Router Conversion & Objection Responses.
5. End-to-End Admission Conversion 5-Turn Call Simulation.
"""
import unittest
from long_conversation import LongConversationManager, DialogueState
from agent import PatternRouter


class TestConversionIntentDetection(unittest.TestCase):
    """Test detection of buying signals across English, Telugu, and Hindi."""

    def setUp(self):
        self.mgr = LongConversationManager(call_id="conv_intent_test")

    def test_english_conversion_intents(self):
        self.assertEqual(
            self.mgr.detect_conversion_intent("Can you send me the application link on WhatsApp?"),
            "send_application_link"
        )
        self.assertEqual(
            self.mgr.detect_conversion_intent("I want to visit the campus this Saturday with my parents"),
            "book_campus_visit"
        )
        self.assertEqual(
            self.mgr.detect_conversion_intent("Please register me for the ASAT scholarship test"),
            "register_asat"
        )
        self.assertEqual(
            self.mgr.detect_conversion_intent("I am ready to confirm admission and reserve my seat"),
            "reserve_seat"
        )

    def test_telugu_conversion_intents(self):
        self.assertEqual(
            self.mgr.detect_conversion_intent("డైరెక్ట్ అప్లికేషన్ లింక్ వాట్సాప్‌కు పంపండి"),
            "send_application_link"
        )
        self.assertEqual(
            self.mgr.detect_conversion_intent("నేను ఈ శనివారం క్యాంపస్ విజిట్ కి వస్తాను"),
            "book_campus_visit"
        )
        self.assertEqual(
            self.mgr.detect_conversion_intent("అశాట్ ఎగ్జామ్ రాయడానికి రిజిస్టర్ చేయండి"),
            "register_asat"
        )
        self.assertEqual(
            self.mgr.detect_conversion_intent("నాకు అడ్మిషన్ సీటు బుక్ చేయండి"),
            "reserve_seat"
        )

    def test_hindi_conversion_intents(self):
        self.assertEqual(
            self.mgr.detect_conversion_intent("व्हाट्सएप पर डायरेक्ट एप्लिकेशन फॉर्म भेज दीजिए"),
            "send_application_link"
        )
        self.assertEqual(
            self.mgr.detect_conversion_intent("हम इस शनिवार को कॉलेज कैंपस विजिट के लिए आएंगे"),
            "book_campus_visit"
        )
        self.assertEqual(
            self.mgr.detect_conversion_intent("स्कॉलरशिप टेस्ट असाट के लिए रजिस्टर कर दीजिए"),
            "register_asat"
        )
        self.assertEqual(
            self.mgr.detect_conversion_intent("मुझे सीएसई में एडमिशन सीट कन्फर्म करनी है"),
            "reserve_seat"
        )


class TestAdmissionObjectionDetection(unittest.TestCase):
    """Test detection of core admission objections."""

    def setUp(self):
        self.mgr = LongConversationManager(call_id="conv_obj_test")

    def test_fee_objection(self):
        self.assertEqual(
            self.mgr.detect_objection("The fees are too high and expensive for my budget"),
            "fee_expensive"
        )
        self.assertEqual(
            self.mgr.detect_objection("ఫీజు చాలా ఎక్కువండి కట్టడం కష్టం"),
            "fee_expensive"
        )
        self.assertEqual(
            self.mgr.detect_objection("फीस बहुत ज्यादा है क्या कोई डिस्काउंट है"),
            "fee_expensive"
        )

    def test_parent_consultation_objection(self):
        self.assertEqual(
            self.mgr.detect_objection("I need to discuss with my father and parents first"),
            "parent_consultation"
        )
        self.assertEqual(
            self.mgr.detect_objection("నేను మా పేరెంట్స్ తో మాట్లాడాలి"),
            "parent_consultation"
        )
        self.assertEqual(
            self.mgr.detect_objection("मुझे अपने माता-पिता से बात करनी पड़ेगी"),
            "parent_consultation"
        )

    def test_exam_waiting_objection(self):
        self.assertEqual(
            self.mgr.detect_objection("I am waiting for EAPCET and JEE counseling results"),
            "waiting_for_exams"
        )
        self.assertEqual(
            self.mgr.detect_objection("ఈఏపీసెట్ ఫలితాల కోసం చూస్తున్నాను"),
            "waiting_for_exams"
        )

    def test_hostel_safety_objection(self):
        self.assertEqual(
            self.mgr.detect_objection("What about hostel safety and mess food quality?"),
            "hostel_safety"
        )
        self.assertEqual(
            self.mgr.detect_objection("హాస్టల్ లో భద్రత మరియు భోజనం ఎలా ఉంటుంది?"),
            "hostel_safety"
        )


class TestGoodbyeGuardAgainstConversionAffirmations(unittest.TestCase):
    """Ensure conversion affirmations with words like 'done' or 'ready' are NEVER falsely ended as goodbyes."""

    def setUp(self):
        self.mgr = LongConversationManager(call_id="goodbye_guard_test")

    def test_conversion_affirmation_not_goodbye(self):
        # "done" alone without farewell should NOT be goodbye if conversion intent is present
        self.assertFalse(self.mgr.is_goodbye("Done! Send me the application link please"))
        self.assertFalse(self.mgr.is_goodbye("Done, register me for Saturday campus visit"))
        self.assertFalse(self.mgr.is_goodbye("Please register me for ASAT"))

    def test_conversion_with_explicit_farewell_is_goodbye(self):
        # If student says "Register me please. Thank you!", that is a legitimate closing turn
        self.assertTrue(self.mgr.is_goodbye("Yes! Register me please. Thank you!"))
        self.assertTrue(self.mgr.is_goodbye("Done, send the link. Thanks and bye!"))
        self.assertTrue(self.mgr.is_goodbye("లింక్ పంపండి, చాలా థాంక్స్ అండి బై"))


class TestFastPathPatternRouterConversion(unittest.TestCase):
    """Test PatternRouter conversion responses (<200ms latency path)."""

    def test_fast_path_application_link(self):
        collected = {"student_name": "Siddharth"}
        resp = PatternRouter.route("Send me the application link on WhatsApp please", collected, lang="en-IN")
        self.assertIsNotNone(resp)
        self.assertIn("provisional application link", resp.lower())
        self.assertEqual(collected.get("engagement_choice"), "application_link")
        self.assertEqual(collected.get("call_outcome"), "interested")

    def test_fast_path_saturday_campus_visit(self):
        collected = {"student_name": "Rohit"}
        resp = PatternRouter.route("I want to visit the campus this Saturday", collected, lang="en-IN")
        self.assertIsNotNone(resp)
        self.assertIn("saturday", resp.lower())
        self.assertIn("10 am", resp.lower())
        self.assertEqual(collected.get("engagement_choice"), "campus_visit")
        self.assertEqual(collected.get("visit_datetime"), "Saturday 10:00 AM")

    def test_fast_path_asat_registration(self):
        collected = {"student_name": "Divya"}
        resp = PatternRouter.route("Please register me for the ASAT scholarship test", collected, lang="en-IN")
        self.assertIsNotNone(resp)
        self.assertIn("asat scholarship test", resp.lower())
        self.assertEqual(collected.get("willing_university_exam"), "yes")
        self.assertEqual(collected.get("engagement_choice"), "asat_registration")

    def test_fast_path_fee_objection(self):
        collected = {"student_name": "Karthik"}
        resp = PatternRouter.route("The fees are high and expensive", collected, lang="en-IN")
        self.assertIsNotNone(resp)
        self.assertIn("scholarship", resp.lower())
        self.assertIn("0% interest", resp.lower())

    def test_fast_path_parent_objection(self):
        collected = {"student_name": "Ananya"}
        resp = PatternRouter.route("I have to discuss with my parents first", collected, lang="en-IN")
        self.assertIsNotNone(resp)
        self.assertIn("campus visit this saturday", resp.lower())


class TestEndToEndAdmissionConversionSimulation(unittest.TestCase):
    """Simulate a realistic 5-turn student conversation leading to a locked admission lead."""

    def test_five_turn_conversion_flow(self):
        manager = LongConversationManager(call_id="sim_conv_5turn")

        # Turn 1: Student introduces name
        t1_user = "Hello, my name is Sneha"
        t1_out = manager.handle_user_input(t1_user)
        self.assertEqual(manager.fact_memory.get_fact("name"), "Sneha")
        agent_t1 = "Hello Sneha! Which program are you interested in at Aditya University?"
        manager.record_turn(t1_user, agent_t1, topic="program")

        # Turn 2: Program and score
        t2_user = "I got 88% in 12th Board and want B.Tech CSE"
        t2_out = manager.handle_user_input(t2_user)
        self.assertEqual(manager.fact_memory.get_fact("program"), "B.Tech CSE")
        self.assertEqual(manager.fact_memory.get_fact("score"), "88%")
        agent_t2 = "Great choice Sneha! With 88%, you qualify for a 30% merit scholarship. Annual fee is ₹87,500."
        manager.record_turn(t2_user, agent_t2, topic="scholarship")

        # Turn 3: Student raises fee concern
        t3_user = "Is there any additional discount? Fees are a bit expensive for us."
        self.assertEqual(manager.detect_objection(t3_user), "fee_expensive")
        agent_t3 = "With ASAT you can upgrade to 50% waiver, and we have 0% interest SBI loan tie-ups. Shall I send the application link or book a Saturday campus tour?"
        manager.record_turn(t3_user, agent_t3, topic="fees")

        # Turn 4: Student accepts CTA (buying signal!)
        t4_user = "That sounds great! Please send me the application link on WhatsApp."
        self.assertEqual(manager.detect_conversion_intent(t4_user), "send_application_link")
        self.assertFalse(manager.is_goodbye(t4_user))
        agent_t4 = "Done Sneha! I've sent the direct priority provisional link to your WhatsApp. Lock your seat today!"
        manager.record_turn(t4_user, agent_t4, topic="application_link")

        # Turn 5: Student confirms and concludes
        t5_user = "Thank you so much Priya, will fill it today! Bye."
        self.assertTrue(manager.is_goodbye(t5_user))
        agent_t5 = "You're most welcome, Sneha! Best of luck for your admissions. Have a wonderful day!"
        manager.record_turn(t5_user, agent_t5, topic="farewell")

        # Audit validation
        summary = manager.get_summary()
        self.assertEqual(summary["turns_count"], 5)
        self.assertEqual(summary["facts"]["name"], "Sneha")
        self.assertEqual(summary["facts"]["program"], "B.Tech CSE")
        self.assertEqual(summary["facts"]["score"], "88%")
        self.assertTrue(manager.conversation_history.has_topic_been_discussed("application_link"))
        # Verify zero repetition
        self.assertFalse(manager.conversation_history.should_ask_about("scholarship"))
        self.assertFalse(manager.conversation_history.should_ask_about("program"))


if __name__ == "__main__":
    unittest.main()
