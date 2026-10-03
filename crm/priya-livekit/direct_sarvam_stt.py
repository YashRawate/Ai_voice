"""
direct_sarvam_stt.py — Direct WebSocket client for Sarvam Realtime STT (saaras:v3).

Eliminates SFU and LiveKit Cloud proxy hops for sub-second Indian language transcription.
Connects directly to wss://api.sarvam.ai/speech-to-text-realtime/ws.
"""

import os
import json
import asyncio
import logging
from urllib.parse import urlencode
from typing import Optional, Callable, Dict, Any, Coroutine
import aiohttp

logger = logging.getLogger("priya.direct_stt")
SARVAM_STT_WS_URL = "wss://api.sarvam.ai/speech-to-text-realtime/ws"


class DirectSarvamSTT:
    """
    Direct client streaming audio to Sarvam Realtime STT WebSocket.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        language_code: str = "en-IN",
        sample_rate: int = 8000,
        encoding: str = "pcm",  # "pcm" or "mulaw"
        model: str = "saaras:v3",
        endpointing: str = "vad",
        prompt: Optional[str] = None,
        on_partial: Optional[Callable[[str, str], Coroutine[Any, Any, None]]] = None,
        on_final: Optional[Callable[[str, str], Coroutine[Any, Any, None]]] = None,
        on_speech_start: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
        on_speech_end: Optional[Callable[[], Coroutine[Any, Any, None]]] = None,
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self.language_code = language_code
        self.sample_rate = sample_rate
        self.encoding = encoding
        self.model = model
        self.endpointing = endpointing
        self.prompt = prompt or (
            "Aditya University admissions counsellor Priya student Telugu Hindi English "
            "B.Tech CSE ECE EEE Mechanical Civil MBA MCA ASAT JEE EAPCET fees placements "
            "scholarships hostel campus"
        )
        self.on_partial = on_partial
        self.on_final = on_final
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end

        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._is_connected = False
        self._closed = False

    def _build_ws_url(self) -> str:
        params: Dict[str, str] = {
            "language_code": self.language_code if self.language_code != "unknown" else "auto",
            "stream_type": "fast",
            "model": "saaras:v4",
            "encoding": self.encoding if self.encoding in ("linear16", "mulaw") else "linear16",
            "sample_rate": str(self.sample_rate),
            "mode": "transcribe",
            "turn_detection": "vad",
            "return_timestamps": "false",
        }
        if self.prompt:
            params["prompt"] = self.prompt

        return f"{SARVAM_STT_WS_URL}?{urlencode(params)}"

    async def connect(self) -> bool:
        """Open the persistent realtime STT WebSocket."""
        if not self.api_key:
            logger.warning("SARVAM_API_KEY missing — DirectSarvamSTT cannot connect")
            return False

        if self._is_connected and self._ws and not self._ws.closed:
            return True

        self._session = aiohttp.ClientSession()
        url = self._build_ws_url()
        headers = {
            "API-SUBSCRIPTION-KEY": self.api_key,
            "User-Agent": "Priya-Direct-STT/1.0",
        }

        try:
            self._ws = await self._session.ws_connect(url, headers=headers, heartbeat=25.0)
            self._is_connected = True
            self._closed = False
            self._listen_task = asyncio.create_task(self._listen_loop())
            logger.info("Direct Sarvam STT WebSocket connected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Sarvam STT WebSocket: {e}")
            self._is_connected = False
            return False

    async def send_audio(self, audio_bytes: bytes):
        """Send raw audio frames (PCM16 or mulaw depending on encoding)."""
        if not self._is_connected or not self._ws or self._ws.closed:
            return
        try:
            await self._ws.send_bytes(audio_bytes)
        except Exception as e:
            logger.debug(f"Error sending audio to Sarvam STT: {e}")

    async def _listen_loop(self):
        """Read incoming JSON transcript and VAD events from Sarvam."""
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_event(data)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"STT listen loop error: {e}")
        finally:
            self._is_connected = False

    async def _handle_event(self, data: Dict[str, Any]):
        event = data.get("event") or data.get("type", "")
        logger.debug(f"Sarvam STT event: {event} | {data}")

        if event in ("vad.speech_start", "speech_start"):
            logger.info("Sarvam STT: user speech detected (speech_start)")
            if self.on_speech_start:
                await self.on_speech_start()
        elif event in ("vad.speech_end", "speech_end"):
            logger.info("Sarvam STT: user speech ended (speech_end)")
            if self.on_speech_end:
                await self.on_speech_end()
        elif "partial" in event:
            text = (data.get("text") or data.get("transcript") or data.get("data", {}).get("text") or data.get("data", {}).get("transcript") or "").strip()
            lang = data.get("language_code") or data.get("language") or data.get("data", {}).get("language_code") or self.language_code
            if text and self.on_partial:
                await self.on_partial(text, lang)
        elif "final" in event or event == "transcript":
            text = (data.get("text") or data.get("transcript") or data.get("data", {}).get("text") or data.get("data", {}).get("transcript") or "").strip()
            lang = data.get("language_code") or data.get("language") or data.get("data", {}).get("language_code") or self.language_code
            if text and self.on_final:
                logger.info(f"Sarvam STT finalized utterance: '{text}' (lang={lang})")
                await self.on_final(text, lang)

    async def close(self):
        """Cleanly close the WebSocket and HTTP session."""
        self._closed = True
        self._is_connected = False
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()
        logger.debug("Direct Sarvam STT closed")
