# test_language_detection.py

import pytest
import numpy as np
import asyncio

from audio_quality_gate import AudioQualityGate, AudioQualityResult
from conversation_context import ConversationContext
from language_detector import LanguageDetector, DetectionResult
from explicit_switch_detector import ExplicitLanguageSwitchDetector, ExplicitSwitchResult
from switch_decision import LanguageSwitchDecider, SwitchDecision
from noise_resilience_handler import NoiseResilienceHandler, RecoveryAction


# ============================================================================
# Layer 1: Audio Quality Gate Tests
# ============================================================================
class TestAudioQualityGate:
    @pytest.mark.asyncio
    async def test_silent_audio_rejected(self):
        gate = AudioQualityGate(sample_rate=16000)
        silent_bytes = b'\x00' * 3200  # 100ms silence
        result = await gate.is_valid_speech(silent_bytes)
        assert not result.is_valid
        assert result.noise_level == "silent" or "quiet" in result.reason.lower()
        assert not result.has_speech

    @pytest.mark.asyncio
    async def test_empty_audio_rejected(self):
        gate = AudioQualityGate(sample_rate=16000)
        result = await gate.is_valid_speech(b'')
        assert not result.is_valid

    @pytest.mark.asyncio
    async def test_clipped_loud_audio_rejected(self):
        gate = AudioQualityGate(sample_rate=16000)
        # Create full-scale clipped signal
        loud_samples = np.full(3200, 32767, dtype=np.int16)
        result = await gate.is_valid_speech(loud_samples.tobytes())
        assert not result.is_valid
        assert result.noise_level == "clipped"

    @pytest.mark.asyncio
    async def test_clean_speech_structure(self):
        gate = AudioQualityGate(sample_rate=16000)
        # Synthetic speech-like harmonic tone
        t = np.linspace(0, 0.5, 8000)
        sine = 0.3 * np.sin(2 * np.pi * 300 * t) + 0.15 * np.sin(2 * np.pi * 600 * t)
        speech_bytes = (sine * 32767).astype(np.int16).tobytes()
        result = await gate.is_valid_speech(speech_bytes)
        assert isinstance(result, AudioQualityResult)
        assert result.snr_db >= 0.0


# ============================================================================
# Layer 2: Conversation Context Tests
# ============================================================================
class TestConversationContext:
    def test_default_state(self):
        ctx = ConversationContext(default_language="en-IN")
        expected = ctx.get_expected_language()
        assert expected["expected_language"] == "en-IN"
        assert expected["required_switch_confidence"] >= 0.80

    def test_explicit_switch_persistence(self):
        ctx = ConversationContext(default_language="en-IN")
        ctx.add_turn("user", "hindi mein baat karo", "hi-IN", explicit_switch=True)
        
        expected = ctx.get_expected_language()
        assert expected["expected_language"] == "hi-IN"
        assert expected["required_switch_confidence"] >= 0.90
        assert ctx.state.dominant_language == "hi-IN"

    def test_multi_turn_dominance_hysteresis(self):
        ctx = ConversationContext(default_language="en-IN")
        # 3 turns in Telugu stabilizes Telugu dominance
        ctx.add_turn("user", "fees entha", "te-IN")
        ctx.add_turn("agent", "fees 1 lakh", "te-IN")
        ctx.add_turn("user", "hostel undha", "te-IN")

        expected = ctx.get_expected_language()
        assert expected["expected_language"] == "te-IN"
        assert expected["required_switch_confidence"] >= 0.85

    def test_crm_slot_recording(self):
        ctx = ConversationContext()
        ctx.record_crm_slot("student_name", "Karthik")
        assert ctx.is_slot_filled("student_name")
        assert ctx.get_slot("student_name") == "Karthik"


# ============================================================================
# Layer 5: Explicit Switch Detector Tests
# ============================================================================
class TestExplicitSwitchDetector:
    def setup_method(self):
        self.detector = ExplicitLanguageSwitchDetector()

    def test_english_explicit_switches(self):
        phrases = [
            "speak in English please",
            "switch to english",
            "english please",
            "can you speak in english",
            "ఇంగ్లీష్ లో మాట్లాడండి"
        ]
        for p in phrases:
            res = self.detector.detect_explicit_switch(p)
            assert res.is_explicit_switch, f"Failed on '{p}'"
            assert res.target_language == "en-IN"
            assert res.confidence > 0.95

    def test_hindi_explicit_switches(self):
        phrases = [
            "hindi mein baat karo",
            "speak in hindi",
            "हिंदी में बात कीजिए",
            "hindi please",
            "ab hindi me bolo"
        ]
        for p in phrases:
            res = self.detector.detect_explicit_switch(p)
            assert res.is_explicit_switch, f"Failed on '{p}'"
            assert res.target_language == "hi-IN"

    def test_telugu_explicit_switches(self):
        phrases = [
            "telugu lo cheppandi",
            "speak in telugu",
            "తెలుగులో మాట్లాడండి",
            "telugu please",
            "telugu lo matladu"
        ]
        for p in phrases:
            res = self.detector.detect_explicit_switch(p)
            assert res.is_explicit_switch, f"Failed on '{p}'"
            assert res.target_language == "te-IN"

    def test_tamil_explicit_switches(self):
        phrases = [
            "tamil la sollunga",
            "speak in tamil",
            "தமிழில் பேசுங்கள்",
            "tamil please"
        ]
        for p in phrases:
            res = self.detector.detect_explicit_switch(p)
            assert res.is_explicit_switch, f"Failed on '{p}'"
            assert res.target_language == "ta-IN"

    def test_normal_queries_no_switch(self):
        queries = [
            "What is the fee for CSE branch?",
            "Do you offer hostel facilities for girls?",
            "Can I get scholarship based on EAMCET rank 15000?",
            "Yes, 15000"
        ]
        for q in queries:
            res = self.detector.detect_explicit_switch(q)
            assert not res.is_explicit_switch, f"False positive on '{q}'"


