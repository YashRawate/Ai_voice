"""
transcript_guards.py - decide whether a transcript really came from the caller and is safe to act on.

Written from the TEST_128 log, where background chatter caused:
  * a Bengali-script transcript to be treated as Hindi (language switch)
  * "This is the final rule."  ->  student_name overwritten with "the final"
  * a Hindi sentence containing "बस" ->  false goodbye, Priya ended the call
  * Priya's reply cut off mid-sentence

Use these functions BEFORE any state change (language switch, name/slot update, goodbye, LLM call).
Run `py transcript_guards.py` to execute the self-tests.
"""
import re
import unicodedata

# Scripts the agent really supports. Add others (for example "TAMIL") only if you support them.
ALLOWED_SCRIPTS = {"LATIN", "DEVANAGARI", "TELUGU"}

# --------------------------------------------------------------------------- script check
def dominant_script(text: str):
    counts = {}
    for ch in text:
        if ch.isalpha():
            try:
                key = unicodedata.name(ch).split()[0]      # e.g. LATIN, DEVANAGARI, BENGALI, TELUGU
            except ValueError:
                continue
            counts[key] = counts.get(key, 0) + 1
    return max(counts, key=counts.get) if counts else None


# --------------------------------------------------------------------------- name guard
STOP_NAME_WORDS = {
    "the", "a", "an", "final", "rule", "yes", "no", "ok", "okay", "hello", "hi", "sir", "madam",
    "btech", "ptech", "mtech", "mba", "bba", "bsc", "cse", "ece", "eee", "mech", "mechanical", "civil",
    "it", "aiml", "fees", "fee", "hostel", "college", "university", "admission", "course", "branch",
    "percent", "percentage", "score", "marks", "please", "thanks", "thank", "you", "i", "am", "is",
    "are", "this", "that", "what", "how", "preference", "cricket", "record", "culture", "good", "fine",
    "interested", "looking", "want", "need", "know", "about", "for", "to", "in", "of", "and",
}
EXPLICIT_NAME = re.compile(
    r"\b(?:my name is|my name's|myself|call me|name is)\s+([A-Za-z][A-Za-z.\-']*(?:\s+[A-Za-z][A-Za-z.\-']*){0,2})",
    re.I)
SOFT_NAME = re.compile(
    r"\b(?:i am|i'm|this is)\s+([A-Za-z][A-Za-z.\-']*(?:\s+[A-Za-z][A-Za-z.\-']*){0,2})", re.I)


def _name_ok(words):
    if not 1 <= len(words) <= 3:
        return False
    for w in words:
        base = re.sub(r"[^a-z]", "", w.lower())          # "B.Tech" -> "btech"
        if len(base) < 2 or base in STOP_NAME_WORDS:
            return False
    return True


def extract_name(text: str, awaiting_name: bool = False):
    """Return a safe name or None.
    - 'my name is ...' / 'myself ...' are always allowed.
    - 'i am ...' / 'this is ...' and bare names are only allowed while we are asking for the name.
    - any stop word (the, final, btech, yes, ...) rejects the whole candidate."""
    t = text.strip().rstrip(".!?,")
    m = EXPLICIT_NAME.search(t)
    if m and _name_ok(m.group(1).split()):
        return " ".join(w.capitalize() for w in m.group(1).split())
    if awaiting_name:
        m = SOFT_NAME.search(t)
        cand = m.group(1) if m else t
        words = cand.split()
        if _name_ok(words):
            return " ".join(w.capitalize() for w in words)
    return None


# --------------------------------------------------------------------------- farewell guard
FAREWELL = [
    r"\b(bye|goodbye|good bye|see you|talk (to you )?later)\b",
    r"\bthat'?s (all|it)\b", r"\bnothing else\b", r"\bno (more )?(questions|doubts)\b",
    r"\bthank(s| you)\b.*\b(bye|that'?s all)\b",
    r"(अलविदा|फिर मिलेंगे|बस इतना ही|बस यही|और कुछ नहीं|कुछ और नहीं|कुछ नहीं चाहिए)",
    r"(ఇంకేమీ లేదు|ఇంకేం లేదు|వస్తాను)",            # have a Telugu speaker review this list
]
FAREWELL_RE = [re.compile(p, re.I) for p in FAREWELL]


def is_farewell(text: str) -> bool:
    """Strict: needs a real goodbye phrase. A lone 'बस' / 'ok' / 'thanks' is NOT a farewell."""
    return any(r.search(text) for r in FAREWELL_RE)


# --------------------------------------------------------------------------- relevance / noise
DOMAIN = re.compile(
    r"(fee|fees|hostel|scholarship|course|b\.?tech|m\.?tech|mba|cse|ece|eee|mech|civil|aiml|branch|placement|"
    r"admission|campus|visit|eapcet|eamcet|jee|rank|marks|percent|percentage|score|cutoff|seat|apply|"
    r"counsell?ing|college|university|bus|transport|mess|food|address|location|call|callback|"
    r"फीस|हॉस्टल|कोर्स|एडमिशन|प्लेसमेंट|कैंपस|स्कॉलरशिप|ఫీజు|హాస్టల్|కోర్సు|అడ్మిషన్)", re.I)
