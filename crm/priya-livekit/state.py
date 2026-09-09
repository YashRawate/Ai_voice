# crm/priya-livekit/state.py
"""
CallState definition for AdmitAI Priya LangChain & LangGraph pipeline.
Single canonical state object per call session, keyed strictly by session_id.
"""

from typing import TypedDict, Optional, Literal, List, Dict, Any
from langchain_core.messages import BaseMessage


class CallState(TypedDict):
    session_id: str
    customer_id: Optional[str]

    # Conversation history — LangGraph/LangChain managed, never wiped by language changes
    messages: List[BaseMessage]

    # Facts ledger — language switches must NEVER touch or reset this
    facts: Dict[str, Any]  # e.g. {"student_name": "Rahul", "program": "B.Tech CSE", ...}

    # Flow control — computed server-side
    stage: Literal["GREETING", "PROGRAM", "ELIGIBILITY", "CONSULT", "CONVERT"]
    next_field: Optional[str]

    # Language — the ONLY field that language switches update
    language_code: str  # "en-IN" | "hi-IN" | "te-IN" | "ta-IN"

    # Per-turn metadata
    last_user_text: str
    current_intent: Optional[str]
    is_followup_call: bool
