"""
Context-aware filler phrases in English, Telugu, and Hindi.
Plays while Azure LLM thinks on the slow path (~30% of turns).
"""
import random

CONTEXTUAL_FILLERS = {
    "en-IN": {
        "FEES": [
            "Let me check the fee details...",
            "Pulling up the fee structure...",
            "One moment, checking tuition...",
        ],
        "PLACEMENTS": [
            "Let me pull the latest placement data...",
            "Checking our placement records...",
            "Getting the recruitment information...",
        ],
        "SCHOLARSHIPS": [
            "Checking scholarship eligibility...",
            "Let me look up the scholarship slabs...",
            "Getting the financial aid details...",
        ],
        "ELIGIBILITY": [
            "Checking admission requirements...",
            "Let me verify the eligibility...",
            "Getting the admission criteria...",
        ],
        "PROGRAMS": [
            "Let me pull up the program details...",
            "Checking our course offerings...",
            "Getting the program information...",
        ],
        "FACILITIES": [
            "Let me check our campus facilities...",
            "Getting the facility details...",
        ],
        "UNIVERSITY": [
            "Let me get the university details...",
            "Checking our accreditation info...",
        ],
        "GENERAL": [
            "Let me check that for you...",
            "One moment...",
            "Looking that up...",
            "Let me get that information...",
        ],
    },
    "te-IN": {
        "FEES": [
            "ఒక్క నిమిషం, ఫీజు వివరాలు చూస్తున్నాను...",
            "ఫీజు వివరాలు చూసి చెప్తాను...",
        ],
        "PLACEMENTS": [
            "ప్లేస్‌మెంట్ వివరాలు చూస్తున్నాను...",
            "ఒక్క నిమిషం, రికార్డులు చూస్తాను...",
        ],
        "SCHOLARSHIPS": [
            "స్కాలర్‌షిప్ వివరాలు చూస్తున్నాను...",
            "ఒక్క నిమిషం, స్లాబ్స్ చెక్ చేస్తున్నాను...",
        ],
        "ELIGIBILITY": [
            "అడ్మిషన్ ఎలిజిబిలిటీ చూస్తున్నాను...",
            "రిక్వైర్మెంట్స్ చెక్ చేస్తున్నాను...",
        ],
        "PROGRAMS": [
            "కోర్సుల వివరాలు చూస్తున్నాను...",
            "ప్రోగ్రామ్స్ లిస్ట్ చూసి చెప్తాను...",
        ],
        "FACILITIES": [
            "క్యాంపస్ ఫెసిలిటీస్ వివరాలు చూస్తున్నాను...",
        ],
        "UNIVERSITY": [
            "యూనివర్సిటీ వివరాలు చూస్తున్నాను...",
        ],
        "GENERAL": [
            "ఒక్క నిమిషం అండీ, చూసి చెప్తాను...",
            "సరేనండి, వివరాలు చూస్తున్నాను...",
            "ఒక్క క్షణం అండీ...",
        ],
    },
    "hi-IN": {
        "FEES": [
            "एक मिनट, फीस डिटेल्स चेक कर रही हूँ...",
            "फीस की जानकारी देख रही हूँ...",
        ],
        "PLACEMENTS": [
            "एक मिनट, प्लेसमेंट रिकॉर्ड्स चेक कर रही हूँ...",
            "प्लेसमेंट की जानकारी निकाल रही हूँ...",
        ],
        "SCHOLARSHIPS": [
            "स्कॉलरशिप डिटेल्स चेक कर रही हूँ...",
            "एक मिनट, स्कॉलरशिप की जानकारी देख रही हूँ...",
        ],
        "ELIGIBILITY": [
            "एडमिशन रिक्वायरमेंट्स चेक कर रही हूँ...",
            "एक मिनट, एलिजिबिलिटी क्राइटेरिया देख रही हूँ...",
        ],
        "PROGRAMS": [
            "कोर्सेज की लिस्ट देख रही हूँ...",
            "एक मिनट, प्रोग्राम डिटेल्स चेक कर रही हूँ...",
        ],
        "FACILITIES": [
            "कैंपस फैसिलिटीज की जानकारी देख रही हूँ...",
        ],
        "UNIVERSITY": [
            "यूनिवर्सिटी की डिटेल्स चेक कर रही हूँ...",
        ],
        "GENERAL": [
            "एक मिनट रुकिए, चेक कर रही हूँ...",
            "जी, जानकारी देख रही हूँ...",
            "एक पल रुकिए...",
        ],
    },
}


def get_filler(topic: str, lang: str = "en-IN") -> str:
    """Pick a random contextual filler for the given question topic and language."""
    lang_key = lang if lang in CONTEXTUAL_FILLERS else "en-IN"
    lang_dict = CONTEXTUAL_FILLERS[lang_key]
    fillers = lang_dict.get(topic, lang_dict.get("GENERAL", CONTEXTUAL_FILLERS["en-IN"]["GENERAL"]))
    return random.choice(fillers)