SHORT_REAL = {"yes", "no", "yeah", "yep", "nope", "ok", "okay", "hello", "hi", "sure", "haan", "han", "nahi",
              "ha", "avunu", "kaadu", "stop", "wait", "sorry", "repeat", "again", "pardon", "हाँ", "हां", "नहीं", "जी"}
INTERRUPT_WORDS = re.compile(r"\b(stop|wait|hold on|one (second|moment)|sorry|pardon|excuse me|hello)\b", re.I)

SLOT_VALIDATORS = {
    "branch": re.compile(r"\b(cse|ece|eee|mech(anical)?|civil|it|ai|aiml|ds|data science|computer|electronics|electrical)\b", re.I),
    "percentage": re.compile(r"(\d{1,3}(\.\d+)?\s*(%|percent|percentage)?)|(\b(eighty|ninety|seventy|sixty|fifty)\b)", re.I),
    "yesno": re.compile(r"\b(yes|no|yeah|yep|nope|sure|correct|right|haan|nahi|avunu|kaadu)\b|हाँ|हां|नहीं", re.I),
}


def classify_transcript(text, *, awaiting_slot=None, agent_speaking=False,
                        allowed_scripts=ALLOWED_SCRIPTS, min_words_when_speaking=3):
    """Return (verdict, reason). verdict is 'ok', 'unclear' or 'drop'.
       drop    -> ignore completely (no state change, no reply)
       unclear -> do not change state; ask the caller to repeat at most once, then stay quiet
       ok      -> process normally"""
    t = (text or "").strip()
    if not t:
        return "drop", "empty"
    script = dominant_script(t)
    if script is None:
        return "drop", "no letters"
    if script not in allowed_scripts:
        return "drop", f"unsupported script {script}"
    words = re.findall(r"\w+", t)
    if agent_speaking and len(words) < min_words_when_speaking and not INTERRUPT_WORDS.search(t):
        return "drop", "too short while agent speaking"
    if awaiting_slot and SLOT_VALIDATORS.get(awaiting_slot) and SLOT_VALIDATORS[awaiting_slot].search(t):
        return "ok", f"answers {awaiting_slot}"
    if DOMAIN.search(t):
        return "ok", "domain keyword"
    if INTERRUPT_WORDS.search(t) and len(words) <= 3:
        return "ok", "interrupt word"
    if len(words) <= 2 and (t.lower().strip(".!? ,") in SHORT_REAL):
        return "ok", "short real reply"
    if awaiting_slot == "name" and extract_name(t, awaiting_name=True):
        return "ok", "looks like a name"
    if t.endswith("?") and len(words) >= 3:
        return "ok", "question"
    return "unclear", "no slot answer, no domain keyword"


# --------------------------------------------------------------------------- self-tests
if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ok = True

    def check(label, got, want):
        global ok
        good = got == want
        ok &= good
        print(("PASS " if good else "FAIL ") + label + f"  -> {got!r}" + ("" if good else f"  (wanted {want!r})"))

    # names (TEST_128: "This is the final rule." overwrote "Yash" with "the final")
    check("name: 'This is the final rule.'", extract_name("This is the final rule."), None)
    check("name: same, while asking name", extract_name("This is the final rule.", True), None)
    check("name: 'My name is Yash'", extract_name("My name is Yash"), "Yash")
    check("name: bare 'Aditya Kumar.' asking", extract_name("Aditya Kumar.", True), "Aditya Kumar")
    check("name: 'P.Tech.' asking", extract_name("P.Tech.", True), None)
    check("name: bare 'Karthik.' not asking", extract_name("Karthik."), None)

    # farewell (TEST_128: a Hindi sentence with 'बस' ended the call)
    check("bye: Hindi chatter with 'बस'", is_farewell("ये जो बस करते हुए होता है।"), False)
    check("bye: 'Okay thank you, that's all'", is_farewell("Okay thank you, that's all"), True)
    check("bye: 'bye'", is_farewell("bye"), True)
    check("bye: 'बस इतना ही, धन्यवाद'", is_farewell("बस इतना ही, धन्यवाद"), True)
    check("bye: lone 'ok thanks'", is_farewell("ok thanks"), False)

    # classification (TEST_128 transcripts)
    check("cls: Bengali script", classify_transcript("বলताও ঠিক আছে।")[0], "drop")
    check("cls: 'This is the final rule.'", classify_transcript("This is the final rule.")[0], "unclear")
    check("cls: Hindi chatter", classify_transcript("हम लोग इतना नहीं है, हम लोग नहीं चाले।")[0], "unclear")
    check("cls: Hindi chatter 2", classify_transcript("ये जो बस करते हुए होता है।")[0], "unclear")
    check("cls: 'What are the fee structure?'", classify_transcript("What are the fee structure?")[0], "ok")
    check("cls: percentage answer", classify_transcript("Eighty eight percent.", awaiting_slot="percentage")[0], "ok")
    check("cls: 'Yes.' after yes/no", classify_transcript("Yes.", awaiting_slot="yesno")[0], "ok")
    check("cls: 2 words while agent speaking", classify_transcript("ये जो", agent_speaking=True)[0], "drop")
    check("cls: 'wait' while agent speaking", classify_transcript("wait", agent_speaking=True)[0], "ok")
    check("cls: name answer", classify_transcript("Aditya Kumar.", awaiting_slot="name")[0], "ok")
    print("\nALL PASSED" if ok else "\nSOME FAILED")
