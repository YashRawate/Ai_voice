# no_repetition.py
"""
No Repetition Engine for Priya Voice Agent.
Ensures the agent NEVER asks the same question twice in the entire call.
Tracks asked questions, user voluntary disclosures, and user refusals.
"""

from __future__ import annotations

import logging
from typing import List, Set

logger = logging.getLogger("priya.no_repetition")


class NoRepetitionEngine:
    """Guarantee zero repeated questions across the entire conversation."""

    POTENTIAL_QUESTIONS = [
        "q_name",
        "name_question",
        "q_program",
        "program_question",
        "q_score",
        "score_question",
        "q_exam",
        "exam_question",
        "q_visit",
        "campus_visit",
    ]

    def __init__(self, history):
        self.history = history

    def should_skip_question(self, question_id: str) -> bool:
        """Return True if this question should be skipped (already asked, known, or refused)."""
        # 1. Skip if already asked
        if self.history.is_question_asked(question_id):
            return True

        # 2. Skip if user already told us
        if self.history.has_fact_for(question_id):
            return True

        # 3. Skip if user refused or asked to postpone
        if self.history.is_refused(question_id):
            return True

        return False

    def is_user_refusing(self, question_id: str) -> bool:
        """Check if user refused or postponed this question."""
        return self.history.is_refused(question_id)

    def get_questions_to_skip(self) -> List[str]:
        """Get all question keys that must NOT be asked."""
        skip_list = []
        for q_id in self.POTENTIAL_QUESTIONS:
            if self.should_skip_question(q_id):
                skip_list.append(q_id)
        return skip_list
