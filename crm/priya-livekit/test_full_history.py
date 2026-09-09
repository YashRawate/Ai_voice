# test_full_history.py
"""
Unit and Integration Test Suite for Full Conversation History + Flexible Dialogue System.
Verifies:
1. Complete conversation memory across 20+ turns without context loss
2. Automatic extraction of voluntary user facts (name, program, score, exam, city)
3. Zero question repetition across all turns
4. Graceful refusal / postponement handling
5. Flexible questioning logic & fact-based summary generation
6. Full call transcript generation & export
"""

import sys
import os
import io

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from conversation_history import ConversationHistory
from question_engine import QuestionEngine
from llm_with_history import LLMWithHistory
from no_repetition import NoRepetitionEngine


def test_fact_extraction():
    print("\n--- Testing Fact Extraction from Voluntary User Input ---")
    hist = ConversationHistory("test_call_1")

    # Turn 1: User volunteers name, program, and score in one turn
    facts = hist.extract_facts("Hi, my name is Karthik. I want CSE and got 92% in 12th board.")
    assert hist.has_fact("name"), "Failed to extract name"
    assert hist.get_fact("name") == "Karthik"
    assert hist.has_fact("program"), "Failed to extract program"
    assert hist.get_fact("program") == "CSE"
    assert hist.has_fact("score"), "Failed to extract score"
    assert hist.get_fact("score") == "92%"
    print("  PASS: Extracted name (Karthik), program (CSE), score (92%) from single utterance")

    # Turn 2: User mentions entrance exam and city
    hist.extract_facts("I also took JEE and I am from Rajahmundry")
    assert hist.has_fact("exam")
    assert "JEE" in hist.get_fact("exam")
    assert hist.has_fact("city")
    assert hist.get_fact("city") == "Rajahmundry"
    print("  PASS: Extracted entrance exam (JEE) and city (Rajahmundry)")

    # Turn 3: User mentions hostel interest
    hist.extract_facts("Do you have hostel accommodation?")
    assert hist.user_preferences.get("interested_in") == "hostel"
    assert hist.has_fact("hostel_interest")
    print("  PASS: Extracted user preference for hostel accommodation")


def test_no_repetition_logic():
    print("\n--- Testing No Repetition Engine ---")
    hist = ConversationHistory("test_call_2")
    engine = NoRepetitionEngine(hist)

    # Initially all questions can be asked
    assert not engine.should_skip_question("q_program")
    assert not engine.should_skip_question("q_score")

    # User volunteers program
    hist.extract_facts("I am looking for B.Tech CSE")
    assert engine.should_skip_question("q_program"), "Program question should be skipped since fact is known"
    print("  PASS: Program question skipped automatically because user volunteered CSE")

    # Agent asks for 12th score
    hist.record_question_asked("q_score")
    assert engine.should_skip_question("q_score"), "Score question should be skipped since already asked"
    print("  PASS: Score question skipped because it was already asked")


def test_refusal_and_postponement():
    print("\n--- Testing Refusal & Postponement Handling ---")
    hist = ConversationHistory("test_call_3")
    engine = NoRepetitionEngine(hist)

    # User refuses / defers score
    hist.extract_facts("I don't know score yet, results are awaited")
    assert hist.is_refused("q_score")
    assert hist.is_refused("score")
    assert engine.should_skip_question("q_score")
    print("  PASS: Score refusal detected ('don't know score yet') -> question skipped")

    # User has no entrance exam
    hist.extract_facts("I haven't taken any entrance exam")
    assert hist.is_refused("q_exam")
    assert engine.should_skip_question("q_exam")
    print("  PASS: Exam refusal detected ('haven't taken any entrance exam') -> question skipped")


