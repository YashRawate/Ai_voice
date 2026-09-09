# crm/priya-livekit/graph.py
"""
LangGraph StateGraph for AdmitAI Priya Voice Agent.
Coordinates language detection, slot extraction, stage routing, and response generation.
"""

from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

from state import CallState
from prompts import build_prompt_template, LANGUAGE_STYLE
from language_handler import LanguageHandler
from checkpointer import get_checkpointer
from langchain_tools import PRIYA_TOOLS
from llm_failover import build_langchain_llm


prompt_template = build_prompt_template()


def detect_language(state: CallState) -> Dict[str, Any]:
    """
    Detect language of the caller without modifying facts or history.
    """
    text = state.get("last_user_text", "")
    curr = state.get("language_code", "en-IN")
    matched_code = LanguageHandler.match_language(
        transcript_text=text,
        current_language=curr
    )
    return {"language_code": matched_code}


def extract_slots(state: CallState) -> Dict[str, Any]:
    """
    Additive slot extraction into facts ledger.
    Never overwrites known facts with empty values.
    """
    text = state.get("last_user_text", "")
    existing_facts = dict(state.get("facts", {}))

    import re
    t_low = text.lower()

    # Extract name if not known
    if "student_name" not in existing_facts:
        m_name = re.search(r'\b(?:my name is|i am|this is|name is|peru|naam)\s+([A-Za-z]+)', text, re.I)
        if m_name:
            cand = m_name.group(1).title()
            if cand.lower() not in {"interested", "calling", "speaking", "here", "fine"}:
                existing_facts["student_name"] = cand

    # Extract program with strict word boundaries
    if re.search(r'\b(cse|computer science|ai/ml|data science|ece|eee|mech|civil|mba|bba|pharmacy)\b', t_low) or re.search(r'\b(ai|ml)\b', t_low):
        if re.search(r'\b(cse|computer science)\b', t_low):
            existing_facts["program"] = "B.Tech CSE"
        elif re.search(r'\b(ai|ml|data science|ai/ml)\b', t_low):
            existing_facts["program"] = "B.Tech AI/ML"
        elif re.search(r'\b(ece)\b', t_low):
            existing_facts["program"] = "B.Tech ECE"
        elif re.search(r'\b(mba)\b', t_low):
            existing_facts["program"] = "MBA"
        elif re.search(r'\b(pharmacy)\b', t_low):
            existing_facts["program"] = "Pharmacy"
        elif re.search(r'\b(bba)\b', t_low):
            existing_facts["program"] = "BBA"
        elif "program" not in existing_facts:
            existing_facts["program"] = "B.Tech"

    # Extract 12th score
    m_score = re.search(r'(\d{2}(?:\.\d+)?)\s*%', text)
    if m_score:
        existing_facts["marks_12"] = f"{m_score.group(1)}%"

    # Extract entrance exam
    if re.search(r'\b(jee|jee main|jee mains)\b', t_low):
        existing_facts["entrance_exam"] = "JEE Main"
    elif re.search(r'\b(eamcet|eapcet|ap eamcet|ap eapcet)\b', t_low):
        existing_facts["entrance_exam"] = "AP EAPCET"
    elif re.search(r'\b(asat)\b', t_low):
        existing_facts["entrance_exam"] = "ASAT"

    return {"facts": existing_facts}


def route_stage(state: CallState) -> Dict[str, Any]:
    """
    Compute current conversation stage and next field to collect.
    """
    facts = state.get("facts", {})

    if "student_name" not in facts:
        return {"stage": "GREETING", "next_field": "student_name"}
    elif "program" not in facts:
        return {"stage": "PROGRAM", "next_field": "program"}
    elif "marks_12" not in facts:
        return {"stage": "ELIGIBILITY", "next_field": "marks_12"}
    elif "entrance_exam" not in facts:
        return {"stage": "ELIGIBILITY", "next_field": "entrance_exam"}
    else:
        return {"stage": "CONVERT", "next_field": "campus_visit"}


