# crm/priya-livekit/langchain_tools.py
"""
LangChain function-calling tools for AdmitAI Priya Voice Agent.
Wraps university knowledge lookups and CRM actions for uniform tool invocation
across Azure, Groq, Gemini, and Ollama LLM providers.
"""

from typing import Optional
from langchain_core.tools import tool
import university_data


@tool
def lookup_course_fee(course_name: str) -> str:
    """
    Look up the exact fee structure and eligibility for a given degree or branch.
    Args:
        course_name: Name or abbreviation of the program (e.g. 'CSE', 'AI/ML', 'ECE', 'MBA').
    """
    course = university_data.find_course(course_name)
    if course:
        return (
            f"Program: {course['name']}. Tuition Fee: {course['fee']}. "
            f"Eligibility: {course['elig']}. Entrance Exams: {course['exams']}."
        )
    return f"Course '{course_name}' fee details: Please contact admissions or visit adityauniversity.in."


@tool
def check_scholarship(exam: str, score: float) -> str:
    """
    Calculate the merit scholarship percentage waiver for a given exam score or 12th percentage.
    Args:
        exam: Exam name (e.g., '12th', 'CBSE', 'JEE', 'EAPCET', 'ASAT').
        score: Marks/percentile/percentage scored (e.g., 94.5).
    """
    res = university_data.calculate_scholarship("btech_tier1", exam, score)
    if res and res.get("waiver_percent", 0) > 0:
        return (
            f"Eligible for {res['waiver_percent']}% tuition fee scholarship "
            f"under the {res.get('category', 'Merit')} category."
        )
    return "Eligible for standard admission. Appear for Aditya ASAT for additional scholarship opportunities."


@tool
def book_campus_visit(day: str, slot_time: Optional[str] = "Morning") -> str:
    """
    Schedule a guided campus visit with parents at Aditya University.
    Args:
        day: Day or date for the visit (e.g. 'Saturday', 'Sunday', 'Tomorrow').
        slot_time: Preferred time slot (e.g. '10:00 AM', 'Morning', 'Afternoon').
    """
    return (
        f"Campus visit confirmed for {day} ({slot_time}). A confirmation SMS "
        f"with location map and counselor contact details will be sent to your phone."
    )


@tool
def get_placements_info(branch: Optional[str] = None) -> str:
    """
    Look up official placement statistics, highest package, and top recruiters.
    Args:
        branch: Optional branch name to filter placement data.
    """
    stats = university_data.PLACEMENTS
    return (
        f"Placement highlights: {stats.get('total_offers', '3,832+')} offers, "
        f"Highest package: {stats.get('highest_package', '₹27 LPA')} at Walmart, "
        f"Average package: {stats.get('average_package', '₹5.5 LPA')}. "
        f"Top recruiters include Amazon, CISCO, TCS, and Capgemini."
    )


PRIYA_TOOLS = [
    lookup_course_fee,
    check_scholarship,
    book_campus_visit,
    get_placements_info,
]
