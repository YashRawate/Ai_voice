# AdmitAI Priya — Comprehensive Project Overview & System Updates

**Document Version:** 1.0.0  
**Generated Date:** September 11, 2026  
**Repository:** `Ai_voice-main`  
**Primary Focus:** Overall Project Architecture, Root-Cause Engineering Fixes, Production Acoustic & Language Pipelines, and Test Verifications.

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [High-Level Project Architecture](#2-high-level-project-architecture)
3. [Comprehensive Engineering Updates & Changelog](#3-comprehensive-engineering-updates--changelog)
   - [Update 1: LangChain & LangGraph Session Lifecycle Architecture](#update-1-langchain--langgraph-session-lifecycle-architecture)
   - [Update 2: 5-Layer Context Engine & Zero-Repetition Memory](#update-2-5-layer-context-engine--zero-repetition-memory)
   - [Update 3: Multi-Provider STT/TTS Failover & Sarvam API Integration](#update-3-multi-provider-stttts-failover--sarvam-api-integration)
   - [Update 4: 7-Step Acoustic Pipeline & Anti-Barge-In System](#update-4-7-step-acoustic-pipeline--anti-barge-in-system)
   - [Update 5: Language Locking & Code-Mixed Stability Architecture](#update-5-language-locking--code-mixed-stability-architecture)
4. [Verification & Test Coverage Matrix](#4-verification--test-coverage-matrix)
5. [Directory Structure & Key File Map](#5-directory-structure--key-file-map)
6. [Operational & Execution Guide](#6-operational--execution-guide)

---

## 1. Executive Summary

**AdmitAI Priya** is an enterprise-grade, autonomous, low-latency Voice AI Counselor and CRM orchestration platform built for educational institutions (specifically configured for **Aditya University**). It conducts human-like, multi-turn voice conversations across telephony (PSTN via Twilio/SIP) and WebRTC environments in multiple Indian languages:
- **English (`en-IN`)**
- **Hindi (`hi-IN`)**
- **Telugu (`te-IN`)**
- **Tamil (`ta-IN`)**

The system captures student information (name, course interest, academic background, exam scores, hostel requirements), provides instant factual guidance from university knowledge bases, scores lead quality, and syncs data in real time with the CRM backend.

---

## 2. High-Level Project Architecture

The overall system is divided into two primary sub-systems:
1. **Voice AI Engine (`crm/priya-livekit/`)**: Real-time audio streaming, speech recognition, language resolution, acoustic filtering, LLM reasoning, and neural text-to-speech synthesis.
2. **CRM & Analytics Platform (`crm/`)**: Lead management, live call supervision, sentiment/intent scoring, transcript viewer, and telephony webhooks.

```
+-----------------------------------------------------------------------------------+
|                                 CALLER / USER                                     |
|               (Telephony / PSTN Trunk via Twilio OR WebRTC Browser)               |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          | Audio Stream (RTP / Opus / PCM 16kHz)
                                          v
+-----------------------------------------------------------------------------------+
|                     STEP 1: 7-STAGE ACOUSTIC PROCESSING PIPELINE                  |
|  - Real-Time AEC (NLMS / WebRTC AEC3) cancelling Priya's TTS loopback             |
|  - RNNoise / Spectral Gating Background Noise Suppressor                          |
|  - SNR Pre-Filter (discards frames below 8 dB before VAD)                         |
|  - Silero VAD (Dual Thresholds: 0.50 Normal Turn / 0.85 Barge-In)                 |
|  - Single-Owner Frame Debouncer (120ms continuous speech window)                  |
|  - Semantic STT Confirmation (filters coughs, clicks, "uh", "hmm")                |
+-----------------------------------------+-----------------------------------------+
                                          | Clean Speech Frames
                                          v
+-----------------------------------------------------------------------------------+
|               STEP 2: MULTILINGUAL STT & LANGUAGE RESOLUTION                      |
|  - STT Providers: Sarvam AI Saaras:v3 / Azure Speech / Deepgram                   |
|  - Language Resolver (priya/language/resolver.py):                                |
|    * Priority 1: Explicit Language Switch Command ("speak in English/Hindi")      |
|    * Priority 2: Short Utterance Guard (<15 chars preserves Indic session)        |
|    * Priority 3: Code-Mixed Loanword Retention (e.g. "admission status kya hai")  |
|    * Priority 4: Sustained Switch Threshold (>=25 chars English structure)       |
+-----------------------------------------+-----------------------------------------+
                                          | Transcript + Locked active_language
                                          v
+-----------------------------------------------------------------------------------+
|               STEP 3: REASONING & ORCHESTRATION (LANGGRAPH + CONTEXT ENGINE)      |
|  - 5-Layer Prompt Engine (Strict <= 600 Token Budget per turn):                   |
|    Layer 1: Identity & Persona (Priya from Aditya University)                     |
|    Layer 2: Mandatory Language Directive ("MUST respond ONLY in {lang}")          |
|    Layer 3: Canonical State Graph Slots (collected, missing, next question)       |
|    Layer 4: RAG University Knowledge (fees, scholarships, eligibility)           |
|    Layer 5: Sliding Recent Turns & Anti-Repetition Guard                          |
|  - LLM: Azure OpenAI GPT-4o-mini / Groq LLaMA 3.3 70B / Sarvam                    |
+-----------------------------------------+-----------------------------------------+
                                          | Response Text (in native Indic script)
                                          v
+-----------------------------------------------------------------------------------+
|               STEP 4: NEURAL TEXT-TO-SPEECH (TTS) & AUDIO OUTPUT                  |
|  - TTS Providers: Sarvam AI Bulbul:v2 (Devanagari/Telugu/Tamil) / Azure / Eleven  |
|  - Synchronized voice selection strictly matches locked active_language           |
|  - Streaming chunks sent back to LiveKit Room / Twilio SIP Stream                 |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               STEP 5: REAL-TIME CRM SYNC & ANALYTICS                              |
|  - SQLite / Postgres Lead Database update with extracted slots                    |
|  - WebSocket live events broadcast to React CRM Dashboard                         |
|  - Diagnostic Call Logs & Transcript preservation in crm/priya-livekit/transcripts|
+-----------------------------------------------------------------------------------+
```

---

## 3. Comprehensive Engineering Updates & Changelog

### Update 1: LangChain & LangGraph Session Lifecycle Architecture
* **Problem**: Mid-call disruptions, burst noise, or language changes caused Priya to re-greet the user from scratch (*"May I know your name, please?"*) and lose memory of previous answers.
* **Root Cause**: The session initialization code was re-invoked on turn errors or disruption events, causing stage resets.
* **Fix Implemented**:
  - Implemented `priya/orchestration/state_graph.py` using a single canonical state dictionary keyed solely by `session_id`.
  - State graph deterministically computes the current conversation stage and next required slot on the server, rather than allowing the LLM to guess.
  - Hardened `session_manager.py` and `agent.py` to decouple language switches from session resets.
  - Verified with `test_langgraph_pipeline.py` and `test_session_lifecycle_and_regreet_patch.py`.

### Update 2: 5-Layer Context Engine & Zero-Repetition Memory
* **Problem**: Prompt bloat (>2,500 tokens) caused high TTFT (Time-to-First-Token) latency and caused Priya to repeatedly ask questions the user had already answered.
* **Fix Implemented**:
  - Engineered the **5-Layer Context Engine** keeping prompt sizes strictly under **600 tokens** per turn:
    1. Base Identity (compact)
    2. Dynamic Per-Turn Language Directive
    3. Extracted Slots (name, phone, course, branch, score)
    4. Compact Knowledge Snippet (RAG)
    5. Sliding 3-turn window with repetition blacklist.
  - Added anti-repetition memory buffer checking similarity before any question is synthesized.
  - Verified with multi-turn replayers `test_test11_replay.py` (17 turns) and `test_test5_replay.py` (12 turns).

### Update 3: Multi-Provider STT/TTS Failover & Sarvam API Integration
* **Problem**: Outages or rate limits with single AI providers caused silent call drops.
* **Fix Implemented**:
  - Integrated robust fallback cascading:
    - **STT**: Sarvam Saaras:v3 $\rightarrow$ Azure Speech $\rightarrow$ Deepgram Nova-2.
    - **TTS**: Sarvam Bulbul:v2 $\rightarrow$ Azure Neural $\rightarrow$ ElevenLabs.
  - Integrated and validated updated Sarvam AI credentials (managed securely via .env).
  - Tuned latency logging in `latency_log.csv` tracking end-to-end user-stop-to-agent-speak timing.

### Update 4: 7-Step Acoustic Pipeline & Anti-Barge-In System
* **Problem**: Priya interrupted callers prematurely due to background noise, room echo, breathing, or her own speaker voice feeding back into the microphone.
* **Fix Implemented**:
  - Created modular acoustic components in `priya/audio/`:
    - `aec.py`: Real-Time Acoustic Echo Cancellation with delay calibration to remove Priya's TTS loopback.
    - `noise_suppression.py`: RNNoise and Spectral Gating pre-filters.
    - `snr_gate.py`: Low-overhead SNR pre-gate rejecting low-energy ambient noise.
    - `vad.py`: Dual-threshold Silero VAD (0.50 for standard turns, 0.85 high-confidence threshold for interrupting Priya while speaking).
    - `debouncer.py`: Single-owner consecutive-frame debouncer requiring $\ge 120\text{ms}$ sustained human speech.
    - `semantic_barge_in.py`: Semantic confirmation checking short audio snippets to reject non-speech fillers (*"uh"*, *"hmm"*, throat clears).
  - Provided calibration utility in `scripts/calibrate_thresholds.py`.
  - Verified with `test_acoustic_pipeline.py` (10/10 tests passed).

### Update 5: Language Locking & Code-Mixed Stability Architecture
* **Problem**: In calls where users spoke Hindi or code-mixed Hindi (e.g. *"admission status kya hai"*, *"fees kitni hai please"*, *"okay"*), Priya repeatedly reverted to English responses.
* **Root Causes Diagnosed**:
  1. Regex in `agent.py` discarded Hindi/Telugu STT language hints whenever the transcript contained English/Roman alphabet loanwords.
  2. STT or detector treated single short English loanwords (*"yes"*, *"okay"*, *"fees"*) as an intent to change the entire call language to English.
  3. System prompts used suggestive wording rather than strict language directives.
* **Fix Implemented**:
  - Created `priya/language/resolver.py`:
    - `resolve_mixed_language(detected_lang, transcript, session_lang)` implementing 4-tier precedence:
      1. **Explicit switch commands** (highest priority).
      2. **Short loanword/filler guard** ($< 15$ characters keeps session language).
      3. **Code-mixed Indic retention** (keeps Hindi/Telugu/Tamil if Indic particles or domain loanwords are present).
      4. **Sustained English switch** ($\ge 25$ characters pure English required to leave Indic mode).
    - `build_language_system_prompt(active_language)`: Injects authoritative per-turn prompt rule instructing the LLM to reply strictly in the active language and script.
  - Synchronized `agent.py` and `direct_server.py` to ensure `STT language` $\rightarrow$ `Language Resolver` $\rightarrow$ `LLM System Prompt` $\rightarrow$ `TTS Voice Selection` all share the exact same locked language variable.
  - Rewrote language styles in `prompts.py` replacing loose suggestions with mandatory instructions for `hi-IN`, `te-IN`, `ta-IN`, and `en-IN`.
  - Verified with `test_language_locking.py` (7/7 tests passed).

---

## 4. Verification & Test Coverage Matrix

All automated test suites in the repository are passing:

| Test Suite File | Focus Area | Verification Detail | Result |
|---|---|---|---|
| `test_language_locking.py` | Language Locking & Resolver | 7 unit tests covering normalization, code-mixed retention, short fillers, explicit switch, and prompt generation | **7/7 PASSED** |
| `test_acoustic_pipeline.py` | Audio, AEC, VAD, Debounce | 10 tests verifying NLMS AEC, SNR gating, dual VAD thresholds, 120ms debounce, and semantic barge-in | **10/10 PASSED** |
| `test_test11_replay.py` | Multi-turn Admissions Flow | 17-turn full conversation replay simulating student lead qualification | **17/17 TURNS PASSED** |
| `test_test5_replay.py` | Course & Scholarship Inquiries | 12-turn dialogue replay checking slot capture and factual consistency | **12/12 TURNS PASSED** |
| `test_langgraph_pipeline.py` | LangGraph State Transitions | 3 tests validating deterministic state progression and slot updates | **3/3 PASSED** |
| `test_session_lifecycle_and_regreet_patch.py` | Anti-Regreeting & Noise Resilience | 4 tests verifying noise bursts and language switches never re-trigger Stage 1 greeting | **4/4 PASSED** |

---

## 5. Directory Structure & Key File Map

```
Ai_voice-main/
│
├── yashupdate.md                         # This comprehensive project & update summary
├── README.md                             # Project overview and general documentation
├── ARCHITECTURE.md                       # Architectural design and flow specifications
├── ADMITAI_PRIYA_SYSTEM_DOCUMENTATION.md # Detailed system manual and CRM docs
├── Aditya_University_Extracted_Data.txt  # Factual admissions data source
│
└── crm/                                  # CRM Application & Backend
    ├── server.js                         # Node.js Express server & WebSockets for CRM
    ├── package.json                      # CRM dependencies
    ├── public/                           # Web CRM dashboard UI
    │
    └── priya-livekit/                    # Voice Agent Core
        ├── agent.py                      # LiveKit worker entry point & turn lifecycle
        ├── direct_server.py              # Low-latency Direct WebSocket & audio server
        ├── prompts.py                    # System prompt templates & language instructions
        ├── session_manager.py            # Session storage & context persistence
        ├── conversation_history.py       # Sliding conversation history tracker
        ├── knowledge_base.py             # Admissions knowledge retriever
        ├── .env                          # Local environment variables & API keys
        │
        ├── priya/
        │   ├── audio/                    # 7-Step Acoustic Pipeline
        │   │   ├── aec.py                # Acoustic Echo Cancellation (NLMS & AEC3)
        │   │   ├── noise_suppression.py  # RNNoise / Spectral noise suppression
        │   │   ├── snr_gate.py           # Signal-to-Noise Ratio gate
        │   │   ├── vad.py                # Dual-threshold Silero VAD wrapper
        │   │   ├── debouncer.py          # Consecutive-frame debouncer
        │   │   └── semantic_barge_in.py  # STT-based semantic filter
        │   │
        │   ├── language/                 # Language Locking & Resolution
        │   │   ├── __init__.py           # Export bindings
        │   │   └── resolver.py           # resolve_mixed_language & prompt builder
        │   │
        │   └── orchestration/            # LangGraph State & Dialogue Management
        │       └── state_graph.py        # State graph & deterministic stage flow
        │
        ├── scripts/
        │   └── calibrate_thresholds.py   # Acoustic threshold calibration tool
        │
        └── tests/
            ├── test_language_locking.py  # Language locking test suite
            ├── test_acoustic_pipeline.py # Acoustic pipeline test suite
            ├── test_test11_replay.py     # 17-turn dialogue replay test
            ├── test_test5_replay.py      # 12-turn dialogue replay test
            ├── test_langgraph_pipeline.py# LangGraph pipeline test
            └── test_session_lifecycle_and_regreet_patch.py # Anti-regreet test
```

---

## 6. Operational & Execution Guide

### 1. Running Unit & Integration Tests
From the voice agent directory (`crm/priya-livekit`):
```bash
# Test language locking & code-mixing logic
py test_language_locking.py

# Test acoustic pipeline (AEC, VAD, Debounce)
py test_acoustic_pipeline.py

# Test conversation replays and state graph
py test_test11_replay.py
py test_test5_replay.py
py test_langgraph_pipeline.py
py test_session_lifecycle_and_regreet_patch.py
```

### 2. Starting the Voice Agent
```bash
# Console mode (Interactive text/audio debugging)
py agent.py console

# Production LiveKit Worker mode
py agent.py start

# Direct WebSocket Audio Server mode
py direct_server.py
```

### 3. Starting the CRM Dashboard
```bash
cd crm
npm install
npm start
# Access web dashboard at http://localhost:3000
```

### 4. Git & GitHub Repository Status
- All changes are cleanly committed or staged on the local `main` branch.
- **Remote Push Policy**: In accordance with user instructions, no remote push (`git push origin main`) will be performed without explicit instruction.
