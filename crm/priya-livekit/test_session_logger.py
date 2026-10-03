# crm/priya-livekit/test_session_logger.py
"""
test_session_logger.py
Console/dev-testing diagnostics for AdmitAI Priya Voice Agent.
Saves every test run inside 'crm/YASH_TEST/' sequentially as TEST_1, TEST_2, ..., TEST_N.
"""

import os
import re
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class TestSessionLogger:
    """
    Diagnostics recorder saving each test run to crm/YASH_TEST/ as TEST_1.md, TEST_2.md, ..., TEST_N.md.
    """

    def __init__(
        self,
        session_id: str,
        base_dir: Optional[str] = None,
        console: bool = True,
        test_index: Optional[int] = None
    ):
        self.session_id = session_id
        self.console = console

        # Resolve directory to 'crm/YASH_TEST'
        if base_dir is None:
            current_dir = Path(__file__).resolve().parent  # crm/priya-livekit
            crm_dir = current_dir.parent if current_dir.name == "priya-livekit" else current_dir
            self.base_dir = crm_dir / "YASH_TEST"
        else:
            self.base_dir = Path(base_dir).resolve()

        os.makedirs(self.base_dir, exist_ok=True)

        # Auto-compute next sequential test index: TEST_1, TEST_2, ... TEST_N
        if test_index is not None:
            self.test_number = test_index
        else:
            self.test_number = self._get_next_test_number()

        self.test_id = f"TEST_{self.test_number}"

        # Markdown file path: crm/YASH_TEST/TEST_N.md
        self.log_file = os.path.join(str(self.base_dir), f"{self.test_id}.md")
        
        # Dedicated test folder: crm/YASH_TEST/TEST_N/
        self.test_folder = os.path.join(str(self.base_dir), self.test_id)
        os.makedirs(self.test_folder, exist_ok=True)
        self.folder_log_file = os.path.join(self.test_folder, f"{self.test_id}.md")
        self.transcript_json_path = os.path.join(self.test_folder, "transcript.json")
        self.events_json_path = os.path.join(self.test_folder, "events.json")

        self.start_time = time.time()
        self.turn_count = 0
        self.caller_turns_count = 0
        self.spoken_replies_count = 0
        self.event_counts = {
            "interruption": 0,
            "session_init": 0,
            "language_switch": 0,
            "reconnect": 0,
            "error": 0,
        }
        self.is_finalized = False
        self.transcript: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []

        _ACTIVE_LOGGERS[self.session_id] = self

        self._start_section()

    # ---------- internal helpers ----------

    @staticmethod
    def _mask_phone_number(text: str) -> str:
        """Mask 10-digit or +91 phone numbers for privacy."""
        if not text:
            return text
        def _repl(m):
            s = m.group(0)
            if len(s) >= 10:
                return s[:3] + "****" + s[-4:]
            return s
        return re.sub(r'(\+?91[\-\s]?)?[6-9]\d{9}', _repl, str(text))

    def _get_next_test_number(self) -> int:
        """Scan base_dir for existing TEST_N files or folders and determine the next number."""
        max_n = 0
        try:
            for item in os.listdir(self.base_dir):
                m = re.match(r'^TEST_(\d+)(?:\.md)?$', item, re.IGNORECASE)
                if m:
                    n = int(m.group(1))
                    if n > max_n:
                        max_n = n
        except Exception:
            pass
        return max_n + 1

    def _elapsed(self) -> float:
        return round(time.time() - self.start_time, 3)

    def _append(self, text: str):
        masked_text = self._mask_phone_number(text)
        # Write to crm/YASH_TEST/TEST_N.md
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(masked_text + "\n")
        # Write copy to crm/YASH_TEST/TEST_N/TEST_N.md
        with open(self.folder_log_file, "a", encoding="utf-8") as f:
            f.write(masked_text + "\n")

        if self.console:
            try:
                print(text)
            except UnicodeEncodeError:
                import sys
                enc = sys.stdout.encoding or "utf-8"
                print(text.encode(enc, errors="replace").decode(enc))

    def _start_section(self):
        header = (
            f"# {self.test_id}\n\n"
            f"- **Session ID:** {self.session_id}\n"
            f"- **Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"### Conversation & Events\n"
        )
        self._append(header)

    # ---------- public logging methods ----------

    def log_stt(
        self,
        text: str,
        language: Optional[str] = None,
        confidence: Optional[float] = None,
        raw_audio_snr: Optional[float] = None
    ):
        self.turn_count += 1
        self.caller_turns_count += 1
        entry = {
            "type": "stt",
            "t": self._elapsed(),
            "text": text,
            "language": language,
            "confidence": confidence,
            "snr": raw_audio_snr,
        }
        self.transcript.append(entry)
        line = (f"- `[{self._elapsed():>7.3f}s]` 🎤 **Caller said** "
                f"({language or 'unknown'}, conf={confidence}, snr={raw_audio_snr}): \"{text}\"")
        self._append(line)

    def log_llm_reply(
        self,
        text: str,
        stage: Optional[str] = None,
        facts_snapshot: Optional[Dict[str, Any]] = None
    ):
        self.spoken_replies_count += 1
        entry = {
            "type": "llm_reply",
            "t": self._elapsed(),
            "text": text,
            "stage": stage,
            "facts_snapshot": dict(facts_snapshot) if facts_snapshot else None,
        }
        self.transcript.append(entry)
        line = f"- `[{self._elapsed():>7.3f}s]` 🤖 **Priya replied** (stage={stage or 'GENERAL'}): \"{text}\""
        if facts_snapshot is not None:
            line += f"\n  - facts: `{facts_snapshot}`"
        self._append(line)

    def log_interruption(self, reason: str, detail: str = "", exc: Optional[Exception] = None):
        self.event_counts["interruption"] += 1
        entry = {
            "type": "interruption",
            "t": self._elapsed(),
            "reason": reason,
            "detail": detail,
            "traceback": traceback.format_exc() if exc else None,
        }
        self.events.append(entry)
        line = f"- `[{self._elapsed():>7.3f}s]` ⚠️ **Interruption** — reason=`{reason}`, detail: {detail}"
        self._append(line)
        if exc:
            self._append(f"  - traceback:\n```\n{traceback.format_exc()}\n```")

    def log_session_init(self, reason: str, is_first_call: Optional[bool] = None):
        self.event_counts["session_init"] += 1
        entry = {
            "type": "session_init",
            "t": self._elapsed(),
            "reason": reason,
            "is_first_call": is_first_call,
            "call_stack": traceback.format_stack(),
        }
        self.events.append(entry)
        flag = " 🚨 **UNEXPECTED MID-CALL RE-INIT — LIKELY BUG**" if is_first_call is False else ""
        line = f"- `[{self._elapsed():>7.3f}s]` 🔄 **Session init** — reason=`{reason}`{flag}"
        self._append(line)

    def log_language_switch(self, old_lang: str, new_lang: str, confidence: Optional[float] = None):
        self.event_counts["language_switch"] += 1
        entry = {
            "type": "language_switch",
            "t": self._elapsed(),
            "from": old_lang,
            "to": new_lang,
            "confidence": confidence,
        }
        self.events.append(entry)
        line = f"- `[{self._elapsed():>7.3f}s]` 🌐 **Language switch** {old_lang} → {new_lang} (conf={confidence})"
        self._append(line)

    def log_reconnect(self, transport: str, reason: str = ""):
        self.event_counts["reconnect"] += 1
        entry = {"type": "reconnect", "t": self._elapsed(), "transport": transport, "reason": reason}
        self.events.append(entry)
        line = f"- `[{self._elapsed():>7.3f}s]` 🔌 **Reconnect** — transport=`{transport}`, reason: {reason}"
        self._append(line)

    def log_error(self, message: str, exc: Optional[Exception] = None):
        self.event_counts["error"] += 1
        entry = {
            "type": "error",
            "t": self._elapsed(),
            "message": message,
            "traceback": traceback.format_exc() if exc else None,
        }
        self.events.append(entry)
        line = f"- `[{self._elapsed():>7.3f}s]` ❌ **Error** — {message}"
        self._append(line)
        if exc:
            self._append(f"  - traceback:\n```\n{traceback.format_exc()}\n```")

    # ---------- finalize ----------

    def finalize(self, disposition: str = "completed", notes: str = "") -> str:
        if self.is_finalized:
            return self.log_file
        self.is_finalized = True

        duration = self._elapsed()
        reinit_flag = "✅ OK" if self.event_counts["session_init"] == 1 else "🚨 CHECK — expected exactly 1"

        turns_without_reply = max(0, self.caller_turns_count - self.spoken_replies_count)
        if turns_without_reply > 0:
            self.event_counts["error"] += turns_without_reply
            if disposition == "completed":
                disposition = "degraded" if self.spoken_replies_count > 0 else "failed"

        summary = f"""
### Summary — {self.test_id}

| Metric | Value |
|---|---|
| Duration | {duration}s |
| Disposition | {disposition} |
| Turns | {self.turn_count} |
| Turns without reply | {turns_without_reply} |
| Spoken replies | {self.spoken_replies_count} |
| Interruptions | {self.event_counts['interruption']} |
| Session re-inits | {self.event_counts['session_init']} ({reinit_flag}) |
| Language switches | {self.event_counts['language_switch']} |
| Reconnects | {self.event_counts['reconnect']} |
| Errors | {self.event_counts['error']} |
| Notes | {notes} |
| File Path | {self.log_file} |
"""
        self._append(summary)

        # Save structured JSON artifacts inside crm/YASH_TEST/TEST_N/
        try:
            with open(self.transcript_json_path, "w", encoding="utf-8") as f:
                json.dump(self.transcript, f, ensure_ascii=False, indent=2)
            with open(self.events_json_path, "w", encoding="utf-8") as f:
                json.dump(self.events, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        if self.console:
            try:
                print(f"\n=== {self.test_id} finalized ({duration}s) -> saved to crm/YASH_TEST/{self.test_id}.md ===\n")
            except UnicodeEncodeError:
                pass

        return self.log_file


# Singleton / registry for accessing current active logger across modules
_ACTIVE_LOGGERS: Dict[str, TestSessionLogger] = {}


def get_or_create_logger(session_id: str, base_dir: Optional[str] = None) -> TestSessionLogger:
    """Retrieve existing logger for session or create new one."""
    if session_id not in _ACTIVE_LOGGERS:
        _ACTIVE_LOGGERS[session_id] = TestSessionLogger(session_id=session_id, base_dir=base_dir)
    return _ACTIVE_LOGGERS[session_id]
