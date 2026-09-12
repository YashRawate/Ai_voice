# crm/priya-livekit/fast_path.py
"""
Deterministic Fast-Path Query Cache for AdmitAI Priya Voice Agent.
Bypasses LLM generation entirely (<100ms response time) for common factual questions:
  - CSE fees / tuition fees
  - Campus location & campus size
  - Hostels & accommodation fees
  - Placement packages & recruiters
  - Scholarships & fee waivers
"""

from __future__ import annotations

import re
from typing import Callable, Dict, Optional, Tuple


# Deterministic verified factual responses across languages
FAST_PATH_RESPONSES = {
    "cse_fee": {
        "en-IN": "B.Tech CSE fees are ₹2,75,000 per year.",
        "hi-IN": "बी.टेक सीएसई की फीस प्रति वर्ष ₹2,75,000 है।",
        "te-IN": "బి.టెక్ సిఎస్ఈ ఫీజు సంవత్సరానికి ₹2,75,000 అండీ.",
    },
    "campus_location": {
        "en-IN": "Our campus is in Surampalem, Kakinada District, Andhra Pradesh across 250 green acres.",
        "hi-IN": "हमारा 250 एकड़ का कैंपस सुरमपलेम, काकीनाडा जिला, आंध्र प्रदेश में स्थित है।",
        "te-IN": "మా క్యాంపస్ కాకినాడ జిల్లా సురంపాలెంలో 250 ఎకరాల విస్తీర్ణంలో ఉంది అండీ.",
    },
    "hostel_fee": {
        "en-IN": "Hostel fees with meals are ₹30,000 per semester for Non-AC and ₹45,000 per semester for AC.",
        "hi-IN": "हॉस्टल की फीस भोजन के साथ नॉन-एसी ₹30,000 और एसी ₹45,000 प्रति सेमेस्टर है।",
        "te-IN": "హాస్టల్ ఫీజు భోజనంతో కలిపి నాన్-ఏసీ సెమిస్టర్‌కి ₹30,000, ఏసీ సెమిస్టర్‌కి ₹45,000 అండీ.",
    },
    "placements": {
        "en-IN": "Aditya University had 3,832+ placements with a highest package of ₹27 LPA at Walmart this year.",
        "hi-IN": "आदित्य यूनिवर्सिटी में इस साल ₹27 लाख के उच्चतम पैकेज के साथ 3,832 से अधिक प्लेसमेंट हुए हैं।",
        "te-IN": "ఆదిత్య యూనివర్సిటీలో ఈ సంవత్సరం వాల్‌మార్ట్‌లో ₹27 లక్షల అత్యధిక ప్యాకేజీతో 3,832 కంటే ఎక్కువ ప్లేస్‌మెంట్స్ వచ్చాయి అండీ.",
    },
    "scholarships": {
        "en-IN": "We provide merit scholarships from 10% to 50% tuition waiver based on your 12th Board or JEE scores.",
        "hi-IN": "हम 12वीं बोर्ड या जेईई स्कोर के आधार पर 10% से 50% तक मेरिट स्कॉलरशिप देते हैं।",
        "te-IN": "మీ 12వ తరగతి లేదా జేఈఈ స్కోర్ ఆధారంగా 10% నుండి 50% వరకు మెరిట్ స్కాలర్‌షిప్ లభిస్తుంది అండీ.",
    },
}

# Regex patterns matching deterministic intent
FAST_PATH_PATTERNS: list[Tuple[re.Pattern, str]] = [
    (re.compile(r'\b(fee\s*structure|tuition\s*fees?|course\s*fees?|fee\s*details?|fees?)\b', re.IGNORECASE), "cse_fee"),
    (re.compile(r'\b(cse|computer\s*science|ai\s*ml|aiml|data\s*science).*(fee|fees|tuition|cost|charges?)\b', re.IGNORECASE), "cse_fee"),
    (re.compile(r'\b(fee|fees|tuition|cost)\b.*\b(cse|computer|aiml|btech)\b', re.IGNORECASE), "cse_fee"),
    (re.compile(r'\b(where.*campus|campus.*location|where.*located|campus.*address|campus.*size)\b', re.IGNORECASE), "campus_location"),
    (re.compile(r'\b(कैंपस.*कहाँ|कहाँ.*कैंपस|कहाँ.*स्थित)\b', re.IGNORECASE), "campus_location"),
    (re.compile(r'\b(hostels?|accommodation|rooms?).*(fee|fees|rent|cost|charges?)\b', re.IGNORECASE), "hostel_fee"),
    (re.compile(r'\b(हॉस्टल.*फीस|फीस.*हॉस्टल)\b', re.IGNORECASE), "hostel_fee"),
    (re.compile(r'\b(highest\s*package|placement\s*record|placement\s*details?|top\s*recruiters?|companies.*visit)\b', re.IGNORECASE), "placements"),
    (re.compile(r'\b(scholarship\s*criteria|merit\s*scholarships?|fee\s*waivers?|discount\s*in\s*fees?)\b', re.IGNORECASE), "scholarships"),
]


def try_fast_path(transcript: str, language_code: str = "en-IN") -> Optional[str]:
    """
    Evaluates caller transcript against deterministic fast-path cache.
    Returns immediate verified answer (<100ms) or None if query requires LLM reasoning.
    """
    if not transcript:
        return None

    t_clean = transcript.strip()
    for pattern, key in FAST_PATH_PATTERNS:
        if pattern.search(t_clean):
            lang_dict = FAST_PATH_RESPONSES.get(key, {})
            # Match language or fallback to English
            ans = lang_dict.get(language_code) or lang_dict.get("en-IN")
            if ans:
                return ans

    return None
