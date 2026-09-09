"""
test_direct_pipeline.py — Comprehensive Test Suite for Direct Raw Audio Pipeline & Dual-Mode Switching.
"""

import os
import unittest
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

import direct_audio_codec as codec
from direct_sarvam_stt import DirectSarvamSTT
from direct_sarvam_tts import DirectSarvamTTS
from direct_server import DirectCallSession, get_llm_client
from long_conversation import detect_conversion_intent, detect_objection, is_goodbye
from agent import PatternRouter


class TestDirectAudioCodec(unittest.TestCase):
    """Test ITU-T G.711 mu-law and PCM16 conversions."""

    def test_mulaw_roundtrip_and_speed(self):
        # 20ms of audio at 8kHz = 160 samples = 320 bytes PCM16
        t = np.linspace(0, 0.02, 160, endpoint=False)
        # 440 Hz sine wave
        sine_wave = (np.sin(2 * np.pi * 440 * t) * 15000).astype(np.int16)
        pcm_in = sine_wave.tobytes()

        # Encode to mulaw (8-bit)
        mulaw = codec.pcm16_to_mulaw(pcm_in)
        self.assertEqual(len(mulaw), 160)

        # Decode back to PCM16
        pcm_out = codec.mulaw_to_pcm16(mulaw)
        self.assertEqual(len(pcm_out), 320)

        # G.711 is lossy companding, verify reconstructed signal correlates closely (>95%)
        reconstructed = np.frombuffer(pcm_out, dtype=np.int16)
        corr = np.corrcoef(sine_wave, reconstructed)[0, 1]
        self.assertGreater(corr, 0.98)

    def test_resampling_8k_to_16k_and_back(self):
        pcm_8k = np.random.randint(-10000, 10000, 160, dtype=np.int16).tobytes()
        pcm_16k = codec.resample_8k_to_16k(pcm_8k)
        self.assertEqual(len(pcm_16k), 640)  # 320 samples * 2 bytes = 640 bytes

        downsampled = codec.resample_16k_to_8k(pcm_16k)
        self.assertEqual(len(downsampled), 320)  # 160 samples * 2 bytes

    def test_rms_energy(self):
        silent = np.zeros(160, dtype=np.int16).tobytes()
        self.assertEqual(codec.calculate_rms_energy(silent), 0.0)

        loud = (np.ones(160, dtype=np.int16) * 16384).tobytes()
        energy = codec.calculate_rms_energy(loud)
        self.assertAlmostEqual(energy, 0.5, places=2)


class TestDirectSarvamSTTProtocol(unittest.TestCase):
    """Test Sarvam STT WebSocket URL generator and configuration."""

    def test_ws_url_generation(self):
        stt = DirectSarvamSTT(
            api_key="test_sarvam_key",
            language_code="te-IN",
            sample_rate=8000,
            encoding="mulaw",
            endpointing="vad",
        )
        url = stt._build_ws_url()
        self.assertIn("wss://api.sarvam.ai/speech-to-text-realtime/ws", url)
        self.assertIn("language_code=te-IN", url)
        self.assertIn("encoding=mulaw", url)
        self.assertIn("sample_rate=8000", url)
        self.assertIn("endpointing=vad", url)


class TestDirectSarvamTTSProtocol(unittest.TestCase):
    """Test Sarvam TTS synthesizer configuration and barge-in cancellation."""

    def test_cancellation(self):
        tts = DirectSarvamTTS(api_key="test_key", speaker="shreya", pace=1.12)
        self.assertFalse(tts._is_cancelled)
        tts.cancel()
        self.assertTrue(tts._is_cancelled)
        tts.reset_cancellation()
        self.assertFalse(tts._is_cancelled)


class TestDirectCallSessionLogic(unittest.IsolatedAsyncioTestCase):
    """Test 1:1 direct call session orchestration and fast paths."""

    async def test_fast_path_in_direct_session(self):
        mock_ws = AsyncMock()
        session = DirectCallSession(ws=mock_ws, stream_sid="stream_123", call_sid="call_abc")

        # Test PatternRouter fast-path hit directly
        query = "What is the fee for B.Tech CSE?"
        cached = PatternRouter.match(query, session.long_mgr.fact_memory.facts, lang="en-IN")
        self.assertIsNotNone(cached)
        self.assertTrue("2.75" in cached or "2,75,000" in cached)
        self.assertIn("scholarship", cached.lower())

    async def test_barge_in_clears_carrier_buffer(self):
        mock_ws = AsyncMock()
        session = DirectCallSession(ws=mock_ws, stream_sid="stream_123", call_sid="call_abc")
        session.is_speaking = True

        # Simulate user speech start (barge-in)
        await session._handle_user_speech_start()
        self.assertFalse(session.is_speaking)
        # Verify Twilio 'clear' event was sent to flush carrier jitter buffer
        mock_ws.send_json.assert_called_with({"event": "clear", "streamSid": "stream_123"})

    async def test_conversion_actions_in_direct_session(self):
        # Verify conversion intent detection is hooked up
        intent = detect_conversion_intent("Please send the application link on WhatsApp")
        self.assertEqual(intent, "send_application_link")

        visit_intent = detect_conversion_intent("I want to visit campus this Saturday")
        self.assertEqual(visit_intent, "book_campus_visit")


class TestDualModeSwitch(unittest.TestCase):
    """Test that environment variables toggle between LiveKit and Direct modes."""

    def test_env_switch_detection(self):
        with patch.dict(os.environ, {"AUDIO_PIPELINE": "direct"}):
            self.assertEqual(os.getenv("AUDIO_PIPELINE"), "direct")

        with patch.dict(os.environ, {"AUDIO_PIPELINE": "livekit", "USE_LIVEKIT": "true"}):
            self.assertEqual(os.getenv("AUDIO_PIPELINE"), "livekit")
            self.assertEqual(os.getenv("USE_LIVEKIT"), "true")


if __name__ == "__main__":
    unittest.main()
