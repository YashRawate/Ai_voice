# test_dialogue_slots.py
"""
Comprehensive test suite for DialogueSlotManager, Scholarship Calculation,
and Session Management integration in Priya Voice Agent.
"""

import sys
import io

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from session_manager import DialogueSlotManager, SessionContext, GLOBAL_SESSION_STORE
import university_data as udata
from agent import PatternRouter


def test_name_extraction():
    print("\n--- Testing Name Extraction ---")
    slots = {}
    slots = DialogueSlotManager.extract_slots("My name is Karthik", slots)
    assert slots.get("student_name") == "Karthik", f"Expected Karthik, got {slots.get('student_name')}"
    print("  PASS: 'My name is Karthik' -> Karthik")

    slots2 = {}
    slots2 = DialogueSlotManager.extract_slots("I am Ramesh and I want admission", slots2)
    assert slots2.get("student_name") == "Ramesh", f"Expected Ramesh, got {slots2.get('student_name')}"
    print("  PASS: 'I am Ramesh' -> Ramesh")

    # Invalid names / conversational fillers should be rejected
    slots3 = {}
    slots3 = DialogueSlotManager.extract_slots("I am interested in CSE", slots3)
    assert slots3.get("student_name") is None, f"Should reject 'interested', got {slots3.get('student_name')}"
    print("  PASS: Filtered invalid name candidate 'interested'")


def test_score_extraction():
    print("\n--- Testing Score Extraction ---")
    slots = {}
    slots = DialogueSlotManager.extract_slots("I got 92 percent in 12th board", slots)
    assert slots.get("class_12_score") == "92.0%", f"Expected 92.0%, got {slots.get('class_12_score')}"
    print("  PASS: '92 percent' -> 92.0%")

    slots2 = {}
    slots2 = DialogueSlotManager.extract_slots("My 12th marks are 95.5%", slots2)
    assert slots2.get("class_12_score") == "95.5%", f"Expected 95.5%, got {slots2.get('class_12_score')}"
    print("  PASS: '95.5%' -> 95.5%")

    slots3 = {}
    slots3 = DialogueSlotManager.extract_slots("I scored 88 in intermediate", slots3)
    assert slots3.get("class_12_score") == "88.0%", f"Expected 88.0%, got {slots3.get('class_12_score')}"
    print("  PASS: 'scored 88' -> 88.0%")


def test_exam_extraction():
    print("\n--- Testing Exam Extraction ---")
    slots = {}
    slots = DialogueSlotManager.extract_slots("I wrote JEE Mains and AP EAMCET", slots)
    exams = slots.get("entrance_exams_taken", "")
    assert "JEE" in exams, f"Expected JEE in {exams}"
    assert "AP_EAPCET" in exams, f"Expected AP_EAPCET in {exams}"
    print(f"  PASS: 'JEE Mains and AP EAMCET' -> {exams}")

    slots = DialogueSlotManager.extract_slots("I am also attempting ASAT", slots)
    exams = slots.get("entrance_exams_taken", "")
    assert "ASAT" in exams, f"Expected ASAT in {exams}"
    print(f"  PASS: Accumulated ASAT -> {exams}")


def test_program_extraction():
    print("\n--- Testing Program Extraction ---")
    slots = {}
    slots = DialogueSlotManager.extract_slots("I want to apply for B.Tech Computer Science", slots)
    assert slots.get("program_of_interest") == "B.Tech CSE", f"Expected B.Tech CSE, got {slots.get('program_of_interest')}"
    print("  PASS: 'Computer Science' -> B.Tech CSE")

    slots2 = {}
    slots2 = DialogueSlotManager.extract_slots("Tell me about Artificial Intelligence and Data Science", slots2)
    assert slots2.get("program_of_interest") in ["B.Tech AI/ML", "B.Tech CSE (Data Science)"]
    print(f"  PASS: 'AI and Data Science' -> {slots2.get('program_of_interest')}")


def test_city_extraction():
    print("\n--- Testing City Extraction ---")
    slots = {}
    slots = DialogueSlotManager.extract_slots("I am from Rajahmundry", slots)
    assert slots.get("current_city") == "Rajahmundry", f"Expected Rajahmundry, got {slots.get('current_city')}"
    print("  PASS: 'from Rajahmundry' -> Rajahmundry")

    slots2 = {}
    slots2 = DialogueSlotManager.extract_slots("Nenu Hyderabad lo untunnanu", slots2)
    assert slots2.get("current_city") == "Hyderabad", f"Expected Hyderabad, got {slots2.get('current_city')}"
    print("  PASS: 'Hyderabad lo untunnanu' -> Hyderabad")


