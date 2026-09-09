# question_engine.py
"""
Question Engine for Priya Voice Agent.
Decides the next natural, non-mandatory question while guaranteeing ZERO repetition.
Adapts to voluntary caller facts and generates fact-based wrap-up summaries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("priya.question_engine")


class QuestionEngine:
    """Decide what to ask next based on what is already known; never repeat questions."""

    def __init__(self, history):
        self.history = history

    def get_next_question(self, user_intent: str = "") -> Optional[str]:
        """
        Determine the next relevant question to ask.
        Never forces a rigid questionnaire; asks only what is relevant to the caller's context.
        """
        # 1. If caller asked about fees or scholarships, prioritize score
        if any(w in user_intent.lower() for w in ["fee", "fees", "scholarship", "cost", "waiver", "discount"]):
            if not self.history.has_fact('score') and self.history.should_ask_question('q_score', 'score'):
                self.history.record_question_asked('q_score')
                prog = self.history.get_fact('program')
                if prog:
                    return f"What is your 12th board or intermediate percentage? I can calculate your exact scholarship for {prog}."
                return "What is your 12th board percentage? We offer up to 50% merit scholarships based on your score."

        # 2. If program is not known, ask about branch/program interest
        if not self.history.has_fact('program'):
            if self.history.should_ask_question('q_program', 'program'):
                self.history.record_question_asked('q_program')
                return "Which program or branch are you interested in at Aditya University?"

        # 3. If score is not known (and not already asked/refused)
        if not self.history.has_fact('score'):
            if self.history.should_ask_question('q_score', 'score'):
                self.history.record_question_asked('q_score')
                prog = self.history.get_fact('program') or "your program"
                return f"What is your 12th score? We offer merit scholarships for {prog}."

        # 4. If entrance exam is not known (and not already asked/refused)
        if not self.history.has_fact('exam'):
            if self.history.should_ask_question('q_exam', 'exam'):
                self.history.record_question_asked('q_exam')
                return "Did you appear for any entrance exams like JEE, AP EAPCET, or our ASAT exam?"

        # 5. If we have program and score, offer closing action (Campus Visit or Application Link)
        if self.history.has_fact('program') and self.history.has_fact('score'):
            if self.history.should_ask_question('q_visit', 'visit'):
                self.history.record_question_asked('q_visit')
                return "Would you like to book a campus visit with your parents this Saturday to see our labs and campus?"

        # 6. Default open question
        if self.history.should_ask_question('q_anything_else', 'anything_else'):
            self.history.record_question_asked('q_anything_else')
            return "Is there anything else you would like to know about our admissions or facilities?"

        return None

    def get_response_based_on_facts(self) -> str:
        """Generate structured response summary using known facts."""
        lines = []

        if self.history.has_fact('name'):
            lines.append(f"- Student Name: {self.history.get_fact('name')}")

        if self.history.has_fact('program'):
            lines.append(f"- Program: {self.history.get_fact('program')}")

        if self.history.has_fact('score'):
            score_str = str(self.history.get_fact('score'))
            lines.append(f"- 12th Board Score: {score_str}")

            # Compute scholarship tier
            try:
                numeric_score = float(score_str.rstrip('%').strip())
                if numeric_score >= 95:
                    scholarship = "50-75% tuition fee waiver (Top Merit Tier)"
                elif numeric_score >= 90:
                    scholarship = "40-50% tuition fee waiver (Category A)"
                elif numeric_score >= 85:
                    scholarship = "30% tuition fee waiver (Category B)"
                elif numeric_score >= 80:
                    scholarship = "20% tuition fee waiver (Category C)"
                else:
                    scholarship = "Eligible for ASAT Entrance Scholarship"
                lines.append(f"- Scholarship Qualification: {scholarship}")
            except (ValueError, AttributeError):
                pass

        if self.history.has_fact('exam'):
            exam_val = self.history.get_fact('exam')
            if exam_val and exam_val.lower() != "none":
                lines.append(f"- Entrance Exam: {exam_val}")

        if self.history.has_fact('city'):
            lines.append(f"- Location: {self.history.get_fact('city')}")

        if not lines:
            return "General admission enquiry for Aditya University."

        return "\n".join(lines)


# Alias for backwards compatibility with research spec
FlexibleInformationGathering = QuestionEngine
