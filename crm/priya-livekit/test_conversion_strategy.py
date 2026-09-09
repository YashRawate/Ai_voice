"""
Unit tests for Lead-to-Admission Conversion Strategy.
Verifies all 5 conversion pillars, personalization, objections, commitment funnel, A/B test harness, and prompt directives.
"""

import unittest
from conversion_strategy import (
    PersonalizedConversionStrategy,
    CommitmentFunnel,
    PostCallNurtureTimeline,
    ConversionABTesting,
    conversion_engine,
    ab_tester
)
from long_conversation import LongConversationManager, detect_conversion_intent, detect_objection


class TestConversionStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy = PersonalizedConversionStrategy()

    def test_personalize_by_score(self):
        msg_95 = self.strategy.personalize_by_score(95.0)
        self.assertIn("100%", msg_95)
        self.assertIn("Honors", msg_95)

        msg_85 = self.strategy.personalize_by_score(85.0)
        self.assertIn("50%", msg_85)
        self.assertIn("62,500", msg_85)

        msg_75 = self.strategy.personalize_by_score(75.0)
        self.assertIn("25%", msg_75)

        msg_65 = self.strategy.personalize_by_score(65.0)
        self.assertIn("ASAT", msg_65)

    def test_personalize_by_location(self):
        msg_delhi = self.strategy.personalize_by_location("Delhi")
        self.assertIn("Delhi", msg_delhi)
        self.assertIn("alumni", msg_delhi)

        msg_mumbai = self.strategy.personalize_by_location("Mumbai")
        self.assertIn("Mumbai", msg_mumbai)
        self.assertIn("alumni", msg_mumbai)

    def test_personalize_by_board(self):
        msg_cbse = self.strategy.personalize_by_exam_board("CBSE")
        self.assertIn("CBSE", msg_cbse)

        msg_icse = self.strategy.personalize_by_exam_board("ICSE")
        self.assertIn("ICSE", msg_icse)

        msg_state = self.strategy.personalize_by_exam_board("State Board")
        self.assertIn("State Board", msg_state)

    def test_personalize_by_gender(self):
        msg_female = self.strategy.personalize_by_gender_diversity("female")
        self.assertIn("50-50 gender balance", msg_female)
        self.assertIn("41%", msg_female)

        msg_male = self.strategy.personalize_by_gender_diversity("male")
        self.assertEqual(msg_male, "")

    def test_create_personalized_offer(self):
        profile = {
            "score": 85.0,
            "board": "CBSE",
            "location": "Delhi",
            "preferred_role": "B.Tech CSE"
        }
        offer = self.strategy.create_personalized_offer(profile)
        self.assertEqual(offer["scholarship_percent"], 50)
        self.assertEqual(offer["discounted_annual_fee"], 62500)
        self.assertEqual(offer["annual_savings"], 62500)
        self.assertIn("50% fee waiver", offer["pitch_script"])
        self.assertIn("5,000", offer["soft_close_incentive"])

    def test_scarcity_messaging(self):
        scarcity = self.strategy.get_scarcity_message(program="B.Tech CSE", score=85.0, remaining=20, total=50)
        self.assertIn("Total seats: 50", scarcity)
        self.assertIn("20 seats remain", scarcity)
        self.assertIn("cutoff", scarcity)

    def test_anticipatory_objections(self):
        preempt = self.strategy.get_anticipatory_objections()
        self.assertIn("Fees", preempt)
        self.assertIn("Entrance Exam", preempt)
        self.assertIn("Placements", preempt)

    def test_objection_rebuttals(self):
        fee_reb = self.strategy.get_objection_rebuttal("fee is high")
        self.assertIn("62,500", fee_reb)
        self.assertIn("12L", fee_reb)

        think_reb = self.strategy.get_objection_rebuttal("let me think")
        self.assertIn("virtual campus walk", think_reb)

        compare_reb = self.strategy.get_objection_rebuttal("comparing with VIT")
        self.assertIn("better fit", compare_reb)

    def test_commitment_funnel(self):
        funnel = CommitmentFunnel()
        self.assertEqual(funnel.current_level, 1)
        self.assertIn("WhatsApp", funnel.get_current_action()["action"])

        step2 = funnel.advance()
        self.assertEqual(funnel.current_level, 2)
        self.assertIn("Virtual campus tour", step2["action"])

        step3 = funnel.advance()
        self.assertEqual(funnel.current_level, 3)
        self.assertIn("Submit formal application", step3["action"])

    def test_post_call_nurture_timeline(self):
        timeline = PostCallNurtureTimeline.get_timeline()
        self.assertEqual(len(timeline), 6)
        times = [t["time"] for t in timeline]
        self.assertIn("Minute 0", times)
        self.assertIn("Hour 12", times)
        self.assertIn("Hour 24", times)
        self.assertIn("Hour 48", times)

    def test_ab_testing_harness(self):
        champ_open = ConversionABTesting.get_winning_variant("opening")
        self.assertIn(champ_open["variant"], ["A", "B"])

        champ_sch = ConversionABTesting.get_winning_variant("scholarship")
        self.assertIn(champ_sch["variant"], ["A", "B", "C"])

        ConversionABTesting.record_interaction("opening", "B", converted=True)
        new_stats = ConversionABTesting.VARIANTS["opening"]["B"]
        self.assertGreaterEqual(new_stats["conversions"], 165)

    def test_long_conversation_conversion_detection(self):
        mgr = LongConversationManager("test_conv_call")

        # 1. Direct apply intent
        intent1 = mgr.detect_conversion_intent("I want to apply right now, take down my details")
        self.assertEqual(intent1, "apply_now_direct")

        # 2. Soft commitment intent
        intent2 = mgr.detect_conversion_intent("Can you add me to the student WhatsApp group")
        self.assertEqual(intent2, "soft_commitment")

        # 3. Objection: want to think
        obj1 = mgr.detect_objection("I want to think about it before making a decision")
        self.assertEqual(obj1, "want_to_think")

        # 4. Objection: comparing colleges
        obj2 = mgr.detect_objection("I am comparing with VIT and SRM right now")
        self.assertEqual(obj2, "comparing_colleges")

        # 5. Build turn prompt with directives
        prompt = mgr.build_turn_prompt("I want to think about it")
        self.assertIn("OBJECTION DIRECTIVE", prompt)
        self.assertIn("wants to think", prompt)


if __name__ == "__main__":
    unittest.main()
