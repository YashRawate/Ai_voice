"""
direct_sarvam_tts.py — Direct Streaming Text-To-Speech client for Sarvam Bulbul:v3.

Connects directly to wss://api.sarvam.ai/text-to-speech/ws with instant REST fallback.
Yields raw audio chunks (8kHz mu-law for telephony or 16kHz PCM/WAV for browser)
with sub-250ms time-to-first-byte audio synthesis.
"""

import os
import json
import base64
import asyncio
import logging
from typing import Optional, AsyncGenerator, Dict, Any
import aiohttp

logger = logging.getLogger("priya.direct_tts")
SARVAM_TTS_WS_URL = "wss://api.sarvam.ai/text-to-speech/ws"
SARVAM_TTS_REST_URL = "https://api.sarvam.ai/text-to-speech"


class DirectSarvamTTS:
    """
    Direct Sarvam TTS synthesizer supporting WebSocket streaming and REST fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        speaker: str = "shreya",
        language_code: str = "en-IN",
        pace: float = 1.12,
        sample_rate: int = 8000,
        output_audio_codec: str = "mulaw",  # "mulaw" for telephony, "wav" for web
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self.speaker = speaker
        self.language_code = language_code
        self.pace = pace
        self.sample_rate = sample_rate
        self.output_audio_codec = output_audio_codec
        self._session: Optional[aiohttp.ClientSession] = None
        self._is_cancelled = False

    def cancel(self):
        """Signal ongoing synthesis to abort (barge-in)."""
        self._is_cancelled = True

    def reset_cancellation(self):
        self._is_cancelled = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def synthesize_stream(
        self,
        text: str,
        language: Optional[str] = None,
    ) -> AsyncGenerator[bytes, None]:
        """
        Synthesize text and yield raw audio bytes.
        Attempts low-latency WebSocket connection first; falls back cleanly to REST.
        """
        if not text or not text.strip():
            return

        self.reset_cancellation()
        lang = language or self.language_code
        session = await self._get_session()
        headers = {
            "API-SUBSCRIPTION-KEY": self.api_key,
            "User-Agent": "Priya-Direct-TTS/1.0",
        }

        # ── 1. Realtime WebSocket Streaming Path ──────────────────────────────
        ws = None
        try:
            ws = await session.ws_connect(SARVAM_TTS_WS_URL, headers=headers, timeout=2.5)
            # Send config
            config_msg = {
                "type": "config",
                "data": {
                    "target_language_code": lang,
                    "speaker": self.speaker,
                    "pace": self.pace,
                    "speech_sample_rate": self.sample_rate,
                    "output_audio_codec": self.output_audio_codec,
                    "enable_cached_responses": True,
                },
            }
            await ws.send_str(json.dumps(config_msg))

            # Send text
            await ws.send_str(json.dumps({"type": "text", "data": {"text": text.strip()}}))
            await ws.send_str(json.dumps({"type": "flush"}))

            # Receive audio chunks
            async for msg in ws:
                if self._is_cancelled:
                    logger.debug("TTS synthesis cancelled by barge-in")
                    break
                if msg.type == aiohttp.WSMsgType.TEXT:
                    resp = json.loads(msg.data)
                    msg_type = resp.get("type")
                    if msg_type == "audio":
                        raw_b64 = resp.get("data", {}).get("audio", "")
                        if raw_b64:
                            yield base64.b64decode(raw_b64)
                    elif msg_type == "done" or msg_type == "flush":
                        break
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
            return
        except Exception as e:
            logger.debug(f"TTS WebSocket streaming unavailable ({e}); falling back to REST")
        finally:
            if ws and not ws.closed:
                await ws.close()

        # ── 2. High-Speed REST Fallback Path ──────────────────────────────────
        if self._is_cancelled:
            return

        try:
            payload = {
                "inputs": [text.strip()],
                "target_language_code": lang,
                "speaker": self.speaker,
                "model": "bulbul:v3",
                "pace": self.pace,
                "speech_sample_rate": self.sample_rate,
                "output_audio_codec": self.output_audio_codec,
                "enable_cached_responses": True,
            }
            async with session.post(
                SARVAM_TTS_REST_URL,
                headers={"api-subscription-key": self.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=5.0,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    audios = data.get("audios", [])
                    if audios and not self._is_cancelled:
                        yield base64.b64decode(audios[0])
                else:
                    err_txt = await resp.text()
                    logger.warning(f"Sarvam REST TTS error {resp.status}: {err_txt}")
        except Exception as ex:
            logger.error(f"Sarvam REST TTS failed: {ex}")

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
