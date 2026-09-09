# llm_with_history.py
"""
LLM Prompt Builder and Handler with Full Conversation History Context.
Guarantees the LLM has access to the ENTIRE call history, known facts, and avoided questions.
Prevents interrogation behavior by commanding the LLM to answer the user's immediate question first.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from language_handler import LanguageHandler

logger = logging.getLogger("priya.llm_history")


class LLMWithHistory:
    """Injects full conversation history and anti-repetition rules into LLM context."""

    def __init__(self, history, question_engine=None):
        self.history = history
        self.questions = question_engine

    def build_prompt(self, user_input: str, language: str = "en-IN") -> str:
        """Build comprehensive system prompt containing full conversation context."""
        full_context = self.history.get_context()
        lang_style = LanguageHandler.get_language_style(language)

        prompt = f"""You are Priya, Senior Admissions Counsellor at Aditya University.

CRITICAL CONVERSATIONAL INSTRUCTIONS:
1. You have access to the ENTIRE conversation history below. Use it to maintain seamless continuity across turns and languages.
2. ANSWER THE USER'S DIRECT QUESTION FIRST! Never deflect or demand their name/score before answering their question.
3. NEVER ask for information already provided in the facts or previous turns.
4. NEVER repeat a question listed in "QUESTIONS ALREADY ASKED".
5. If user declined or postponed a detail (e.g. 12th score or exam), respect it and do NOT pester them.
6. Speak in a warm, concise, human telephone counselor tone (max 25 words per reply).
7. Exactly ONE question per turn. Never combine multiple questions.

{full_context}

LANGUAGE STYLE (respond in this language — all facts & history above still apply):
{lang_style}

CURRENT USER INPUT:
{user_input}

Generate your response following these rules. Reference known facts naturally to show you remember.
"""
        return prompt

    def build_turn_directives(self, user_input: str, language: str = "en-IN") -> str:
        """
        Build compact turn directives to inject into LiveKit chat_ctx system messages.
        Provides full facts, anti-repetition blacklist, and context guidance without token bloat.
        """
        directives = []

        # 1. Facts already known
        known_facts = []
        for k in ["name", "program", "score", "exam", "city"]:
            val = self.history.get_fact(k)
            if val and str(val).lower() != "none":
                known_facts.append(f"{k.upper()}={val}")
        if known_facts:
            directives.append(f"KNOWN CALLER FACTS (DO NOT RE-ASK): {', '.join(known_facts)}")

        # 2. Blocked questions
        all_blocked = set(self.history.questions_asked) | set(self.history.refusals)
        if all_blocked:
            directives.append(f"QUESTIONS TO NEVER REPEAT: {', '.join(sorted(all_blocked))}")

        # 3. Conversational flow guidance
        directives.append("CONVERSATION DIRECTIVE: Answer the caller's immediate question or concern FIRST. Never interrogate.")

        # 4. If we have both program and score, guide toward closing action
        if self.history.has_fact('program') and self.history.has_fact('score'):
            if not self.history.is_question_asked('q_visit') and not self.history.is_refused('q_visit'):
                directives.append("ACTION CLOSE: If appropriate, offer a Campus Visit or direct application link.")

        return "\n".join(directives)

    async def generate_response(
        self,
        user_input: str,
        llm_client: Any,
        language: str = "en-IN"
    ) -> str:
        """Generate response with full history using an async LLM client."""
        # Extract facts from user input first
        self.history.extract_facts(user_input)

        prompt = self.build_prompt(user_input, language=language)

        if hasattr(llm_client, "generate"):
            response = await llm_client.generate(
                system_prompt=prompt,
                user_input=user_input,
                language=language,
                cache_control={"type": "ephemeral"}
            )
            return response

        return f"Hello! I am Priya from Aditya University. How can I assist you with admissions today?"


# Alias for research spec compatibility
IntelligentPrompting = LLMWithHistory
