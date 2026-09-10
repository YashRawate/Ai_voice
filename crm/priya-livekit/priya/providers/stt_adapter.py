# crm/priya-livekit/priya/providers/stt_adapter.py
"""
Multi-Provider STT Adapter for AdmitAI Priya Voice Agent.
Primary: Sarvam Streaming STT (saaras:v3)
Fallback: Groq Whisper (whisper-large-v3-turbo) / Faster-Whisper
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import time
from typing import Optional, Dict, Any

logger = logging.getLogger("priya.stt_adapter")

ADITYA_BIASING_PROMPT = (
    "Aditya University admissions counsellor Priya student Karthik Telugu Hindi English "
    "B.Tech CSE ECE EEE Mechanical Civil MBA MCA ASAT JEE EAPCET fees placements scholarships hostel campus"
)


class MultiProviderSTT:
    """
    STT adapter with automatic failover to Groq Whisper when Sarvam credits run out.
    """

    def __init__(self, primary_provider: str = "sarvam", sarvam_api_key: Optional[str] = None):
        self.primary_provider = primary_provider
        self.sarvam_api_key = sarvam_api_key or os.getenv("SARVAM_API_KEY", "")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.is_sarvam_exhausted = False

    async def transcribe_audio_chunk(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language_hint: str = "en"
    ) -> Dict[str, Any]:
        """
        Transcribes an audio chunk using Sarvam or Groq Whisper fallback.
        Returns: {"text": str, "language": str, "provider": str}
        """
        if not audio_bytes or len(audio_bytes) < 320:
            return {"text": "", "language": language_hint, "provider": "none"}

        # If Sarvam is active and not exhausted, use Sarvam
        if self.primary_provider == "sarvam" and not self.is_sarvam_exhausted and self.sarvam_api_key:
            try:
                from direct_sarvam_stt import transcribe_sarvam_rest
                t0 = time.perf_counter()
                res = await transcribe_sarvam_rest(audio_bytes, sample_rate=sample_rate, language=language_hint)
                if res and res.get("text"):
                    dt = (time.perf_counter() - t0) * 1000
                    logger.debug(f"[STT:Sarvam] Transcribed in {dt:.1f}ms: '{res['text']}'")
                    return {"text": res["text"], "language": res.get("language", language_hint), "provider": "sarvam"}
            except Exception as e:
                err_msg = str(e).lower()
                if "credits exhausted" in err_msg or "402" in err_msg or "1003" in err_msg:
                    logger.warning("[STT] Sarvam credits exhausted! Switching to Groq Whisper fallback.")
                    self.is_sarvam_exhausted = True
                else:
                    logger.warning(f"[STT] Sarvam STT error: {e}. Attempting Groq Whisper fallback.")

        # Fallback: Groq Whisper
        if self.groq_api_key:
            try:
                t0 = time.perf_counter()
                text = await self._transcribe_groq_whisper(audio_bytes, sample_rate)
                dt = (time.perf_counter() - t0) * 1000
                logger.info(f"[STT:Groq] Transcribed in {dt:.1f}ms: '{text}'")
                return {"text": text, "language": language_hint, "provider": "groq"}
            except Exception as ex:
                logger.error(f"[STT:Groq] Whisper fallback failed: {ex}")

        return {"text": "", "language": language_hint, "provider": "failed"}

    async def _transcribe_groq_whisper(self, audio_bytes: bytes, sample_rate: int) -> str:
        """Calls Groq Whisper API for ultra-fast fallback transcription."""
        import wave
        from openai import AsyncOpenAI

        # Convert raw PCM to WAV buffer
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_bytes)
        wav_io.seek(0)
        wav_io.name = "audio.wav"

        client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=self.groq_api_key
        )
        transcription = await client.audio.transcriptions.create(
            file=("audio.wav", wav_io.read()),
            model="whisper-large-v3-turbo",
            prompt=ADITYA_BIASING_PROMPT,
            response_format="text",
            temperature=0.0,
        )
        return str(transcription).strip()