def test_scholarship_calculation():
    print("\n--- Testing Scholarship Calculations ---")
    # Tier 1: 95%+ -> 75%
    res95 = udata.calculate_scholarship("B.Tech CSE", "96%")
    assert res95["waiver_percentage"] == 75, f"Expected 75%, got {res95['waiver_percentage']}"
    assert res95["final_annual_fee"] == 31250, f"Expected 31250, got {res95['final_annual_fee']}"
    print(f"  PASS: 96% score -> 75% waiver, fee: ₹{res95['final_annual_fee']:,}")

    # Tier 2: 90-95% -> 50% (Week 1 canonical test case)
    res92 = udata.calculate_scholarship("B.Tech CSE", "92%")
    assert res92["waiver_percentage"] == 50, f"Expected 50%, got {res92['waiver_percentage']}"
    assert res92["final_annual_fee"] == 62500, f"Expected 62500, got {res92['final_annual_fee']}"
    print(f"  PASS: 92% score -> 50% waiver, fee: ₹{res92['final_annual_fee']:,}")

    # Tier 3: 80-90% -> 25%
    res85 = udata.calculate_scholarship("B.Tech CSE", "85%")
    assert res85["waiver_percentage"] == 25, f"Expected 25%, got {res85['waiver_percentage']}"
    assert res85["final_annual_fee"] == 93750, f"Expected 93750, got {res85['final_annual_fee']}"
    print(f"  PASS: 85% score -> 25% waiver, fee: ₹{res85['final_annual_fee']:,}")

    # Tier 4: 70-80% -> 15%
    res75 = udata.calculate_scholarship("B.Tech CSE", "75%")
    assert res75["waiver_percentage"] == 15, f"Expected 15%, got {res75['waiver_percentage']}"
    assert res75["final_annual_fee"] == 106250, f"Expected 106250, got {res75['final_annual_fee']}"
    print(f"  PASS: 75% score -> 15% waiver, fee: ₹{res75['final_annual_fee']:,}")

    # Non-qualifying: <70%
    res65 = udata.calculate_scholarship("B.Tech CSE", "65%")
    assert res65["waiver_percentage"] == 0
    assert not res65["qualifies"]
    print("  PASS: 65% score -> No scholarship waiver")


def test_personalized_pattern_router():
    print("\n--- Testing PatternRouter Personalized Scholarship ---")
    collected = {
        "student_name": "Karthik",
        "class_12_score": "92%",
        "program_of_interest": "B.Tech CSE"
    }
    
    # English query with pre-collected score
    resp_en = PatternRouter._scholarship("Can I get a scholarship?", collected, lang="en-IN")
    assert resp_en is not None
    assert "50%" in resp_en
    assert "62,500" in resp_en
    print(f"  PASS (EN): {resp_en}")

    # Telugu query
    resp_te = PatternRouter._scholarship("స్కాలర్‌షిప్ వస్తుందా?", collected, lang="te-IN")
    assert resp_te is not None
    assert "50%" in resp_te
    assert "62,500" in resp_te
    print(f"  PASS (TE): {resp_te}")

    # Hindi query
    resp_hi = PatternRouter._scholarship("स्कॉलरशिप कितनी मिलेगी?", collected, lang="hi-IN")
    assert resp_hi is not None
    assert "50%" in resp_hi
    assert "62,500" in resp_hi
    print(f"  PASS (HI): {resp_hi}")


def test_full_session_flow():
    print("\n--- Testing Multi-Turn Session Extraction Flow ---")
    ctx = SessionContext("test_session_101")
    
    # Turn 1: Caller introduces name and score
    t1_text = "Hi, my name is Karthik and I got 92 percent in 12th"
    ctx.collected = DialogueSlotManager.extract_slots(t1_text, ctx.collected)
    ctx.add_turn("user", t1_text)
    
    assert ctx.collected.get("student_name") == "Karthik"
    assert ctx.collected.get("class_12_score") == "92.0%"
    assert ctx.is_question_redundant("student_name")
    print(f"  Turn 1 Result: {ctx.collected}")

    # Turn 2: Caller states exam and program
    t2_text = "I am preparing for JEE and want to do CSE"
    ctx.collected = DialogueSlotManager.extract_slots(t2_text, ctx.collected)
    ctx.add_turn("user", t2_text)
    
    assert "JEE" in ctx.collected.get("entrance_exams_taken", "")
    assert ctx.collected.get("program_of_interest") == "B.Tech CSE"
    assert ctx.is_question_redundant("program_interest")
    assert ctx.is_question_redundant("entrance_exam")
    print(f"  Turn 2 Result: {ctx.collected}")

    # Turn 3: Caller mentions city
    t3_text = "I live in Rajahmundry"
    ctx.collected = DialogueSlotManager.extract_slots(t3_text, ctx.collected)
    ctx.add_turn("user", t3_text)
    
    assert ctx.collected.get("current_city") == "Rajahmundry"
    print(f"  Turn 3 Result: {ctx.collected}")

    # Turn 4: Caller asks for fees/scholarship
    calc = udata.calculate_scholarship(ctx.collected["program_of_interest"], ctx.collected["class_12_score"])
    assert calc["final_annual_fee"] == 62500
    print(f"  Turn 4 Personalized Calculation: 50% waiver applied -> ₹{calc['final_annual_fee']:,}")


def main():
    print("=" * 60)
    print("RUNNING DIALOGUE SLOT MANAGER & SCHOLARSHIP TEST SUITE")
    print("=" * 60)
    
    test_name_extraction()
    test_score_extraction()
    test_exam_extraction()
    test_program_extraction()
    test_city_extraction()
    test_scholarship_calculation()
    test_personalized_pattern_router()
    test_full_session_flow()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED WITH 100% SUCCESS")
    print("=" * 60)


if __name__ == "__main__":
    main()
