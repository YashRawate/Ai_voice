# language_detector.py

import re
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("priya.language_detector")


@dataclass
class DetectionResult:
    detected_language: str
    confidence: float
    detection_methods: Dict[str, float]
    reason: str


class LanguageDetector:
    """
    Layer 3: Detects language from transcript + STT metadata + audio signals.
    Emits continuous confidence scores rather than premature binary decisions.
    """

    def __init__(self, sarvam_client=None):
        self.sarvam_client = sarvam_client

        # Language-specific keyword tables (Romanized Indic & common English)
        self.keywords: Dict[str, list] = {
            "hi-IN": [
                "kya", "kaise", "kitna", "kitni", "kab", "kahan", "kyun", "hai", "hain", "hoga",
                "hogi", "chahiye", "bataiye", "batao", "boliye", "bolo", "mujhe", "mera", "meri",
                "mere", "karna", "theek", "achha", "nahi", "baat", "namaste", "dhanyawad", "mein"
            ],
            "te-IN": [
                "enti", "entha", "eppudu", "ekkada", "ela", "undi", "undhi", "undha", "ledu",
                "kaavali", "kavali", "cheppandi", "matladandi", "matladu", "meeru", "nenu",
                "naaku", "naa", "bagundi", "vivaralu", "kosam", "gurinchi", "vachayi", "peru",
                "anukuntunna", "avunu", "alage", "sare", "dhanyavadalu", "namaskaram", "inka", "lo"
            ],
            "ta-IN": [
                "enna", "eppadi", "enga", "irukku", "illa", "venum", "sollunga", "pesunga",
                "kedaikkuma", "epdi", "theriyuma", "vanakkam", "nandri", "thaan", "nee", "oru", "la"
            ],
            "en-IN": [
                "what", "is", "how", "can", "will", "fee", "fees", "placement", "campus", "hostel",
                "admission", "scholarship", "branch", "engineering", "college", "university",
                "please", "tell", "details", "cutoff", "eligibility", "structure", "thank", "you"
            ]
        }

        # Unicode script ranges for exact character scanning
        self.script_ranges = {
            "hi-IN": (0x0900, 0x097F),  # Devanagari
            "te-IN": (0x0C00, 0x0C7F),  # Telugu
            "ta-IN": (0x0B80, 0x0BFF),  # Tamil
            "en-IN": (0x0041, 0x007A),  # Basic Latin (A-Z, a-z)
        }

    def analyze_script(self, text: str) -> Tuple[str, float]:
        """Detect dominant script by analyzing Unicode code points."""
        if not text:
            return "unknown", 0.0

        script_counts: Dict[str, int] = {}
        for char in text:
            code = ord(char)
            for lang, (start, end) in self.script_ranges.items():
                if start <= code <= end:
                    script_counts[lang] = script_counts.get(lang, 0) + 1

        if not script_counts:
            return "unknown", 0.0

        dominant_lang = max(script_counts, key=script_counts.get)
        total_matched = sum(script_counts.values())

        # If Native Indic script exists with at least 3 chars, give high weight
        indic_counts = {k: v for k, v in script_counts.items() if k != "en-IN"}
        if indic_counts:
            top_indic = max(indic_counts, key=indic_counts.get)
            if indic_counts[top_indic] >= 3:
                conf = min(1.0, indic_counts[top_indic] / max(1, total_matched))
                return top_indic, max(0.85, conf)

        confidence = script_counts[dominant_lang] / max(1, total_matched)
        return dominant_lang, float(confidence)

    def extract_keywords(self, text: str) -> Tuple[str, float]:
        """Detect language by Romanized and localized vocabulary token matching."""
        if not text:
            return "unknown", 0.0

        tokens = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
        if not tokens:
            return "unknown", 0.0

        keyword_scores: Dict[str, int] = {}
        for lang, kw_list in self.keywords.items():
            matches = sum(1 for kw in kw_list if kw in tokens)
            if matches > 0:
                keyword_scores[lang] = matches

        if not keyword_scores:
            return "unknown", 0.0

        # Prioritize Indic Romanized vocabulary when present
        indic_scores = {k: v for k, v in keyword_scores.items() if k != "en-IN"}
        if indic_scores:
            top_indic = max(indic_scores, key=indic_scores.get)
            if indic_scores[top_indic] >= 2:
                # 2 or more distinct Indic words is a strong signal for code-mixing
                confidence = min(1.0, 0.60 + (indic_scores[top_indic] * 0.15))
                return top_indic, float(confidence)

        detected_lang = max(keyword_scores, key=keyword_scores.get)
        confidence = min(1.0, keyword_scores[detected_lang] / 3.0)
        return detected_lang, float(confidence)

    async def detect_language_with_confidence(
        self,
        transcript: str,
        audio_bytes: bytes = b"",
        stt_language: Optional[str] = None,
        stt_confidence: float = 0.5
    ) -> DetectionResult:
        """
        Multi-method language detection with weighted confidence fusion:
        - STT language: 40%
        - Unicode script analysis: 25%
        - Keyword analysis: 20%
        - Audio/Model ID: 15%
        """
        text = transcript or ""

        # Determine script analysis
        script_lang, script_conf = self.analyze_script(text)

        # Determine keyword analysis
        # Determine script analysis
        script_lang, script_conf = self.analyze_script(text)

        # Determine keyword analysis
        keyword_lang, keyword_conf = self.extract_keywords(text)

        # Method 1: STT language
        m1_lang = stt_language
        m1_conf = float(stt_confidence) if stt_language else 0.0

        # Method 2: Script analysis
        m2_lang = script_lang
        m2_conf = float(script_conf) if script_lang != "unknown" else 0.0

        # Method 3: Keyword analysis
        m3_lang = keyword_lang
        m3_conf = float(keyword_conf) if keyword_lang != "unknown" else 0.0

        # Method 4: Audio language model
        m4_lang = "en-IN"
        m4_conf = 0.0
        if audio_bytes and self.sarvam_client and hasattr(self.sarvam_client, "identify_language"):
            try:
                res = await self.sarvam_client.identify_language(audio_bytes)
                m4_lang = res.get("language_code", "en-IN")
                m4_conf = float(res.get("confidence", 0.0))
            except Exception as e:
                logger.debug(f"audio language model identification skipped: {e}")

        # Weighted score accumulation
        scores = {
            "hi-IN": 0.0,
            "te-IN": 0.0,
            "ta-IN": 0.0,
            "en-IN": 0.0
        }

        # Check if text is Romanized Indic (Latin alphabet with Indic vocabulary)
        is_romanized_indic = (script_lang == "en-IN" and keyword_lang in ("te-IN", "hi-IN", "ta-IN") and keyword_conf >= 0.5)

        if is_romanized_indic:
            # For Romanized Indic: STT (45%) + Keywords (45%) + Audio (10%)
            if m1_lang and m1_lang in scores:
                scores[m1_lang] += m1_conf * 0.45
            if m3_lang in scores and m3_conf > 0:
                scores[m3_lang] += m3_conf * 0.45
            if m4_lang in scores and m4_conf > 0:
                scores[m4_lang] += m4_conf * 0.10
        else:
            # Standard Script-based / English / Native Indic: STT (40%) + Script (25%) + Keywords (25%) + Audio (10%)
            if m1_lang and m1_lang in scores:
                scores[m1_lang] += m1_conf * 0.40
            if m2_lang in scores and m2_conf > 0:
                scores[m2_lang] += m2_conf * 0.25
            if m3_lang in scores and m3_conf > 0:
                scores[m3_lang] += m3_conf * 0.25
            if m4_lang in scores and m4_conf > 0:
                scores[m4_lang] += m4_conf * 0.10

        # If STT and Keywords agree on the same language, boost confidence by 10%
        if m1_lang and m3_lang and m1_lang == m3_lang and m1_lang in scores:
            scores[m1_lang] = min(1.0, scores[m1_lang] + 0.10)

        # Default to en-IN if zero signals
        if max(scores.values()) == 0.0:
            scores["en-IN"] = 0.50

        # Pick highest scoring language
        detected_language = max(scores, key=scores.get)
        total_confidence = min(1.0, float(scores[detected_language]))

        reason = (
            f"Detected {detected_language} (confidence: {total_confidence:.2f}) via "
            f"STT={m1_lang}({m1_conf:.2f}), Script={script_lang}({m2_conf:.2f}), "
            f"Keywords={keyword_lang}({m3_conf:.2f})"
        )

        return DetectionResult(
            detected_language=detected_language,
            confidence=total_confidence,
            detection_methods={
                "stt_language": m1_conf,
                "script_analysis": m2_conf,
                "keyword_analysis": m3_conf,
                "audio_language_model": m4_conf
            },
            reason=reason
        )


