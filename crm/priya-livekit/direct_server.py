"""
direct_server.py — Self-Hosted Direct Raw Audio Pipeline Server for Priya.

Replaces LiveKit Cloud (SFU, SIP bridge, room orchestration) with a direct,
in-process 1:1 audio pipe for telephony (Twilio/Exotel/Plivo) and browser clients.
Achieves <500ms voice-to-voice turn latency.

Run:
    python direct_server.py                  # starts FastAPI on port 8000
    python direct_server.py --port 8080      # custom port
"""

import os
import re
import json
import time
import base64
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from openai import AzureOpenAI, OpenAI

import university_data as udata
from reporter import Reporter
from latency import LatencyTracker
from long_conversation import LongConversationManager, is_goodbye, detect_conversion_intent, detect_objection
from direct_audio_codec import mulaw_to_pcm16, pcm16_to_mulaw, calculate_rms_energy
from direct_sarvam_stt import DirectSarvamSTT
from direct_sarvam_tts import DirectSarvamTTS
from agent import PatternRouter, _normalize_numbers_for_speech, INSTRUCTIONS
from test_session_logger import TestSessionLogger, get_or_create_logger

load_dotenv()
logger = logging.getLogger("priya.direct_server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(title="Priya Direct Audio Pipeline Server", version="2.0.0")

# ── Global Configuration ──────────────────────────────────────────────────────
PORT = int(os.getenv("DIRECT_SERVER_PORT", "8000"))
HOST = os.getenv("DIRECT_SERVER_HOST", "0.0.0.0")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "azure").lower().strip()
SARVAM_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_SPEAKER = os.getenv("SARVAM_SPEAKER", "shreya")
TTS_PACE = float(os.getenv("TTS_PACE", "1.12"))
DEFAULT_LANG = os.getenv("DEFAULT_LANGUAGE", "en-IN")
USE_LANGGRAPH = os.getenv("USE_LANGGRAPH", "true").lower() == "true"

# ── LangGraph Pipeline Initialization ─────────────────────────────────────────
_LANGGRAPH_APP = None
try:
    from graph import build_call_graph
    from llm_failover import build_langchain_llm
    _LANGGRAPH_LLM = build_langchain_llm()
    _LANGGRAPH_APP = build_call_graph(llm=_LANGGRAPH_LLM)
    logger.info("LangGraph pipeline successfully initialized for direct audio server")
except Exception as _ex:
    logger.warning(f"LangGraph initialization deferred or running in fallback: {_ex}")


def get_llm_client():
    """Build OpenAI / AzureOpenAI client based on .env."""
    if os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"):
        return "azure", AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            timeout=4.0,
        ), os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    elif os.getenv("GROQ_API_KEY"):
        return "groq", OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY", ""),
            timeout=4.0,
        ), os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    else:
        return "openai", OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "dummy"),
            timeout=4.0,
        ), "gpt-4o-mini"