# ============================================================================
# Layer 3: Language Detector Tests (Multi-Signal Scoring)
# ============================================================================
class TestLanguageDetector:
    def setup_method(self):
        self.detector = LanguageDetector()

    @pytest.mark.asyncio
    async def test_native_script_detection(self):
        # Telugu script
        res_te = await self.detector.detect_language_with_confidence("ఫీజు వివరాలు చెప్పండి")
        assert res_te.detected_language == "te-IN"
        assert res_te.confidence >= 0.25

        # Devanagari script
        res_hi = await self.detector.detect_language_with_confidence("एडमिशन की प्रक्रिया क्या है")
        assert res_hi.detected_language == "hi-IN"
        assert res_hi.confidence >= 0.25

    @pytest.mark.asyncio
    async def test_code_mixed_keywords(self):
        # Hinglish
        res_hi = await self.detector.detect_language_with_confidence("CSE mein kitna fees hai")
        assert res_hi.detected_language == "hi-IN"

        # Tenglish
        res_te = await self.detector.detect_language_with_confidence("hostel facility ela undi")
        assert res_te.detected_language == "te-IN"

    @pytest.mark.asyncio
    async def test_english_query_detection(self):
        res_en = await self.detector.detect_language_with_confidence(
            "What is the average placement package for computer science?",
            stt_language="en-IN",
            stt_confidence=0.9
        )
        assert res_en.detected_language == "en-IN"
        assert res_en.confidence >= 0.50


# ============================================================================
# Layer 4: Switch Decision Tests (4 Gates)
# ============================================================================
class TestSwitchDecider:
    def setup_method(self):
        self.decider = LanguageSwitchDecider(max_switches_per_call=5)

    @pytest.mark.asyncio
    async def test_gate1_audio_invalid_blocks_switch(self):
        audio_quality = {"is_valid": False, "reason": "SNR too low"}
        context = {"expected_language": "en-IN", "required_switch_confidence": 0.85}
        detected = {"detected_language": "te-IN", "confidence": 0.95}

        decision = await self.decider.should_switch_language(audio_quality, context, detected)
        assert not decision.should_switch
        assert "Gate 1" in decision.reason

    @pytest.mark.asyncio
    async def test_gate2_max_switches_blocks(self):
        self.decider.switch_history = [{"from": "en", "to": "hi"}] * 5  # Max reached
        audio_quality = {"is_valid": True, "confidence": 0.90}
        context = {"expected_language": "en-IN", "required_switch_confidence": 0.85}
        detected = {"detected_language": "te-IN", "confidence": 0.95}

        decision = await self.decider.should_switch_language(audio_quality, context, detected)
        assert not decision.should_switch
        assert "Gate 2" in decision.reason

    @pytest.mark.asyncio
    async def test_gate3_low_confidence_blocks_switch(self):
        audio_quality = {"is_valid": True, "confidence": 0.90}
        context = {"expected_language": "en-IN", "required_switch_confidence": 0.85}
        detected = {"detected_language": "te-IN", "confidence": 0.70}  # Below 0.85

        decision = await self.decider.should_switch_language(audio_quality, context, detected)
        assert not decision.should_switch
        assert "Gate 3" in decision.reason

    @pytest.mark.asyncio
    async def test_gate4_same_language_is_noop(self):
        audio_quality = {"is_valid": True, "confidence": 0.90}
        context = {"expected_language": "en-IN", "required_switch_confidence": 0.85}
        detected = {"detected_language": "en-IN", "confidence": 0.90}

        decision = await self.decider.should_switch_language(audio_quality, context, detected)
        assert not decision.should_switch
        assert decision.action == "stay"

    @pytest.mark.asyncio
    async def test_all_gates_pass_allows_switch(self):
        audio_quality = {"is_valid": True, "confidence": 0.95}
        context = {"expected_language": "en-IN", "required_switch_confidence": 0.85}
        detected = {"detected_language": "te-IN", "confidence": 0.92}

        decision = await self.decider.should_switch_language(audio_quality, context, detected)
        assert decision.should_switch
        assert decision.target_language == "te-IN"
        assert decision.action == "switch"


# ============================================================================
# Layer 6: Noise Resilience Handler Tests
# ============================================================================
class TestNoiseResilienceHandler:
    def setup_method(self):
        self.handler = NoiseResilienceHandler()

    @pytest.mark.asyncio
    async def test_noisy_audio_asks_repeat_in_current_lang(self):
        audio_quality = {"is_valid": False, "noise_level": "very_noisy", "confidence": 0.1}
        
        # In Telugu
        action_te = await self.handler.handle_detection_failure(audio_quality, current_language="te-IN")
        assert action_te.action == "ask_repeat"
        assert "క్షమించండి" in action_te.message
        assert action_te.stay_in_language == "te-IN"

        # In Hindi
        action_hi = await self.handler.handle_detection_failure(audio_quality, current_language="hi-IN")
        assert action_hi.action == "ask_repeat"
        assert "माफ़ कीजिए" in action_hi.message

    @pytest.mark.asyncio
    async def test_ambiguous_low_conf_asks_clarification(self):
        audio_quality = {"is_valid": True, "noise_level": "moderate", "confidence": 0.6}
        det_result = {"confidence": 0.25}

        action = await self.handler.handle_detection_failure(
            audio_quality,
            current_language="en-IN",
            detection_result=det_result
        )
        assert action.action == "ask_clarification"
        assert "English" in action.message
