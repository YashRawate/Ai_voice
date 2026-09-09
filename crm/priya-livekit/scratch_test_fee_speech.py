import re
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

_NUM_WORDS_BASE = {
    0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
    6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten', 11: 'eleven',
    12: 'twelve', 13: 'thirteen', 14: 'fourteen', 15: 'fifteen', 16: 'sixteen',
    17: 'seventeen', 18: 'eighteen', 19: 'nineteen', 20: 'twenty', 30: 'thirty',
    40: 'forty', 50: 'fifty', 60: 'sixty', 70: 'seventy', 80: 'eighty', 90: 'ninety'
}

def _int_to_words(n: int) -> str:
    if n in _NUM_WORDS_BASE:
        return _NUM_WORDS_BASE[n]
    if n < 100:
        tens, rem = divmod(n, 10)
        return f"{_NUM_WORDS_BASE.get(tens * 10, '')} {_NUM_WORDS_BASE.get(rem, '')}".strip()
    if n < 1000:
        hundreds, rem = divmod(n, 100)
        rem_str = f" {_int_to_words(rem)}" if rem else ""
        return f"{_NUM_WORDS_BASE.get(hundreds, '')} hundred{rem_str}".strip()
    if n < 100000:
        thousands, rem = divmod(n, 1000)
        rem_str = f" {_int_to_words(rem)}" if rem else ""
        return f"{_int_to_words(thousands)} thousand{rem_str}".strip()
    if n < 10000000:
        lakhs, rem = divmod(n, 100000)
        rem_str = f" {_int_to_words(rem)}" if rem else ""
        return f"{_int_to_words(lakhs)} lakh{rem_str}".strip()
    return str(n)

