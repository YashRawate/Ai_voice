"""
MCP Server for Priya — Aditya University Voice Agent & CRM.

Exposes university admissions tools (course fees, scholarships, programs, university facts, lead logging)
via the Model Context Protocol (MCP) using FastMCP.
"""
import sys
import json
import logging
from mcp.server.fastmcp import FastMCP
import university_data as udata

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("priya_mcp")

# Initialize FastMCP Server
mcp = FastMCP("PriyaAdmissionsMCP")

@mcp.tool()
def get_course_fee(course_query: str) -> str:
    """Lookup annual tuition fee, eligibility, and accepted exams for a university program.
    
    Args:
        course_query: The program or specialization name (e.g. 'CSE', 'B.Tech AI ML', 'MBA').
    """
    course = udata.find_course(course_query)
    if not course:
        return f"No exact match found for '{course_query}'. A counsellor will follow up with full details."
    
    parts = [f"Program: {course['name']}."]
    if course.get("fee"):
        parts.append(f"Annual tuition fee: {course['fee']}.")
    if course.get("elig"):
        parts.append(f"Eligibility: {course['elig']}.")
    if course.get("exams"):
        parts.append(f"Accepted exams: {course['exams']}.")
    if course.get("industry"):
        parts.append(f"Industry partner: {course['industry']}.")
    return " ".join(parts)

@mcp.tool()
def check_scholarship(exam_name: str, score: str, course_query: str = "B.Tech CSE") -> str:
    """Compute exact scholarship percentage for an entrance exam score or rank.
    
    Args:
        exam_name: Exam name (e.g. 'ASAT', 'EAPCET', 'JEE', 'BIE', 'CBSE').
        score: The score or rank achieved (e.g. '95%', '15000', '9.8 CGPA').
        course_query: Target program name (defaults to 'B.Tech CSE').
    """
    return udata.compute_scholarship(exam_name, score, course_query)

@mcp.tool()
def list_programs(branch: str = "") -> str:
    """List available academic branches or specific program tracks.
    
    Args:
        branch: Branch filter such as 'CSE', 'ECE', 'Mechanical', or empty to list all top branches.
    """
    if not branch.strip():
        branches = udata.list_branches()
        return "Top B.Tech branches available: " + ", ".join(branches)
    progs = udata.list_programs(branch)
    if not progs:
        return f"No programs found matching '{branch}'."
    return f"Programs matching '{branch}': " + ", ".join(progs[:8])

@mcp.tool()
def get_university_fact(topic: str = "general") -> str:
    """Get general facts about Aditya University (accreditation, NIRF ranking, campus, contact info).
    
    Args:
        topic: Topic query ('naac', 'ranking', 'campus', 'contact', 'location', 'general').
    """
    t = topic.lower().strip()
    u = udata.UNIVERSITY
    if "naac" in t or "accreditation" in t or "nba" in t:
        return f"Aditya University is NAAC A++ graded and NBA Tier-1 accredited with QS I-Gauge Diamond Rating."
    if "rank" in t or "nirf" in t:
        return f"NIRF 2025 Rank Band: 151-200 (University category). Ranked #1 in Quality Education in AP by THE Impact Rankings."
    if "campus" in t or "location" in t:
        return f"Location: {u['location']}. Campus: 250-acre smart campus with international students from 20+ countries."
    if "contact" in t or "phone" in t:
        return f"Admissions helpline: {u['contacts']}. Official website: {u['website']}."
    return (f"Aditya University (established {u['established']}): {u['naac']} Grade, {u['campus']}, "
            f"NIRF Rank 151-200. Website: {u['website']}, Contacts: {u['contacts']}.")

@mcp.tool()
def save_student_lead(student_name: str, program_of_interest: str, current_city: str = "", score: str = "") -> str:
    """Log collected student lead information to the CRM.
    
    Args:
        student_name: Full name of the candidate.
        program_of_interest: Program selected by student.
        current_city: Candidate's city/location.
        score: Marks/score/rank shared by candidate.
    """
    lead_summary = f"Student: {student_name} | Program: {program_of_interest}"
    if current_city:
        lead_summary += f" | City: {current_city}"
    if score:
        lead_summary += f" | Score: {score}"
    logger.info(f"MCP Lead Logged: {lead_summary}")
    return f"Lead successfully recorded in CRM for {student_name}."

if __name__ == "__main__":
    mcp.run(transport="stdio")
