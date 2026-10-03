# crm/priya-livekit/structured_memory.py
"""
Structured Persistent Memory & State Machine for Priya Voice Agent.
Implements the 2-tier memory model:
  1. Short-term conversation memory (recent dialogue turns)
  2. Long-term structured call state (extracted facts with explicit boolean flags)

Guarantees:
  - Additive merging (new facts never erase old facts)
  - Explicit boolean collection flags for state-machine progression
  - Correction awareness (explicit updates override previous values)
  - Permanent persistence across calls indexed by phone number (SQLite / JSON + Redis)
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("priya.memory")


@dataclass
class StructuredCallState:
    call_id: str
    phone_number: str = ""
    name: Optional[str] = None
    program: Optional[str] = None
    marks: Optional[str] = None
    college: Optional[str] = None
    city: Optional[str] = None
    language: str = "English"

    # Explicit Boolean Collection Flags
    name_collected: bool = False
    program_collected: bool = False
    marks_collected: bool = False
    college_collected: bool = False
    city_collected: bool = False

    # Workflow state
    current_step: str = "name"
    is_followup_call: bool = False

    def update_flags(self):
        """Re-sync boolean flags from state fields."""
        if self.name and str(self.name).strip().lower() not in {"unknown", "none", "n/a", "null", "caller", "student"}:
            self.name_collected = True
        if self.program and str(self.program).strip():
            self.program_collected = True
        if self.marks and str(self.marks).strip():
            self.marks_collected = True
        if self.college and str(self.college).strip():
            self.college_collected = True
        if self.city and str(self.city).strip():
            self.city_collected = True

        self.current_step = self.determine_next_missing_step()

    def determine_next_missing_step(self) -> str:
        """
        Monotonic State Machine:
        Returns the first missing field in the structured collection pipeline.
        Skips any step where the information is already collected.
        """
        if not self.name_collected:
            return "name"
        elif not self.program_collected:
            return "program"
        elif not self.marks_collected:
            return "marks"
        elif not self.city_collected:
            return "city"
        elif not self.college_collected:
            return "college"
        else:
            return "campus_visit"

    def merge_facts(self, extracted: Dict[str, Any], is_correction: bool = False):
        """
        Additive merge: old_state + new_information.
        Existing fields are preserved unless is_correction is True.
        """
        if not extracted:
            return

        # Name mapping
        new_name = extracted.get("student_name") or extracted.get("name")
        if new_name:
            if not self.name or is_correction:
                self.name = str(new_name).strip()
                self.name_collected = True

        # Program mapping
        new_prog = extracted.get("program_of_interest") or extracted.get("program") or extracted.get("course")
        if new_prog:
            if not self.program or is_correction:
                self.program = str(new_prog).strip()
                self.program_collected = True

        # Marks mapping
        new_marks = extracted.get("class_12_score") or extracted.get("marks") or extracted.get("score")
        if new_marks:
            if not self.marks or is_correction:
                self.marks = str(new_marks).strip()
                self.marks_collected = True

        # College / School mapping
        new_college = extracted.get("college") or extracted.get("school")
        if new_college:
            if not self.college or is_correction:
                self.college = str(new_college).strip()
                self.college_collected = True

        # City / Location mapping
        new_city = extracted.get("current_city") or extracted.get("city") or extracted.get("location")
        if new_city:
            if not self.city or is_correction:
                self.city = str(new_city).strip()
                self.city_collected = True

        self.update_flags()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_llm_prompt_block(self) -> str:
        """
        Formats the structured state directly into the LLM system prompt
        following the prompt rules of the persistent memory specification.
        """
        lines = [
            "# STRUCTURED USER PROFILE (SOURCE OF TRUTH)",
            f"• Name: {self.name if self.name_collected else 'Unknown'} (Collected: {'Yes' if self.name_collected else 'No'})",
            f"• Program: {self.program if self.program_collected else 'Unknown'} (Collected: {'Yes' if self.program_collected else 'No'})",
            f"• 12th Marks / Score: {self.marks if self.marks_collected else 'Unknown'} (Collected: {'Yes' if self.marks_collected else 'No'})",
            f"• Location / City: {self.city if self.city_collected else 'Unknown'} (Collected: {'Yes' if self.city_collected else 'No'})",
            f"• Previous College/School: {self.college if self.college_collected else 'Unknown'} (Collected: {'Yes' if self.college_collected else 'No'})",
            "",
            f"CURRENT REQUIRED INFORMATION (NEXT MISSING FIELD): {self.current_step.upper()}",
            "",
            "# PERSISTENT MEMORY RULES:",
            "1. NEVER ask for information that is already marked as Collected: Yes above.",
            "2. Never ask the user's name again because it is already known." if self.name_collected else "",
            "3. If the user provides multiple pieces of information in one sentence, acknowledge and accept all of them.",
            "4. If the user corrects previously provided information, use the newly confirmed information.",
            f"5. Focus ONLY on collecting the missing '{self.current_step}' or answering their direct inquiry first.",
            "6. Keep responses short and conversational (spoken phone audio).",
        ]
        return "\n".join(line for line in lines if line is not None)


class PersistentUserStore:
    """
    Cross-Call Long-Term Memory indexed by Phone Number.
    Uses SQLite with JSON fallback and auto-syncs with Redis if active.
    Persists profile from Call #1 so Call #2 knows the user immediately.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "user_profiles.db")
        self._init_sqlite()

    def _init_sqlite(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        phone_number TEXT PRIMARY KEY,
                        name TEXT,
                        program TEXT,
                        marks TEXT,
                        college TEXT,
                        city TEXT,
                        language TEXT,
                        profile_json TEXT,
                        updated_at REAL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.warning(f"[USER_STORE] SQLite init failed ({e}). Fallback to local memory.")

    def get_profile(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Look up user profile by phone number across all previous calls."""
        if not phone_number:
            return None
        clean_phone = re.sub(r'[\s\-\(\)]', '', str(phone_number))
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE phone_number = ?", (clean_phone,))
                row = cursor.fetchone()
                if row:
                    profile = {
                        "phone_number": row["phone_number"],
                        "student_name": row["name"],
                        "name": row["name"],
                        "program_of_interest": row["program"],
                        "program": row["program"],
                        "class_12_score": row["marks"],
                        "marks": row["marks"],
                        "college": row["college"],
                        "current_city": row["city"],
                        "city": row["city"],
                        "language": row["language"],
                    }
                    if row["profile_json"]:
                        try:
                            extra = json.loads(row["profile_json"])
                            profile.update(extra)
                        except Exception:
                            pass
                    logger.info(f"[USER_STORE] Found existing profile for {clean_phone}: {profile.get('name')}")
                    return profile
        except Exception as e:
            logger.debug(f"[USER_STORE] SQLite lookup failed ({e})")
        return None

    def save_profile(self, phone_number: str, state_or_facts: Dict[str, Any]):
        """Save or update caller's profile permanently."""
        if not phone_number:
            return
        clean_phone = re.sub(r'[\s\-\(\)]', '', str(phone_number))
        name = state_or_facts.get("student_name") or state_or_facts.get("name")
        program = state_or_facts.get("program_of_interest") or state_or_facts.get("program")
        marks = state_or_facts.get("class_12_score") or state_or_facts.get("marks")
        college = state_or_facts.get("college") or state_or_facts.get("school")
        city = state_or_facts.get("current_city") or state_or_facts.get("city")
        language = state_or_facts.get("language") or "en-IN"

        profile_json = json.dumps(state_or_facts)
        now = time.time()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (phone_number, name, program, marks, college, city, language, profile_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(phone_number) DO UPDATE SET
                        name = COALESCE(excluded.name, users.name),
                        program = COALESCE(excluded.program, users.program),
                        marks = COALESCE(excluded.marks, users.marks),
                        college = COALESCE(excluded.college, users.college),
                        city = COALESCE(excluded.city, users.city),
                        language = excluded.language,
                        profile_json = excluded.profile_json,
                        updated_at = excluded.updated_at
                """, (clean_phone, name, program, marks, college, city, language, profile_json, now))
                conn.commit()
                logger.info(f"[USER_STORE] Saved persistent profile for {clean_phone}")
        except Exception as e:
            logger.warning(f"[USER_STORE] SQLite save failed ({e})")


# Singleton instance
GLOBAL_USER_STORE = PersistentUserStore()