# ── Active Call Session Context ───────────────────────────────────────────────
class DirectCallSession:
    """Manages a single 1:1 call lifecycle with direct raw audio."""

    def __init__(self, ws: WebSocket, stream_sid: str = "", call_sid: str = "", caller_number: str = "", meta: dict = None):
        self.ws = ws
        self.stream_sid = stream_sid
        self.call_sid = call_sid
        self.caller_number = caller_number
        self.meta = meta or {}

        self.session_id = self.meta.get("session_id") or f"direct_{stream_sid or int(time.time())}"
        self.test_logger = get_or_create_logger(self.session_id)
        self.test_logger.log_session_init(reason="direct_carrier_call_start", is_first_call=True)

        report_url = self.meta.get("report_url") or os.getenv("BACKEND_REPORT_URL", "")
        self.reporter = Reporter(report_url, self.session_id)
        self.reporter.start()

        self.long_mgr = LongConversationManager(call_id=self.session_id)
        self.active_language = DEFAULT_LANG
        self.student_name = self.meta.get("student_name") or ""

        # Direct audio clients
        self.stt: Optional[DirectSarvamSTT] = None
        self.tts = DirectSarvamTTS(
            api_key=SARVAM_KEY,
            speaker=SARVAM_SPEAKER,
            language_code=self.active_language,
            pace=TTS_PACE,
            sample_rate=8000,
            output_audio_codec="mulaw",
        )

        self.is_speaking = False
        self.current_tts_task: Optional[asyncio.Task] = None
        self.is_closed = False
        self.turn_queue = asyncio.Queue()
        self.process_turns_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Connect STT and initialize turn processor (Called EXACTLY ONCE on new call)."""
        logger.info(f"[{self.session_id}] [SESSION_INIT] Initializing new call session")
        self.stt = DirectSarvamSTT(
            api_key=SARVAM_KEY,
            language_code="unknown",  # auto-detect
            sample_rate=8000,
            encoding="mulaw",        # direct telephony mulaw streaming
            on_final=self._handle_stt_final,
            on_speech_start=self._handle_user_speech_start,
        )
        await self.stt.connect()
        self.process_turns_task = asyncio.create_task(self._turn_worker())

        # Speak warm initial admissions greeting (ONLY on first initialization)
        greeting = (
            f"Hello! I am Priya from Aditya University Admissions. Am I speaking with {self.student_name}?"
            if self.student_name
            else "Hello! This is Priya from Aditya University Admissions Office. May I know your name, please?"
        )
        await self.speak_phrase(greeting)

    async def reconnect_transport(self, ws: WebSocket, stream_sid: str):
        """
        Re-binds WebSocket transport after a mid-call network/noise drop.
        Preserves all facts, context, and conversation stage WITHOUT re-greeting.
        """
        logger.info(f"[{self.session_id}] [TRANSPORT_RECONNECT] Re-binding WebSocket streamSid={stream_sid}. Retaining facts.")
        self.ws = ws
        self.stream_sid = stream_sid
        self.test_logger.log_reconnect(transport="twilio_media_stream", reason="carrier_reconnect")
        if self.stt:
            try:
                await self.stt.connect()
            except Exception as e:
                logger.warning(f"[{self.session_id}] STT reconnect warning: {e}")
                self.test_logger.log_error(f"STT reconnect failed: {e}")

    async def _handle_user_speech_start(self):
        """Barge-in: caller started speaking while Priya is playing audio."""
        if self.is_speaking:
            logger.info(f"[{self.session_id}] Barge-in detected — interrupting Priya")
            self.test_logger.log_interruption(reason="caller_barge_in", detail="Caller spoke over TTS")
            await self.stop_speaking()

    async def _handle_stt_final(self, transcript: str, language_code: str):
        """User finished an utterance."""
        if not transcript.strip():
            return
        logger.info(f"[{self.session_id}] Caller ({language_code}): {transcript}")
        self.test_logger.log_stt(text=transcript, language=language_code)
        if language_code and language_code in {"te-IN", "hi-IN", "en-IN", "ta-IN"}:
            if language_code != self.active_language:
                self.test_logger.log_language_switch(old_lang=self.active_language, new_lang=language_code)
            self.active_language = language_code
        await self.turn_queue.put((transcript, language_code))

    async def stop_speaking(self):
        """Cancel ongoing TTS playback and flush carrier audio buffer."""
        self.is_speaking = False
        if self.current_tts_task and not self.current_tts_task.done():
            self.current_tts_task.cancel()
        self.tts.cancel()
        # Send Twilio clear event to empty carrier jitter buffer instantly
        if self.stream_sid:
            try:
                await self.ws.send_json({"event": "clear", "streamSid": self.stream_sid})
            except Exception:
                pass

    async def speak_phrase(self, text: str):
        """Synthesize text and stream raw mulaw frames to caller."""
        if not text or self.is_closed:
            return

        text = _normalize_numbers_for_speech(text, lang=self.active_language)
        self.is_speaking = True
        self.reporter.push_assistant_message(text)

        try:
            async for chunk in self.tts.synthesize_stream(text, language=self.active_language):
                if not self.is_speaking or self.is_closed:
                    break
                payload = base64.b64encode(chunk).decode("utf-8")
                await self.ws.send_json({
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": payload}
                })
                # Yield to event loop to keep latency tight
                await asyncio.sleep(0.001)
        except asyncio.CancelledError:
            logger.debug("Playback cancelled by interruption")
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            self.test_logger.log_error("TTS synthesis failed", exc=e)
        finally:
            self.is_speaking = False

    async def _turn_worker(self):
        """Background worker that pulls user utterances and triggers responses."""
        while not self.is_closed:
            try:
                transcript, lang = await self.turn_queue.get()
            except asyncio.CancelledError:
                break

            t0 = time.time()
            self.reporter.push_user_message(transcript)

            # 1. Update 4-layer memory facts
            self.long_mgr.update_user_turn(transcript, language=lang)
            collected = self.long_mgr.fact_memory.facts

            # 2. Check for Goodbye with Goodbye Guard
            if is_goodbye(transcript):
                farewell = (
                    "ధన్యవాదాలు! మీ అడ్మిషన్ వివరాలు మా వాట్సాప్ ద్వారా పంపిస్తాము. హావ్ ఏ గ్రేట్ డే!"
                    if lang == "te-IN"
                    else "धन्यवाद! हम आपके एडमिशन की जानकारी व्हाट्सएप पर भेज देंगे। आपका दिन शुभ हो!"
                    if lang == "hi-IN"
                    else "Thank you for contacting Aditya University! We have sent the admission details to your number. Have a great day!"
                )
                self.test_logger.log_llm_reply(text=farewell, stage="GOODBYE", facts_snapshot=collected)
                await self.speak_phrase(farewell)
                await asyncio.sleep(1.0)
                await self.close()
                break

            # 3. Check for admissions objections or conversion actions
            intent = detect_conversion_intent(transcript)
            objection = detect_objection(transcript)

            if intent == "book_campus_visit":
                self.long_mgr.record_fact("engagement_choice", "campus_visit")
                self.long_mgr.record_fact("visit_datetime", "Saturday 10:00 AM")
                self.reporter.push_detail("visit_datetime", "Saturday 10:00 AM")
                reply = (
                    "పర్ఫెక్ట్ అండి! ఈ శనివారం ఉదయం 10 గంటలకు మీ క్యాంపస్ విజిట్ కన్ఫర్మ్ చేశాము. "
                    "మీ తల్లిదండ్రులతో కలిసి రండి, ల్యాబ్స్ మరియు ఫెసిలిటీస్ చూపిస్తాము. మీకు లొకేషన్ లింక్ వాట్సాప్ చేయనా?"
                    if lang == "te-IN"
                    else "Perfect! We have scheduled your VIP campus visit for this Saturday at 10:00 AM. "
                    "Please bring your parents along. Shall I send the campus map on WhatsApp?"
                )
                self.test_logger.log_llm_reply(text=reply, stage="CONVERT", facts_snapshot=collected)
                await self.speak_phrase(reply)
                continue
            elif intent == "send_application_link":
                self.long_mgr.record_fact("engagement_choice", "application_link")
                self.long_mgr.record_fact("call_outcome", "interested")
                self.reporter.push_detail("call_outcome", "interested")
                reply = (
                    "తప్పకుండా అండి! ఆదిత్య యూనివర్సిటీ ప్రొవిజనల్ అడ్మిషన్ అప్లికేషన్ లింక్ మీ వాట్సాప్ నంబర్‌కు పంపించాము. "
                    "ఫారమ్ పూర్తి చేసి సీటు రిజర్వ్ చేసుకోండి. ఇంకేమైనా సందేహాలు ఉన్నాయా?"
                    if lang == "te-IN"
                    else "Certainly! I have dispatched your priority provisional admission link to your WhatsApp number. "
                    "Would you like any assistance with scholarship details?"
                )
                self.test_logger.log_llm_reply(text=reply, stage="CONVERT", facts_snapshot=collected)
                await self.speak_phrase(reply)
                continue

            # 4. Fast-Path Pattern Router (Sub-50ms cache)
            cached_response = PatternRouter.match(transcript, collected, lang=lang)
            if cached_response:
                elapsed_ms = (time.time() - t0) * 1000
                logger.info(f"[{self.session_id}] [FAST-PATH] Hit in {elapsed_ms:.1f}ms: {cached_response[:40]}...")
                self.long_mgr.update_agent_turn(cached_response, language=lang)
                self.test_logger.log_llm_reply(text=cached_response, stage="FAST_PATH", facts_snapshot=collected)
                await self.speak_phrase(cached_response)
                continue

            # 5. LLM Consultative Closer Generation
            reply = await self._generate_llm_response(transcript, lang)
            self.long_mgr.update_agent_turn(reply, language=lang)
            self.test_logger.log_llm_reply(text=reply, stage="CONSULT", facts_snapshot=collected)
            await self.speak_phrase(reply)

    async def _generate_llm_response(self, user_text: str, lang: str) -> str:
        """Call LLM with dynamic conversion directives or LangGraph state machine."""
        if USE_LANGGRAPH and _LANGGRAPH_APP is not None:
            try:
                config = {"configurable": {"thread_id": self.session_id}}
                graph_input = {
                    "session_id": self.session_id,
                    "last_user_text": user_text,
                    "language_code": lang,
                    "facts": dict(self.long_mgr.fact_memory.facts),
                    "stage": "GREETING",
                    "next_field": "student_name",
                }
                res = _LANGGRAPH_APP.invoke(graph_input, config=config)
                if "facts" in res:
                    for k, v in res["facts"].items():
                        self.long_mgr.record_fact(k, v)
                ai_msg = res["messages"][-1]
                content = getattr(ai_msg, "content", str(ai_msg)).strip()
                content = content.replace("*", "").replace("#", "").strip()
                if content:
                    return content
            except Exception as e:
                logger.warning(f"LangGraph execution exception, falling back to direct LLM: {e}")

        prov, client, model_name = get_llm_client()
        directives = self.long_mgr.build_turn_prompt(user_text, language=lang)

        system_prompt = f"{INSTRUCTIONS}\n\n# REALTIME DIRECTIVES FOR THIS TURN:\n{directives}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]

        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=60,
                temperature=0.6,
            )
            content = resp.choices[0].message.content.strip()
            # Clean up markdown / quotes
            content = content.replace("*", "").replace("#", "").strip()
            return content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            self.test_logger.log_error("LLM generation exception", exc=e)
            return "Aditya University offers excellent B.Tech programs with up to 50% merit scholarships. Would you like me to share our admission link on WhatsApp?"

    async def close(self):
        """Terminate call session."""
        if self.is_closed:
            return
        self.is_closed = True
        if self.process_turns_task:
            self.process_turns_task.cancel()
        if self.stt:
            await self.stt.close()
        await self.tts.close()
        self.reporter.finish()
        self.test_logger.finalize(disposition="completed", notes="Direct carrier session concluded")
        logger.info(f"[{self.session_id}] Call session ended")


ACTIVE_DIRECT_SESSIONS: Dict[str, "DirectCallSession"] = {}


# ── Webhook & WebSocket Endpoints ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "priya_direct_pipeline",
        "provider": LLM_PROVIDER,
        "mode": "1:1 raw audio stream",
        "livekit_bypassed": True,
    }


@app.api_route("/twiml", methods=["GET", "POST"])
async def twiml_response(request: Request):
    """Returns TwiML instructing Twilio to stream raw audio to our WebSocket."""
    host = request.headers.get("host", f"localhost:{PORT}")
    ws_protocol = "wss" if request.url.scheme == "https" or "ngrok" in host else "ws"
    stream_url = f"{ws_protocol}://{host}/media-stream"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{stream_url}">
            <Parameter name="agent" value="priya" />
        </Stream>
    </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(ws: WebSocket):
    """
    Twilio / Exotel / Plivo raw bidirectional media stream WebSocket.
    """
    await ws.accept()
    session: Optional[DirectCallSession] = None
    stream_sid = ""
    call_sid = ""

    try:
        async for message in ws.iter_json():
            event = message.get("event")

            if event == "start":
                start_data = message.get("start", {})
                stream_sid = message.get("streamSid", "")
                call_sid = start_data.get("callSid", "")
                custom_params = start_data.get("customParameters", {})
                logger.info(f"Call event 'start': callSid={call_sid}, streamSid={stream_sid}")

                # Check if this call already has an active session (transport reconnect)
                lookup_key = call_sid or custom_params.get("session_id") or stream_sid
                if lookup_key in ACTIVE_DIRECT_SESSIONS and not ACTIVE_DIRECT_SESSIONS[lookup_key].is_closed:
                    session = ACTIVE_DIRECT_SESSIONS[lookup_key]
                    logger.info(f"[{session.session_id}] Existing call reconnected — bypassing session initialization & greeting")
                    await session.reconnect_transport(ws, stream_sid)
                else:
                    session = DirectCallSession(
                        ws=ws,
                        stream_sid=stream_sid,
                        call_sid=call_sid,
                        meta=custom_params,
                    )
                    ACTIVE_DIRECT_SESSIONS[lookup_key] = session
                    await session.initialize()

            elif event == "media":
                if not session or session.is_closed:
                    continue
                media_payload = message.get("media", {}).get("payload", "")
                if media_payload:
                    mulaw_chunk = base64.b64decode(media_payload)
                    # Forward telephony mulaw bytes straight to Sarvam STT
                    if session.stt:
                        await session.stt.send_audio(mulaw_chunk)

            elif event == "stop":
                logger.info(f"Carrier sent stop event for stream {stream_sid}")
                if session:
                    lookup_key = call_sid or session.session_id or stream_sid
                    ACTIVE_DIRECT_SESSIONS.pop(lookup_key, None)
                    await session.close()
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {stream_sid}")
    except Exception as e:
        logger.error(f"Error in media_stream loop: {e}")
    finally:
        if session:
            await session.close()


if __name__ == "__main__":
    print("=" * 65)
    print(f"  STARTING PRIYA DIRECT AUDIO PIPELINE SERVER (Port {PORT})")
    print(f"  Bypassing LiveKit Cloud -> Direct 1:1 In-Process Media Stream")
    print("=" * 65)
    uvicorn.run(app, host=HOST, port=PORT)
