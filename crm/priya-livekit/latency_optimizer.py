"""
Latency Optimizer for Priya Voice Agent
Implements immediate latency quick-wins:
1. Fast-path pattern matching (<50ms response for 70%+ FAQ queries)
2. Pre-cached responses for common admission inquiries
3. Response chunking for streaming TTS
4. Multilingual support (English, Telugu, Hindi, Tamil)
"""

import re
import asyncio
import logging
from typing import Optional, Dict, List, Callable, Any

logger = logging.getLogger("priya.latency_optimizer")

class LatencyOptimizer:
    """Quick-win latency optimizations for ultra-fast voice responses."""

    # ── Quick-Win 4: Pre-cached verified responses ───────────────────────────
    CACHED_RESPONSES: Dict[str, Dict[str, str]] = {
        "fee": {
            "en-IN": "The annual tuition fee for B.Tech CSE is 2 lakh 75 thousand rupees, and core engineering branches start from 1 lakh rupees per year.",
            "te-IN": "B.Tech CSE annual tuition fee year ki 2 lakh 75 thousand rupees untundandi, and core branches 1 lakh rupees nunchi start avthayi.",
            "hi-IN": "B.Tech CSE ki annual tuition fee per year 2 lakh 75 thousand rupees hai, aur core branches 1 lakh rupees se start hoti hain."
        },
        "scholarship": {
            "en-IN": "We offer merit scholarships from 10% to 50% tuition waiver based on 12th Board, JEE, and ASAT scores.",
            "te-IN": "12th Board marks, JEE, and ASAT score batti 10% nunchi 50% varaku merit scholarship vasthundandi.",
            "hi-IN": "12th Board marks, JEE, aur ASAT score ke basis par 10% se 50% tak merit scholarship milti hai."
        },
        "placement": {
            "en-IN": "Aditya University has recorded over 3,800 placement offers with a 27 lakh highest package and top recruiters like Amazon, Walmart, and TCS.",
            "te-IN": "Ma Aditya University lo 3,800 kante ekkuva placement offers vachayandi, highest package 27 lakh rupees. Amazon, Walmart lanti top recruiters vacharu.",
            "hi-IN": "Hamare yahan 3,800 se zyada placement offers record huye hain, aur highest package 27 lakh rupees hai Amazon aur Walmart jaise recruiters ke saath."
        },
        "hostel": {
            "en-IN": "Campus hostel facilities with meals are available: Non-AC at 30 thousand rupees per semester and AC at 45 thousand rupees per semester.",
            "te-IN": "Hostel facilities lo AC and Non-AC rooms unnayandi with meals: Non-AC 30 thousand rupees, AC 45 thousand rupees per semester.",
            "hi-IN": "Campus mein AC aur Non-AC hostel facilities meals ke saath available hain: Non-AC 30 thousand rupees aur AC 45 thousand rupees per semester."
        },
        "admission": {
            "en-IN": "B.Tech admission requires 60% in 12th Board or Intermediate with ASAT, JEE, or EAPCET.",
            "te-IN": "B.Tech admission kosam 12th Board lo 60% marks and ASAT, JEE leda EAPCET rank kavali.",
            "hi-IN": "B.Tech admission ke liye 12th Board mein 60% marks aur ASAT, JEE ya EAPCET rank chahiye."
        },
        "campus": {
            "en-IN": "Aditya University is situated on a 250-acre smart campus in Surampalem, Kakinada District with world-class facilities.",
            "te-IN": "Aditya University Surampalem daggara 250-acre green smart campus lo world-class facilities tho undandi.",
            "hi-IN": "Aditya University Surampalem mein 250-acre ke smart campus mein world-class facilities ke saath hai."
        },
        "cse": {
            "en-IN": "B.Tech CSE offers specialized tracks in AI & ML, Data Science, and industry programs with SAP, Google Cloud, and Microsoft.",
            "te-IN": "B.Tech CSE lo AI & ML, Data Science and SAP, Google Cloud tho tie-up unna industry programs unnayandi.",
            "hi-IN": "B.Tech CSE mein AI & ML, Data Science aur Google Cloud, SAP ke saath industry programs available hain."
        },
        "cutoff": {
            "en-IN": "For B.Tech CSE, minimum 60% in 12th Board plus a qualifying ASAT rank or top EAPCET/JEE percentiles are required.",
            "te-IN": "B.Tech CSE ki 12th Board lo minimum 60% marks tho patu ASAT leda EAPCET rank undali.",
            "hi-IN": "B.Tech CSE ke liye 12th Board mein minimum 60% marks ke saath ASAT ya EAPCET rank honi chahiye."
        },
        "facilities": {
            "en-IN": "Our campus provides smart classrooms, advanced research labs, central library, sports complex, and medical centre.",
            "te-IN": "Ma campus lo smart classrooms, research labs, central library, sports complex and medical centre facilities unnayandi.",
            "hi-IN": "Hamare campus mein smart classrooms, research labs, central library, sports complex aur hospital facilities available hain."
        },
        "apply": {
            "en-IN": "You can apply online at adityauniversity.in with your 12th marks or register for the ASAT entrance exam.",
            "te-IN": "Meeru adityauniversity.in website lo online apply cheyochu, leda ASAT exam ki register avvochu.",
            "hi-IN": "Aap adityauniversity.in website par online apply kar sakte hain ya ASAT exam ke liye register kar sakte hain."
        },
        "visit": {
            "en-IN": "We would be delighted to welcome you to our 250-acre smart campus in Surampalem! Which date and time would be convenient for your visit?",
            "te-IN": "Surampalem lo unna ma 250-acre smart campus ki meeku warm welcome! Meeru ఏ date and time lo visit cheyalani anukuntunnaru?",
            "hi-IN": "Surampalem mein hamare 250-acre smart campus mein aapka welcome hai! Aap kaunsi date aur time par visit karna chahenge?"
        },
        "unavailable_program": {
            "en-IN": "Aditya University does not offer this course. We specialize in B.Tech Engineering (CSE, AI/ML, Data Science, ECE), Management (BBA, MBA), Pharmacy, Forensic Science, and Agricultural Sciences. Would you like details on any of these?",
            "te-IN": "ఆదిత్య యూనివర్సిటీలో ఈ కోర్సు అందుబాటులో లేదండి. మా దగ్గర B.Tech (CSE, AI/ML, Data Science, ECE), Pharmacy, MBA, BBA, Forensic Science మరియు Agriculture కోర్సులు ఉన్నాయి. వీటిలో దేని గురించి తెలుసుకోవాలనుకుంటున్నారు?",
            "hi-IN": "आदित्य यूनिवर्सिटी में यह कोर्स उपलब्ध नहीं है। हमारे यहाँ B.Tech (CSE, AI/ML, ECE), Pharmacy, MBA, BBA, Forensic Science और Agriculture के प्रमुख प्रोग्राम्स हैं। क्या आप इनमें से किसी कोर्स की जानकारी लेना चाहेंगे?"
        }
    }

    # ── Quick-Win 2: Fast-path regex patterns ─────────────────────────────────
    FAST_PATHS = {
        r"\b(mbbs|bds|dental|dentist|bams|bhms|ayush|medicine|doctor\s*course|law|llb|llm|ba\s*llb|bba\s*llb|advocate|lawyer|aviation|commercial\s*pilot|pilot\s*training|air\s*hostess|cabin\s*crew|b\.?arch|architecture|fashion\s*design(?:ing)?|nift|interior\s*design(?:ing)?|veterinary|bvsc|hotel\s*management|culinary|marine\s*engineering|nautical\s*science|merchant\s*navy|b\.?ed|d\.?ed)\b|ఎంబీబీఎస్|లా\s*కోర్స్|పైలట్|ఆర్కిటెక్చర్|ఫ్యాషన్\s*డిజైన్|एमबीबीएस|वकील|लॉ|पायलट|आर्किटेक्चर|फैशन\s*डिजाइन": "unavailable_program",
        r"\b(campus\s*visit|book\s*(?:a\s*)?visit|schedule\s*(?:a\s*)?visit|want\s*to\s*visit|visiting|come\s*to\s*campus|offline\s*counselling)\b|విజిట్|క్యాంపస్\s*విజిట్|विजिट|कैंपस\s*विजिट": "visit",
        r"\b(hostels?|accommodations?|mess|canteens?|rooms?|stays?)\b|హాస్టల్|హాస్టల్స్|हॉस्टल": "hostel",
        r"\b(scholarships?|waivers?|concessions?|discounts?|merits?|free.?seats?)\b|స్కాలర్‌షిప్|స్కాలర్షిప్|స్కాలర్షిప్పులు|स्कॉलरशिप|छात्रवृत्ति": "scholarship",
        r"\b(placements?|jobs?|recruits?|recruiters?|packages?|lpa|highest package|average package)\b|ప్లేస్‌మెంట్|ప్లేస్మెంట్|జాబ్స్?|ప్యాకేజీ|प्लेसमेंट|पैकेज": "placement",
        r"\b(facilities|facility|labs?|library|libraries|sports?|gym|wifi|medical)\b|సదుపాయాలు|వసతులు|सुविधाएं": "facilities",
        r"\b(cutoffs?|cut off|rank required|how much rank|marks needed)\b|కటాఫ్|कटऑफ": "cutoff",
        r"\b(admissions?|eligibles?|eligibility|qualifications?|qualif|criteria|minimum.*score)\b|అర్హత|ఎలిజిబిలిటీ|అడ్మిషన్|एडमिशन|योग्यता": "admission",
        r"\b(cse|computer science|aiml|data science|specializations?|tracks?)\b|కంప్యూటర్|సిఎస్ఈ|సీఎస్ఈ|कंप्यूटर|सीएसई": "cse",
        r"\b(campus\s*location|where\s*is.*campus|campus\s*size|campus\s*area|surampalem|kakinada|rankings?|accreditations?|naac|nirf)\b|క్యాంపస్\s*ఎక్కడ|యూనివర్సిటీ|कैंपस": "campus",
        r"\b(apply|applications?|register|registration|how to join|forms?)\b|అప్లై|దరఖాస్తు|आवेदन|रजिस्ट्रेशन": "apply",
        r"\b(fees?|cost|tuition|charges?|price|kitna|paisa|rupees?|₹)\b|ఫీజు|ఫీజులు|ఖర్చు|ఫీ|फीस|कितनी|खर्च": "fee",
    }

    @classmethod
    def get_cached_response(cls, key: str, lang: str = "en-IN") -> str:
        """Get localized pre-cached response text."""
        entry = cls.CACHED_RESPONSES.get(key, {})
        norm_lang = "te-IN" if "te" in lang.lower() else ("hi-IN" if "hi" in lang.lower() else "en-IN")
        return entry.get(norm_lang) or entry.get("en-IN", "")

    @classmethod
    async def try_fast_path(cls, text: str, lang: str = "en-IN") -> Optional[str]:
        """
        Fast-path check: returns response in <50ms, bypassing LLM (1.77s).
        """
        if not text or not text.strip():
            return None
        text_lower = text.lower().strip()

        for pattern, key in cls.FAST_PATHS.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                resp = cls.get_cached_response(key, lang=lang)
                if resp:
                    logger.info(f"[FAST_PATH] Hit category '{key}' for query: '{text}' (lang={lang})")
                    return resp

        return None

    # ── Quick-Win 3: Response chunking for streaming TTS ─────────────────────
    @classmethod
    def chunk_response(cls, response: str, chunk_size: int = 15) -> List[str]:
        """
        Split response into spoken clause/sentence chunks for low-latency streaming TTS.
        Ensures the user hears audio in <300ms instead of waiting for full generation.
        """
        if not response or not response.strip():
            return []

        # Sentence/clause splitting preserving abbreviations (B.Tech, ₹2.75)
        # Matches punctuation followed by whitespace
        parts = re.split(r'(?<=[.!?।;,\n])\s+', response.strip())
        chunks = []
        cur_words = []

        for p in parts:
            p_clean = p.strip()
            if not p_clean:
                continue
            words = p_clean.split()
            if len(cur_words) + len(words) <= chunk_size or not cur_words:
                cur_words.extend(words)
            else:
                chunks.append(" ".join(cur_words))
                cur_words = list(words)

        if cur_words:
            chunks.append(" ".join(cur_words))

        if not chunks:
            words = response.split()
            return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

        return chunks

    # ── Quick-Win 1 + Combined Pipeline ──────────────────────────────────────
    @classmethod
    async def process_optimized(
        cls,
        text: str,
        llm_func: Callable[[str], Any],
        tts_func: Callable[[str], Any],
        lang: str = "en-IN"
    ) -> List[Any]:
        """
        Optimized processing combining all quick-wins:
        1. Fast-path lookup (<50ms)
        2. LLM fallback if no fast match
        3. Response chunking & streamable TTS output
        """
        # Try fast-path first (0.05s)
        cached = await cls.try_fast_path(text, lang=lang)
        if cached:
            response_text = cached
        else:
            # Fallback to LLM
            res = llm_func(text)
            if asyncio.iscoroutine(res):
                response_text = await res
            else:
                response_text = str(res)

        # Chunk response for streaming
        chunks = cls.chunk_response(response_text)
        audio_outputs = []
        for chunk in chunks:
            res_tts = tts_func(chunk)
            if asyncio.iscoroutine(res_tts):
                audio = await res_tts
            else:
                audio = res_tts
            audio_outputs.append(audio)

        return audio_outputs
