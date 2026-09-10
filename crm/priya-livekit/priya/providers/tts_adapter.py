# crm/priya-livekit/priya/providers/tts_adapter.py
"""
Multi-Provider Streaming TTS Adapter for AdmitAI Priya Voice Agent.
Primary: Sarvam Bulbul v3
Fallback: EdgeTTS Streaming Neural Voice (Zero-Cost, Supports en-IN, hi-IN, te-IN, ta-IN)
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import time
from typing import AsyncIterator, Optional

logger = logging.getLogger("priya.tts_adapter")

EDGE_VOICES = {
    "en-IN": "en-IN-NeerjaNeural",
    "hi-IN": "hi-IN-SwaraNeural",
    "te-IN": "te-IN-ShrutiNeural",
    "ta-IN": "ta-IN-PallaviNeural",
}


class StreamingTTSAdapter:
    """
    Manages speech synthesis with instant automatic fallback when cloud credits expire.
    """

    def __init__(
        self,
        primary_provider: str = "sarvam",
        default_language: str = "en-IN",
        sarvam_api_key: Optional[str] = None,
    ):
        self.primary_provider = primary_provider
        self.default_language = default_language
        self.sarvam_api_key = sarvam_api_key or os.getenv("SARVAM_API_KEY", "")
        self.is_sarvam_exhausted = False

    async def synthesize_stream(
        self,
        text: str,
        language_code: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """
        Synthesizes text into audio chunks (mp3/pcm).
        Automatically falls back to EdgeTTS if Sarvam returns credit exhaustion (402/1003).
        """
        lang = language_code or self.default_language
        clean_text = text.strip()
        if not clean_text:
            return

        # Try Sarvam if active and not marked exhausted
        if self.primary_provider == "sarvam" and not self.is_sarvam_exhausted and self.sarvam_api_key:
            try:
                # If using livekit plugins or direct sarvam
                from direct_sarvam_tts import synthesize_sarvam_tts
                t0 = time.perf_counter()
                audio_data = await synthesize_sarvam_tts(clean_text, target_language=lang)
                if audio_data:
                    dt = (time.perf_counter() - t0) * 1000
                    logger.debug(f"[TTS:Sarvam] Synthesized in {dt:.1f}ms")
                    yield audio_data
                    return
            except Exception as e:
                err_msg = str(e).lower()
                if "credits exhausted" in err_msg or "402" in err_msg or "1003" in err_msg:
                    logger.warning("[TTS] Sarvam credits exhausted! Automatically switching to EdgeTTS fallback permanently for this session.")
                    self.is_sarvam_exhausted = True
                else:
                    logger.warning(f"[TTS] Sarvam TTS error: {e}. Falling back to EdgeTTS.")

        # Fallback: EdgeTTS streaming neural voice
        async for chunk in self._synthesize_edge_tts(clean_text, lang):
            yield chunk

    async def _synthesize_edge_tts(self, text: str, language_code: str) -> AsyncIterator[bytes]:
        """Synthesizes text using Microsoft Edge Neural TTS."""
        import edge_tts

        voice = EDGE_VOICES.get(language_code, EDGE_VOICES["en-IN"])
        logger.info(f"[TTS:EdgeTTS] Synthesizing with voice {voice} for '{text[:40]}...'")

        try:
            communicate = edge_tts.Communicate(text, voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error(f"[TTS:EdgeTTS] Synthesis failed: {e}")
            # Final fallback: Try English voice if regional voice failed
            if voice != EDGE_VOICES["en-IN"]:
                try:
                    fallback_comm = edge_tts.Communicate(text, EDGE_VOICES["en-IN"])
                    async for chunk in fallback_comm.stream():
                        if chunk["type"] == "audio":
                            yield chunk["data"]
                except Exception as ex2:
                    logger.error(f"[TTS:EdgeTTS] Fallback voice failed: {ex2}")