def test_long_call_continuity_20_plus_turns():
    print("\n--- Testing Long Call Memory (20+ Turns Without Truncation) ---")
    hist = ConversationHistory("test_call_long")

    # Populate 22 turns
    for i in range(1, 23):
        u_msg = f"User statement on turn {i}"
        a_msg = f"Agent response on turn {i}"
        if i == 1:
            u_msg = "Hello, my name is Priya Sharma and I am interested in AI/ML"
        elif i == 5:
            u_msg = "I scored 94% in my intermediate exams"
        elif i == 12:
            u_msg = "What about hostel facilities and bus routes?"
        elif i == 20:
            u_msg = "Can my parents visit the campus this weekend?"

        hist.add_turn(u_msg, a_msg, latency=0.4, language="en-IN")

    assert len(hist.turns) == 22, f"Expected 22 turns, got {len(hist.turns)}"
    # Verify Turn 1 fact is still remembered on Turn 22!
    assert hist.get_fact("name") == "Priya"
    assert hist.get_fact("program") == "AI/ML"
    assert hist.get_fact("score") == "94%"
    print("  PASS: 22 turns recorded without loss; Turn 1 facts fully retained on Turn 22")

    context_str = hist.get_context()
    assert "Turn 1 (en-IN):" in context_str
    assert "Turn 22 (en-IN):" in context_str
    assert "FACTS EXTRACTED FROM CALLER" in context_str
    print("  PASS: get_context() correctly formats complete 22-turn history")


def test_question_engine_flexible_guidance():
    print("\n--- Testing Question Engine Guidance & Fact Summaries ---")
    hist = ConversationHistory("test_call_qe")
    qe = QuestionEngine(hist)

    # Initial state: should suggest program
    q1 = qe.get_next_question()
    assert "program" in q1.lower() or "branch" in q1.lower()
    print(f"  PASS: Initial question guidance: '{q1}'")

    # User provides program
    hist.extract_facts("I want Mechanical Engineering")
    q2 = qe.get_next_question()
    assert "score" in q2.lower() or "12th" in q2.lower()
    print(f"  PASS: After program known, suggests score: '{q2}'")

    # User provides score
    hist.extract_facts("My 12th score is 91%")
    summary = qe.get_response_based_on_facts()
    assert "Mechanical" in summary
    assert "91%" in summary
    assert "Scholarship" in summary
    print("  PASS: Fact-based summary computed accurately:\n" + "\n".join("    " + l for l in summary.splitlines()))


def test_full_call_transcript_generation():
    print("\n--- Testing Transcript Generation & Export ---")
    hist = ConversationHistory("test_call_transcript")
    hist.add_turn("Hi, I want CSE", "Great! CSE is our top program.", latency=0.3, language="en-IN")
    hist.add_turn("I scored 92% in 12th", "With 92%, you qualify for a 50% scholarship!", latency=0.4, language="en-IN")
    hist.add_turn("Thank you, that's all", "Thank you for contacting Aditya University! Have a great day!", latency=0.2, language="en-IN")

    transcript = hist.get_full_transcript()
    assert "COMPLETE CALL TRANSCRIPT (test_call_transcript)" in transcript
    assert "Turn 1" in transcript
    assert "Turn 2" in transcript
    assert "Turn 3" in transcript
    assert "CALL SUMMARY:" in transcript
    assert "Total Duration:" in transcript

    # Test file write
    os.makedirs("transcripts", exist_ok=True)
    out_file = "transcripts/test_call_transcript.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(transcript)
    assert os.path.exists(out_file)
    print("  PASS: Full call transcript generated and exported to disk")


def main():
    print("=" * 60)
    print("RUNNING FULL CONVERSATION HISTORY & FLEXIBLE DIALOGUE TESTS")
    print("=" * 60)

    test_fact_extraction()
    test_no_repetition_logic()
    test_refusal_and_postponement()
    test_long_call_continuity_20_plus_turns()
    test_question_engine_flexible_guidance()
    test_full_call_transcript_generation()

    print("\n" + "=" * 60)
    print("ALL FULL CONVERSATION HISTORY TESTS PASSED (100% SUCCESS)!")
    print("=" * 60)


if __name__ == "__main__":
    main()
