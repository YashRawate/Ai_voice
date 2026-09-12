# test_language_locking.py
"""
Test Suite for Priya Voice Agent Language Locking & Code-Mixed Stability.

Verifies:
1. Code-mixed Hindi / Hinglish utterances do not flip the session back to English.
2. Short loanword utterances ('okay', 'fees', 'form') preserve the active Indic language.
3. Explicit user switches ('speak in English', 'हिंदी में बात करो') trigger immediate language updates.
4. Confident long English utterances switch back to English.
5. System prompt enforces strict 'MUST respond ONLY in <language>' with native script.
6. detect_language honors STT multi-language tags even on Romanized text.
"""

import unittest
from priya.language import (
    resolve_mixed_language,
    build_language_system_prompt,
    normalize_lang_code,
    SUPPORTED_LANGS,
    LANG_NAMES,
)
from agent import detect_language
from prompts import format_system_prompt


class TestLanguageLocking(unittest.TestCase):

    def test_normalize_lang_codes(self):
        self.assertEqual(normalize_lang_code("hi"), "hi-IN")
        self.assertEqual(normalize_lang_code("te"), "te-IN")
        self.assertEqual(normalize_lang_code("ta"), "ta-IN")
        self.assertEqual(normalize_lang_code("en"), "en-IN")
        self.assertEqual(normalize_lang_code("hi-IN"), "hi-IN")
        self.assertEqual(normalize_lang_code(""), "en-IN")

    def test_codemixed_hindi_preserves_session_language(self):
        """Code-mixed Hindi with English technical words must stay locked in hi-IN."""
        session_lang = "hi-IN"

        # Utterance with English loanwords + Hindi grammar
        u1 = "admission ka status batao please"
        self.assertEqual(resolve_mixed_language("en-IN", u1, session_lang), "hi-IN")

        # Utterance asking about fees
        u2 = "B.Tech computer science ki fees kitni hai?"
        self.assertEqual(resolve_mixed_language("en-IN", u2, session_lang), "hi-IN")

        # Utterance with Devanagari script
        u3 = "मुझे स्कॉलरशिप के बारे में जानना है"
        self.assertEqual(resolve_mixed_language("hi-IN", u3, session_lang), "hi-IN")

    def test_short_utterance_does_not_flip_language(self):
        """Short neutral / loanword utterances (< 15 chars) must not flip language."""
        self.assertEqual(resolve_mixed_language("en-IN", "okay", session_lang="hi-IN"), "hi-IN")
        self.assertEqual(resolve_mixed_language("en-IN", "yes", session_lang="hi-IN"), "hi-IN")
        self.assertEqual(resolve_mixed_language("en-IN", "fine", session_lang="te-IN"), "te-IN")
        self.assertEqual(resolve_mixed_language("en-IN", "form", session_lang="hi-IN"), "hi-IN")
        self.assertEqual(resolve_mixed_language("en-IN", "fees kitna", session_lang="hi-IN"), "hi-IN")

    def test_explicit_language_switch_overrides_immediately(self):
        """Explicit requests ('speak in English', 'हिंदी में बात करो') take 100% priority."""
        # Switch from Hindi to English
        res1 = resolve_mixed_language("en-IN", "please speak in English from now on", session_lang="hi-IN")
        self.assertEqual(res1, "en-IN")

        # Switch from English to Hindi
        res2 = resolve_mixed_language("en-IN", "हिंदी में बात करो", session_lang="en-IN")
        self.assertEqual(res2, "hi-IN")

        # Switch from English to Telugu
        res3 = resolve_mixed_language("en-IN", "telugu lo matladandi please", session_lang="en-IN")
        self.assertEqual(res3, "te-IN")

    def test_confident_sustained_english_switches_session(self):
        """A long, purely English question with no Indic markers switches session back to English."""
        session_lang = "hi-IN"
        pure_english = "Could you please explain the complete eligibility criteria for undergraduate programs?"
        self.assertEqual(resolve_mixed_language("en-IN", pure_english, session_lang), "en-IN")

    def test_stt_language_hint_honored_in_detect_language(self):
        """STT language hint from Sarvam Saaras must not be blocked by Romanized characters."""
        code, reason = detect_language("admission status", current_lang="en-IN", stt_lang="hi-IN")
        self.assertEqual(code, "hi-IN")
        self.assertIn("stt_hint", reason)

        code_te, reason_te = detect_language("fees entha", current_lang="en-IN", stt_lang="te-IN")
        self.assertEqual(code_te, "te-IN")

    def test_system_prompt_includes_strict_language_mandate(self):
        """Verifies system prompt strictly mandates response in caller's language and script."""
        hindi_prompt = build_language_system_prompt("hi-IN")
        self.assertIn("The user is speaking in Hindi", hindi_prompt)
        self.assertIn("You MUST respond ONLY in Hindi", hindi_prompt)
        self.assertIn("Devanagari script", hindi_prompt)
        self.assertIn("Do NOT switch to English", hindi_prompt)

        telugu_prompt = build_language_system_prompt("te-IN")
        self.assertIn("The user is speaking in Telugu", telugu_prompt)
        self.assertIn("You MUST respond ONLY in Telugu", telugu_prompt)
        self.assertIn("Telugu script", telugu_prompt)

        # In format_system_prompt
        sys_prompt = format_system_prompt(facts={}, stage="GREETING", next_field="name", language_code="hi-IN")
        self.assertIn("You MUST respond ONLY in Hindi", sys_prompt)


if __name__ == "__main__":
    unittest.main()