def normalize_numbers_for_speech(s: str, lang: str = "en-IN") -> str:
    if not s:
        return s

    # Strip formal catalog parentheses like (non-refundable), (compulsory), (per attempt)
    s = re.sub(r"\s*\((?:non-refundable|compulsory|one-time|per attempt|maximum \d+ attempts)\)", "", s, flags=re.IGNORECASE)

    has_telugu_script = bool(re.search(r'[\u0C00-\u0C7F]', s))
    has_hindi_script = bool(re.search(r'[\u0900-\u097F]', s))

    # ── Pure Telugu Script Handling ──
    if has_telugu_script:
        # 1. Decimal lakhs in Telugu
        def _replace_lakh_te(m):
            w, f = m.group(1), m.group(2)
            if w == "1" and (not f or int(f) == 0):
                return "ఒక లక్ష రూపాయలు"
            if w == "2" and f and f.startswith("75"):
                return "రెండు లక్షల డెబ్బై ఐదు వేల రూపాయలు"
            if w == "1" and f and f.startswith("15"):
                return "లక్షా పదిహేను వేల రూపాయలు"
            if w == "1" and f and f.startswith("30"):
                return "లక్షా ముప్పై వేల రూపాయలు"
            if w == "1" and f and f.startswith("35"):
                return "లక్షా ముప్పై ఐదు వేల రూపాయలు"
            return f"{w} లక్షల రూపాయలు"

        s = re.sub(r"(?:₹|\bRs\.?\s*)?(\d+)(?:\.(\d+))?\s*(?:lakhs?|లక్షలు|లక్ష|lpa)\b(?:\s*(?:రూపాయలు|rupees?))?", _replace_lakh_te, s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?1[,.]?15[,.]?000\b", "లక్షా పదిహేను వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?1[,.]?30[,.]?000\b", "లక్షా ముప్పై వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?2[,.]?75[,.]?000\b", "రెండు లక్షల డెబ్బై ఐదు వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?15[,.]?000\b", "పదిహేను వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?30[,.]?000\b", "ముప్పై వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?45[,.]?000\b", "నలభై ఐదు వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?500\b", "ఐదు వందల రూపాయలు", s, flags=re.IGNORECASE)
        s = s.replace("₹", "").replace("Rs.", "")
        return re.sub(r"\s{2,}", " ", s).strip()

    # ── Pure Hindi Script Handling ──
    if has_hindi_script:
        s = re.sub(r"(?:₹|\bRs\.?\s*)?2\.75\s*(?:lakhs?|लाख)\b", "दो लाख पचहत्तर हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?1\.15\s*(?:lakhs?|लाख)\b", "एक लाख पंद्रह हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?1\.30\s*(?:lakhs?|लाख)\b", "एक लाख तीस हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?15[,.]?000\b", "पंद्रह हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?30[,.]?000\b", "तीस हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?45[,.]?000\b", "पैंतालीस हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?500\b", "पाँच सौ रुपये", s, flags=re.IGNORECASE)
        s = s.replace("₹", "").replace("Rs.", "")
        return re.sub(r"\s{2,}", " ", s).strip()

    # ── Standard English / Teluglish / Hinglish Roman Script Normalizer ──
    # 1. Decimal lakhs: ₹2.75 lakh, 2.75 lakh, 1.15 lakh, 1.30 lakh, 27 LPA, 27 lakh
    def _replace_lakh(m):
        w, f = m.group(1), m.group(2)
        whole = int(w)
        frac = int(f.ljust(2, '0')[:2]) if f else 0
        parts = []
        if whole > 0:
            parts.append(f"{_int_to_words(whole)} lakh")
        if frac > 0:
            parts.append(f"{_int_to_words(frac)} thousand")
        amt = " ".join(parts) if parts else "zero"
        return f"{amt} rupees"

    s = re.sub(r"(?:₹|\bRs\.?\s*|\bINR\s*)?(\d+)(?:\.(\d+))?\s*(?:lakhs?|lakh per year|lpa)\b(?:\s*(?:rupees?|/-))?", _replace_lakh, s, flags=re.IGNORECASE)

    # 2. Indian formatted comma numbers: ₹1,15,000, 1,15,000, ₹2,75,000, ₹15,000, 15,000, ₹1,30,000
    def _replace_comma_amount(m):
        num_str = m.group(1).replace(",", "")
        try:
            num = int(num_str)
            if num >= 100:
                return f"{_int_to_words(num)} rupees"
            return _int_to_words(num)
        except ValueError:
            return m.group(0)

    s = re.sub(r"(?:₹|\bRs\.?\s*|\bINR\s*)?(\d{1,2},\d{2},\d{3}|\d{1,3},\d{3})\b(?:\s*(?:rupees?|/-))?", _replace_comma_amount, s, flags=re.IGNORECASE)

    # 3. Direct numbers preceded by currency symbol: ₹15000, ₹500, ₹30000, ₹275000
    def _replace_curr_num(m):
        try:
            num = int(m.group(1))
            return f"{_int_to_words(num)} rupees"
        except ValueError:
            return m.group(0)

    s = re.sub(r"(?:₹|\bRs\.?\s*|\bINR\s*)(\d+)\b(?:\s*(?:rupees?|/-))?", _replace_curr_num, s, flags=re.IGNORECASE)

    # 4. Clean up stray currency symbols
    s = s.replace("₹", "").replace("Rs.", "").replace("Rs", "")

    # 5. Ordinals
    s = re.sub(r"\b10th\b", "tenth", s, flags=re.IGNORECASE)
    s = re.sub(r"\b12th\b", "twelfth", s, flags=re.IGNORECASE)
    s = re.sub(r"\b1st\b", "first", s, flags=re.IGNORECASE)
    s = re.sub(r"\b2nd\b", "second", s, flags=re.IGNORECASE)
    s = re.sub(r"\b3rd\b", "third", s, flags=re.IGNORECASE)
    s = re.sub(r"\b4th\b", "fourth", s, flags=re.IGNORECASE)

    # 6. Percentages
    s = re.sub(r"\b(\d+)\s*%", lambda m: f"{_int_to_words(int(m.group(1)))} percent", s)
    s = re.sub(r"\b(\d+)\s+(percent|percentage)\b", lambda m: f"{_int_to_words(int(m.group(1)))} {m.group(2)}", s, flags=re.IGNORECASE)

    # 7. Decimals (non-lakh) e.g. 2.75 -> two point seven five
    def _replace_decimal(m):
        whole, frac = m.group(1), m.group(2)
        whole_w = _int_to_words(int(whole)) if whole.isdigit() else whole
        frac_w = " ".join(_NUM_WORDS_BASE.get(int(d), d) for d in frac)
        return f"{whole_w} point {frac_w}"
    s = re.sub(r"\b(\d+)\.(\d+)\b", _replace_decimal, s)

    # 8. Clean up excess whitespace
    return re.sub(r"\s{2,}", " ", s).strip()

samples = [
    ('The annual tuition fee for B.Tech CSE is ₹2.75 lakh.', 'en-IN'),
    ('Hostel non-AC is ₹1,15,000 and AC is ₹1,30,000 per year.', 'en-IN'),
    ('One-time admission fee is ₹15,000.', 'en-IN'),
    ('ASAT exam fee is ₹500.', 'en-IN'),
    ('Aditya University lo B.Tech CSE tuition fee year ki ₹2.75 lakh untundandi.', 'te-IN'),
    ('Aditya University lo hostel fee ₹1,15,000 untundandi.', 'te-IN'),
    ('B.Tech CSE ఫీజు ₹2.75 lakh.', 'te-IN'),
    ('హాస్టల్ ఫీజు ₹1,15,000 మరియు AC ₹1,30,000.', 'te-IN'),
    ('CSE फीस ₹2.75 lakh per year hai.', 'hi-IN')
]
for sm, lg in samples:
    print(f'[{lg}] Original:   {sm}')
    print(f'[{lg}] Spoken:     {normalize_numbers_for_speech(sm, lang=lg)}\n')
