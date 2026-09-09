# ⚡ QUICK REFERENCE & COPY-PASTE GUIDE

This document contains ready-to-reference snippets and explanations for **Optimization 1 (Language Matching)** and **Optimization 2 (Latency Reduction)**.

---

## 🌐 FIX 1: LANGUAGE MATCHING (30-Minute Implementation)

### Problem
Calls started in English or mixed languages flip unpredictably into incorrect accents or languages due to noisy background audio or single-word misdetections.

### Solution: 6-Layer Decision Pipeline
1. **Gate 1: Audio Quality Gate (`audio_quality_gate.py`)**: Checks SNR, clipping, and energy to reject noise before speech detection.
2. **Gate 2: Multi-Signal Language Detection (`language_detector.py`)**: Uses Sarvam STT hints, script analysis (Telugu `\u0c00-\u0c7f`, Devanagari `\u0900-\u097f`), and romanized Indic keyword dictionaries.
3. **Gate 3: Explicit Switch Override (`explicit_switch_detector.py`)**: Direct caller instructions ("speak in English", "telugu lo matladandi", "hindi mein boliye") override all heuristics with 100% priority.
4. **Gate 4: Hysteresis Decider (`switch_decision.py`)**: Requires **2 consecutive turns** of high-confidence detection before switching away from dominant language, preventing voice flip-flops.
5. **Gate 5: Allowed Language Allowlist**: Spoken TTS is constrained strictly to `en-IN`, `te-IN`, `hi-IN`, `ta-IN`.
6. **Gate 6: Noise Resilience & Graceful Fallback (`noise_resilience_handler.py`)**: Prompts caller politely in the current language if audio is garbled instead of flipping languages.

### Agent Integration in `agent.py`:
```python
# Language switch logic in Priya agent:
def switch_language(self, code: str, reason: str):
    if not code or code == self._lang or code not in TTS_ALLOWED:
        return
    old_lang = self._lang
    self._lang = code
    self.conv_session.active_language = code
    self.tts.update_options(target_language_code=code)
    logger.info(f"[LANG] Switched voice language: {old_lang} -> {code} ({reason})")
```

---

## ⚡ FIX 2: LATENCY OPTIMIZATION (3 Quick Wins)

### Quick Win 1: Dynamic Prompt Context (<100 Tokens)
Avoid accumulating past system instructions into LLM chat history. Only the base persona and a compact single-turn directive are passed:
```python
# In agent.py llm_node:
if hasattr(self, "conv_session") and getattr(self.conv_session, "long_mgr", None):
    turn_directives = self.conv_session.long_mgr.build_turn_prompt(last_user_text, language=self._lang)
    turn_prompts.append(turn_directives)
```

### Quick Win 2: Fast-Path Caching (~0ms Response)
Common factual questions (fees, eligibility, hostel, placements) hit `PatternRouter` / `LatencyOptimizer` cache and return immediately:
```python
cached = PatternRouter.match(last_user_text, self.collected, lang=self._lang)
if not cached:
    cached = await LatencyOptimizer.try_fast_path(last_user_text, lang=self._lang)
if cached:
    self.conv_session.add_turn("assistant", cached, language=self._lang)
    yield cached
    return  # Azure LLM skipped entirely, 0ms latency
```

### Quick Win 3: Sentence-Level Audio Streaming
Streaming speech sentences as they are generated allows TTS to speak before the full response finishes generating:
- First word spoken in **<0.60s**.
- GPU prewarming (`_prewarm_llm()`) keeps Azure endpoints warm during the call.
- Contextual fillers (`fillers.py`) provide natural conversational pacing if Azure takes >1s on complex queries.

---

## 🧪 Verification Commands

```bash
# Verify language system
python run_tests_standalone.py

# Verify latency optimizer
python -m pytest test_latency_optimizer.py -v
```