def create_reply_generator(llm: Optional[Any] = None):
    """Creates generate_reply node function with injected LLM or fast fallback."""

    def generate_reply(state: CallState) -> Dict[str, Any]:
        facts = state.get("facts", {})
        facts_str = "\n".join(f"• {k}: {v}" for k, v in facts.items()) if facts else "(none yet)"
        lang_code = state.get("language_code", "en-IN")
        style_instruction = LANGUAGE_STYLE.get(lang_code, LANGUAGE_STYLE["en-IN"])
        messages = list(state.get("messages", []))

        user_text = state.get("last_user_text", "")
        if user_text:
            messages.append(HumanMessage(content=user_text))

        formatted_messages = prompt_template.format_messages(
            facts=facts_str,
            stage=state.get("stage", "GREETING"),
            next_field=state.get("next_field") or "(all required fields collected)",
            language_style=style_instruction,
            messages=messages[:-1] if messages else [],
        )

        reply_content = ""
        if llm is not None:
            try:
                ai_resp = llm.invoke(formatted_messages)
                reply_content = getattr(ai_resp, "content", str(ai_resp))
            except Exception:
                pass

        if not reply_content:
            u_low = user_text.lower()
            if "fee" in u_low or "fees" in u_low:
                if lang_code == "hi-IN":
                    reply_content = "B.Tech CSE की ट्यूशन फीस ₹2,75,000 प्रति वर्ष है और 50% तक मेरिट स्कॉलरशिप उपलब्ध है।"
                elif lang_code == "te-IN":
                    reply_content = "B.Tech CSE ట్యూషన్ ఫీజు సంవత్సరానికి ₹2,75,000 మరియు 50% వరకు స్కాలర్‌షిప్ ఉంది."
                else:
                    reply_content = "The B.Tech CSE tuition fee is ₹2,75,000 per year with up to 50% merit scholarships available."
            elif "hostel" in u_low:
                if lang_code == "te-IN":
                    reply_content = "మా దగ్గర AC మరియు Non-AC హాస్టల్స్ ఉన్నాయి. వార్షిక ఫీజు ₹1,15,000 నుండి మొదలవుతుంది."
                elif lang_code == "hi-IN":
                    reply_content = "हमारे पास AC और Non-AC हॉस्टल उपलब्ध हैं। क्या आप हॉस्टल देखना चाहेंगे?"
                else:
                    reply_content = "We provide AC and Non-AC hostels with multi-cuisine dining on campus."
            elif "visit" in u_low or "saturday" in u_low:
                if lang_code == "hi-IN":
                    reply_content = "बहुत बढ़िया! हमने शनिवार के लिए आपका कैंपस विजिट स्लॉट बुक कर दिया है।"
                elif lang_code == "te-IN":
                    reply_content = "చాలా మంచిది! శనివారం క్యాంపస్ విజిట్ కన్ఫర్మ్ చేసాము."
                else:
                    reply_content = "Wonderful! I have scheduled your campus visit for this Saturday."
            else:
                next_field = state.get("next_field", "")
                if next_field == "student_name":
                    reply_content = "Hello! This is Priya from Aditya University. May I know your good name, please?"
                elif next_field == "program":
                    name = facts.get("student_name", "")
                    reply_content = f"Nice to connect with you, {name}! Which program or branch are you interested in?" if name else "Which course or branch are you interested in?"
                elif next_field == "marks_12":
                    reply_content = "What was your 12th Board or Intermediate percentage?"
                elif next_field == "entrance_exam":
                    reply_content = "Have you appeared for JEE Main, AP EAPCET, or our ASAT scholarship exam?"
                else:
                    reply_content = "Would you like to book a guided campus tour with your parents this Saturday?"

        ai_message = AIMessage(content=reply_content)
        return {"messages": messages + [ai_message]}

    return generate_reply


# ── Build StateGraph ─────────────────────────────────────────────────────────

def build_call_graph(llm: Optional[Any] = None, checkpointer: Optional[Any] = None):
    """Build and compile the CallState StateGraph."""
    workflow = StateGraph(CallState)

    workflow.add_node("detect_language", detect_language)
    workflow.add_node("extract_slots", extract_slots)
    workflow.add_node("route_stage", route_stage)
    workflow.add_node("generate_reply", create_reply_generator(llm))

    workflow.set_entry_point("detect_language")
    workflow.add_edge("detect_language", "extract_slots")
    workflow.add_edge("extract_slots", "route_stage")
    workflow.add_edge("route_stage", "generate_reply")
    workflow.add_edge("generate_reply", END)

    cp = checkpointer if checkpointer is not None else get_checkpointer()
    return workflow.compile(checkpointer=cp)