class LanguageHysteresisEngine:
    """
    Prevents random language switches using 4 layers:
    1. Native script detection (Devanagari, Telugu, Tamil)
    2. Explicit user requests ("speak in Hindi")
    3. Vocabulary markers (Hindi/Telugu/Tamil words)
    4. Hysteresis: Requires 2 consecutive turns before switching
    """

    HINDI_MARKERS = {
        "kya", "kaise", "kaisa", "kaisi", "kitna", "kitni", "kab", "kahan", "kyun", "hai", "hain", "hoga",
        "hogi", "chahiye", "bataiye", "batao", "boliye", "bolo", "mujhe", "mera", "meri", "mere", "karna",
        "karein", "theek", "achha", "accha", "nahi", "baat", "namaste", "dhanyawad", "mein", "milega",
        "bilkul", "thik", "kuch", "ke", "baare", "pata"
    }

    TELUGU_MARKERS = {
        "enti", "entha", "enta", "eppudu", "ekkada", "ela", "undi", "undhi", "undha", "ledu",
        "kaavali", "kavali", "cheppandi", "matladandi", "matladu", "meeru", "nenu", "naaku", "naa",
        "bagundi", "vivaralu", "kosam", "gurinchi", "vachayi", "peru", "anukuntunna", "avunu", "alage",
        "sare", "dhanyavadalu", "namaskaram", "inka", "lo", "unnayi", "vastunda", "babu", "ani", "andi"
    }

    TAMIL_MARKERS = {
        "enna", "eppadi", "epdi", "enga", "irukku", "illa", "venum", "sollunga", "pesunga",
        "kedaikkuma", "theriyuma", "vanakkam", "nandri", "thaan", "nee", "oru", "la"
    }

    def __init__(self, default_lang: str = "en-IN"):
        self.dominant_lang = default_lang
        self.pending_lang: Optional[str] = None
        self.pending_count = 0

    def evaluate_turn(self, text: str, stt_lang: str = None) -> Tuple[str, str]:
        """
        Decide language for this turn.
        Returns (language, reason).
        """
        if not text or not text.strip():
            return self.dominant_lang, "empty_input"

        t_clean = text.strip()
        t_lower = t_clean.lower()

        # ===== LAYER 1: NATIVE SCRIPT =====
        # If user types/speaks in Devanagari, it's DEFINITELY Hindi
        if re.search(r'[\u0900-\u097F]', t_clean):
            self.dominant_lang = "hi-IN"
            self.pending_lang = None
            self.pending_count = 0
            return "hi-IN", "devanagari_script"

        # If user speaks in Telugu script, it's DEFINITELY Telugu
        if re.search(r'[\u0C00-\u0C7F]', t_clean):
            self.dominant_lang = "te-IN"
            self.pending_lang = None
            self.pending_count = 0
            return "te-IN", "telugu_script"

        # If user speaks in Tamil script, it's DEFINITELY Tamil
        if re.search(r'[\u0B80-\u0BFF]', t_clean):
            self.dominant_lang = "ta-IN"
            self.pending_lang = None
            self.pending_count = 0
            return "ta-IN", "tamil_script"

        # ===== LAYER 2: EXPLICIT REQUEST =====
        # User says "speak in English"
        if re.search(r'\b(english\s*please|speak.*english|in\s*english|talk.*english)\b', t_lower):
            self.dominant_lang = "en-IN"
            self.pending_lang = None
            self.pending_count = 0
            return "en-IN", "explicit_english_request"

        # User says "hindi me"
        if re.search(r'\b(hindi\s*me|hindi\s*mein|bolo\s*hindi|speak.*hindi|talk.*hindi)\b', t_lower):
            self.dominant_lang = "hi-IN"
            self.pending_lang = None
            self.pending_count = 0
            return "hi-IN", "explicit_hindi_request"

        # User says "telugu lo"
        if re.search(r'\b(telugu\s*lo|speak.*telugu|telugu.*please|talk.*telugu|matladandi)\b', t_lower):
            self.dominant_lang = "te-IN"
            self.pending_lang = None
            self.pending_count = 0
            return "te-IN", "explicit_telugu_request"

        # User says "tamil la"
        if re.search(r'\b(tamil\s*la|speak.*tamil|tamil.*please|talk.*tamil|pesunga)\b', t_lower):
            self.dominant_lang = "ta-IN"
            self.pending_lang = None
            self.pending_count = 0
            return "ta-IN", "explicit_tamil_request"

        # ===== LAYER 3: VOCABULARY MARKERS =====
        words = set(re.findall(r'\b\w+\b', t_lower))
        hi_score = len(words & self.HINDI_MARKERS)
        te_score = len(words & self.TELUGU_MARKERS)
        ta_score = len(words & self.TAMIL_MARKERS)

        detected = None
        if hi_score >= 2 and hi_score > te_score and hi_score > ta_score:
            detected = "hi-IN"
        elif te_score >= 2 and te_score > hi_score and te_score > ta_score:
            detected = "te-IN"
        elif ta_score >= 2 and ta_score > hi_score and ta_score > te_score:
            detected = "ta-IN"
        elif stt_lang in ["hi-IN", "te-IN", "ta-IN"]:
            detected = stt_lang

        # ===== LAYER 4: HYSTERESIS =====
        # If same language detected, keep it
        if not detected or detected == self.dominant_lang:
            self.pending_lang = None
            self.pending_count = 0
            return self.dominant_lang, "dominant_preserved"

        # If new language: require 2 consecutive turns before switching
        if detected == self.pending_lang:
            self.pending_count += 1
            if self.pending_count >= 2:  # Confirmed!
                self.dominant_lang = detected
                self.pending_lang = None
                self.pending_count = 0
                logger.info(f"🔄 Language switch confirmed: {self.dominant_lang} (2-turn hysteresis)")
                return detected, "hysteresis_switch_confirmed"
        else:
            # New detected language, start counter
            self.pending_lang = detected
            self.pending_count = 1
            logger.info(f"⏳ Language pending: {detected} (turn 1/2)")

        # While pending, STAY in current language
        return self.dominant_lang, "hysteresis_holding"

