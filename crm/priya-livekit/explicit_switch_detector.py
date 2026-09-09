# explicit_switch_detector.py

import re
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class ExplicitSwitchResult:
    is_explicit_switch: bool
    target_language: Optional[str] = None
    confidence: float = 0.0
    matched_pattern: Optional[str] = None


class ExplicitLanguageSwitchDetector:
    """
    Layer 5: Detect explicit user language switch requests.
    These commands ALWAYS take top priority over acoustic/script detection.
    """

    def __init__(self):
        # Compiled patterns per language
        self.explicit_patterns: Dict[str, List[re.Pattern]] = {
            "en-IN": [
                re.compile(r"\b(speak|talk|reply|respond|switch|change|converse)\s+(in\s+|to\s+)?(english|angrezi|aanglam)\b", re.I),
                re.compile(r"\benglish\s+(please|pls|only|lo|mein|la)\b", re.I),
                re.compile(r"\b(can\s+you\s+)?speak\s+english\b", re.I),
                re.compile(r"\bfrom\s+now\s+on\s+english\b", re.I),
                re.compile(r"ఇంగ్లీష్|ఇంగ్లీషు|इंग्लिश|अंग्रेजी|ஆங்கிலம்", re.I),
            ],

            "hi-IN": [
                # Hindi explicit requests (Romanized + Devanagari)
                re.compile(r"\b(speak|talk|reply|respond|switch|change)\s+(in\s+|to\s+)?hindi\b", re.I),
                re.compile(r"\b(hindi\s+(mein|me|main|se)|हिंदी\s*(में|मे|से))\b", re.I),
                re.compile(r"\bhindi\s+(bol|bolo|bolna|boliye|baat|baat\s+karo|baat\s+kijiye|please)\b", re.I),
                re.compile(r"हिंदी\s*में\s*(बोल|बोलिए|बातें|बात|कर|करें|करो)", re.I),
                re.compile(r"\b(ab\s+)?hindi\s+mein\s+baat\b", re.I),
                re.compile(r"हिंदी\s*बोलिए|हिंदी\s*में", re.I),
            ],

            "te-IN": [
                # Telugu explicit requests (Romanized + Telugu script)
                re.compile(r"\b(speak|talk|reply|respond|switch|change)\s+(in\s+|to\s+)?telugu\b", re.I),
                re.compile(r"\b(telugu\s+(lo|loh|lo\s+matladu|lo\s+matladandi|cheppandi)|తెలుగు\s*)", re.I),
                re.compile(r"\btelugu\s+(cheppa|cheppandi|matladu|matladandi|matladatha|please)\b", re.I),
                re.compile(r"తెలుగులో\s*(చెప్పండి|మాట్లాడండి|చెప్పు|మాట్లాడు|మాట్ల|చెప్ప)", re.I),
                re.compile(r"\btelugu\s+mein\s+(baat|bolna|boliye)\b", re.I),
                re.compile(r"\btelugu\s+(language|lo)\s+(please|kindly)?\b", re.I),
                re.compile(r"తెలుగు\s*ప్లీజ్|తెలుగులో", re.I),
            ],

            "ta-IN": [
                # Tamil explicit requests (Romanized + Tamil script)
                re.compile(r"\b(speak|talk|reply|respond|switch|change)\s+(in\s+|to\s+)?tamil\b", re.I),
                re.compile(r"\b(tamil\s+(la|lah|pesunga|sollunga)|தமிழ்\s*)", re.I),
                re.compile(r"\btamil\s+(sollunga|solla|pesunga|pesu|please)\b", re.I),
                re.compile(r"தமிழ்(ில்)?\s*(சொல்லுங்க|பேசுங்கள்|பேசுங்க|பேசு)", re.I),
                re.compile(r"\btamil\s+language\s+(please|kindly)?\b", re.I),
                re.compile(r"தமிழில்|தமிழ்\s*ப்ளீஸ்", re.I),
            ]
        }

    def detect_explicit_switch(self, transcript: str) -> ExplicitSwitchResult:
        """
        Scan text for explicit language change directives.
        """
        if not transcript or not transcript.strip():
            return ExplicitSwitchResult(is_explicit_switch=False)

        text = transcript.strip()

        for language, patterns in self.explicit_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    return ExplicitSwitchResult(
                        is_explicit_switch=True,
                        target_language=language,
                        confidence=0.99,
                        matched_pattern=pattern.pattern
                    )

        return ExplicitSwitchResult(is_explicit_switch=False)

    def add_pattern(self, language: str, pattern_str: str):
        """Register custom pattern dynamically."""
        if language not in self.explicit_patterns:
            self.explicit_patterns[language] = []
        self.explicit_patterns[language].append(re.compile(pattern_str, re.I))
