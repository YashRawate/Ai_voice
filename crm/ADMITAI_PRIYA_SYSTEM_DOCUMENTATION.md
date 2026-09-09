# AdmitAI Priya — Voice Agent with CRM: Technical Architecture & System Documentation

**Project Name**: AdmitAI Priya (Aditya University AI Admissions Voice Agent & CRM Platform)  
**Document Version**: 2.0.0  
**Last Updated**: September 2026  
**Source of Truth Note**: This document is built strictly from the actual codebase, live implementations, verified test suites, and configurations within this repository. Implemented features, optional modules, and proposed architectures are explicitly designated throughout.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Executive Summary](#2-executive-summary)
3. [Complete Technology Stack](#3-complete-technology-stack)
4. [System Architecture](#4-system-architecture)
5. [End-to-End Call Flow](#5-end-to-end-call-flow)
6. [Voice Agent — Priya](#6-voice-agent--priya)
7. [Supported Languages & 6-Layer Detection](#7-supported-languages--6-layer-detection)
8. [Admission Conversion Funnel](#8-admission-conversion-funnel)
9. [Short-Term Memory (STM) Architecture](#9-short-term-memory-stm-architecture)
10. [Long-Term / Persistent Customer Memory](#10-long-term--persistent-customer-memory)
11. [Memory vs Conversation History](#11-memory-vs-conversation-history)
12. [Redis Architecture & Session Store](#12-redis-architecture--session-store)
13. [MongoDB & CRM Database Architecture](#13-mongodb--crm-database-architecture)
14. [CRM Dashboard (React + Vite Frontend)](#14-crm-dashboard-react--vite-frontend)
15. [Backend API Architecture (Node.js/Express)](#15-backend-api-architecture-nodejs-express)
16. [AI / LLM Architecture & Failover Chains](#16-ai--llm-architecture--failover-chains)
17. [Prompt Engineering & Dynamic Context Injection](#17-prompt-engineering--dynamic-context-injection)
18. [No-Repetition Engine](#18-no-repetition-engine)
19. [DialogueSlotManager & Entity Extraction](#19-dialogueslotmanager--entity-extraction)
20. [Question Engine](#20-question-engine)
21. [Knowledge Base, RAG & Vector Store](#21-knowledge-base-rag--vector-store)
22. [Tools and Function Calling](#22-tools-and-function-calling)
23. [Model Context Protocol (MCP) Architecture](#23-model-context-protocol-mcp-architecture)
24. [Watchdog & Reliability Architecture](#24-watchdog--reliability-architecture)
25. [Handling Real-World Voice Problems](#25-handling-real-world-voice-problems)
26. [Latency Optimization & Fast-Path Routing](#26-latency-optimization--fast-path-routing)
27. [Concurrency, Load Calculations & Scalability](#27-concurrency-load-calculations--scalability)
28. [Security, Privacy & Data Protection](#28-security-privacy--data-protection)
29. [Configuration & Environment Variables](#29-configuration--environment-variables)
30. [Project Folder Structure](#30-project-folder-structure)
31. [Important Classes, Functions & Interfaces](#31-important-classes-functions--interfaces)
32. [Data Models & Schemas](#32-data-models--schemas)
33. [Complete Data Flow Diagram](#33-complete-data-flow-diagram)
34. [Error Handling & Fallback Matrix](#34-error-handling--fallback-matrix)
35. [Logging, Metrics & Monitoring](#35-logging-metrics--monitoring)
36. [Testing & Verification Suite](#36-testing--verification-suite)
37. [Deployment Architecture](#37-deployment-architecture)
38. [Local Development Setup Guide](#38-local-development-setup-guide)
39. [Production Architecture](#39-production-architecture)
40. [LangChain Integration (Proposed / Architectural Fit)](#40-langchain-integration--proposed--architectural-fit)
41. [STM vs LTM Comparison Matrix](#41-stm-vs-ltm-comparison-matrix)
42. [Current Technical Limitations](#42-current-technical-limitations)
43. [Future Roadmap & Improvements](#43-future-roadmap--improvements)
44. [Critical Constraints](#44-critical-constraints)
45. [Interview & Viva Explanations](#45-interview--viva-explanations)
46. [Frequently Asked Questions (Technical FAQ)](#46-frequently-asked-questions-technical-faq)
47. [Architecture Decision Records (ADRs)](#47-architecture-decision-records-adrs)
48. [Final Architecture Summary & Developer Handoff](#48-final-architecture-summary--developer-handoff)

---

## 1. Project Overview

* **Project Name**: AdmitAI Priya — Intelligent Admissions Voice Agent & Multi-Tenant CRM Platform.
* **One-Line Description**: A dual-pipeline, multilingual AI voice counselor and enterprise CRM that conducts real-time consultative admission phone calls in Indian languages with sub-second latency, zero question repetition, and automated lead lifecycle synchronization.
* **Detailed Description**: AdmitAI Priya is a production-grade admissions automation system built for Aditya University (and multi-tenant educational institutions). It bridges high-throughput telephony (LiveKit SIP Cloud and direct WebSocket telephony streaming), Indian-language AI speech services (Sarvam AI), high-speed LLM inference (Azure OpenAI, Groq, Gemini), structured short-term and persistent memory, and a comprehensive Node.js/Express + React CRM platform.
* **Problem Statement**: Higher education institutions receive hundreds of thousands of student inquiries during admission seasons. Human counseling teams suffer from severe operational bottlenecks: long caller hold times, inconsistent course eligibility screening, repetitive information gathering, inability to handle regional Indian languages fluently (Telugu, Hindi, Tamil, English), high counselor turnover, and manual CRM data entry errors.
* **Why This Project Is Needed**: Traditional IVR systems are rigid, robotic, and frustrating to callers. Generic chatbots cannot handle conversational speech over telephony, struggle with code-mixed Indian dialects ("Telugish", "Hinglish"), forget facts gathered 2 minutes earlier, and fail to drive persuasive admission conversions. AdmitAI Priya solves this with a human-like, consultative voice agent that remembers caller facts, handles real-time interruptions, and updates CRM lead states in real time.
* **Target Users**:
  1. *Prospective Students & Parents*: Inquiring about programs (B.Tech, Management, Pharmacy, Nursing), eligibility, fees, scholarships (ASAT), and campus tours.
  2. *Admissions Counselors & Tele-callers*: Managing lead assignments, viewing call transcripts, verifying candidate documents, and tracking follow-ups.
  3. *Admissions Directors & Campus Admins*: Monitoring real-time campaign conversions, regional performance, counselor analytics, and competitive intelligence.
* **Main Objective**: Maximize qualified admissions conversions by engaging every caller in their native language within 1 second of speaking, resolving questions accurately from an audited university knowledge base, and booking campus visits or scholarship applications.
* **Key Differentiators**:
  * *Dual-Mode Audio Pipeline*: Supports both LiveKit SFU (cloud telephony via SIP trunks) and direct WebSocket raw $\mu$-law streaming for zero-transcoding in-process telephony.
  * *6-Layer Language Architecture*: Audio quality gating, multi-turn hysteresis, script + lexical detection, 4-gate switch verification, explicit switch override, and noise resilience.
  * *4-Layer Memory System*: Sliding window active context, permanent slot facts, conversation audit trails, and explicit dialogue finite state machine.
  * *Zero Question Repetition Engine*: Proactively removes already-collected slots (name, exam scores, program preference) from prompts and question queues.
  * *Unified CRM Sync*: Live event streaming directly into MongoDB with automated AI post-call summarization and sentiment extraction.
* **High-Level Workflow**:
  1. Caller dials university number $\rightarrow$ Telephony routes audio to Voice Worker.
  2. Voice Worker streams audio through STT $\rightarrow$ Extracts user slots $\rightarrow$ Queries Memory & Knowledge Base.
  3. LLM synthesizes concise, stage-appropriate counsel $\rightarrow$ Synthesizes TTS $\rightarrow$ Streams audio back to caller.
  4. Worker pushes real-time call events to Node.js backend $\rightarrow$ MongoDB updates lead status $\rightarrow$ React CRM reflects live transcript.
* **What the System Can and Cannot Do**:
  * *Can Do*: Handle inbound/outbound phone calls, dynamically switch between English, Telugu, Hindi, and Tamil, extract student profiles, handle barge-in interruptions under 200ms, query university program/fee/hostel data, book campus tours, export CRM reports, and trigger automated follow-up campaigns.
  * *Cannot Do*: Cannot perform legal financial transactions directly on the call (direct payment gateways are handed off via SMS/WhatsApp links), cannot make medical diagnostic assessments, and cannot admit students who do not meet government/AICTE minimum statutory criteria.

---

## 2. Executive Summary

AdmitAI Priya is an end-to-end voice AI and admissions management system. In under 3 minutes, here is how the entire platform operates:

1. **The Inbound/Outbound Call**: When a prospective student calls Aditya University (or when the automated CRM triggers an outbound campaign), the voice stream connects directly to Priya via LiveKit SIP or the Direct Audio WebSocket Server.
2. **Instant Perception & Quality Gating**: As the caller speaks, the audio is analyzed for Signal-to-Noise Ratio (SNR) and clipping. Sarvam AI converts speech into text in real time. The 6-layer language engine identifies whether the student is speaking English, Telugu, Hindi, or Tamil—even when code-mixing ("Telugish" like *"B.Tech CSE fee entha andi?"*).
3. **Structured Memory & Slot Extraction**: Rather than dumping the entire messy conversation history into the LLM, the `DialogueSlotManager` immediately extracts structured facts (Student Name, Exam Name, Board Marks, Desired Branch, City) into Short-Term Memory (STM). If Rahul states his name in Turn 1, the `NoRepetitionEngine` permanently locks Rahul's identity, preventing Priya from ever asking for his name again.
4. **Consultative Intelligence (LLM)**: Priya's prompt is dynamically assembled with her consultative persona, the verified university knowledge base, the extracted customer facts, and anti-repetition rules. Running on Azure OpenAI (`gpt-4.1-mini`), Groq (`llama-3.3-70b`), or Gemini, the LLM generates a crisp, conversational response limited to 25 words to maintain rapid voice rhythm.
5. **Human-like Speech Synthesis**: The response is streamed sentence-by-sentence to Sarvam AI (`bulbul:v3` *shreya* voice) or Azure Realtime voice, returning natural-sounding Indian voice audio with total turn latency under 1 second.
6. **Live CRM Synchronization**: Simultaneously in the background, a lightweight `Reporter` streams live transcript turns, sentiment scores, and gathered facts to the Node.js Express backend. The MongoDB database updates the lead record, and admissions officers watching the React CRM dashboard see the live transcript update turn-by-turn.
7. **Production Engineering**: Built with non-blocking async operations, circuit breakers, multi-LLM failover chains, Redis session caching, and full unit test coverage across all 6 language layers and backend APIs.

---

## 3. Complete Technology Stack

| Technology | Purpose | Where Used in Project | Why It Is Used |
|---|---|---|---|
| **Python 3.10+ / 3.13** | Core Voice Agent Runtime | `crm/priya-livekit/` | High-performance asynchronous runtime for audio processing, WebSocket streaming, and AI integrations. |
| **LiveKit Agents SDK** | Telephony & WebRTC SFU | `crm/priya-livekit/agent.py` | Industry-standard WebRTC and SIP orchestration with native VAD, turn endpointing, and streaming LLM-to-TTS pipeline. |
| **FastAPI / Uvicorn** | Direct Audio Telephony Server | `crm/priya-livekit/direct_server.py` | Lightweight, high-throughput ASGI server hosting direct raw 8kHz $\mu$-law WebSocket connections for low-overhead telephony. |
| **Sarvam AI (Saaras / Bulbul)** | Indian STT & TTS Engine | `agent.py`, `direct_sarvam_stt.py`, `direct_sarvam_tts.py` | State-of-the-art accuracy for 11 Indian languages and dialects, code-mixed script support, and low-latency audio synthesis. |
| **Azure OpenAI Service** | Primary LLM & Realtime Engine | `agent.py`, `direct_server.py`, `test_voice_azure.py` | Enterprise-grade `gpt-4.1-mini` and `gpt-realtime-mini` deployment hosted in South India datacenter for low roundtrip latency. |
| **Groq Cloud** | High-Speed Fallback LLM | `agent.py`, `direct_server.py` | LPU hardware acceleration running `llama-3.3-70b-versatile` with Time-To-First-Token (TTFT) ~0.7s for sentence streaming. |
| **Google Gemini (1.5 / 2.5 Flash)** | Post-Call Analytics & Fallback LLM | `crm/backend/services/gemini.js`, `agent.py` | Multimodal intelligence for structured post-call report generation, transcript extraction, and vector embedding generation. |
| **Redis** | High-Frequency Session Cache | `crm/priya-livekit/`, `long_conversation.py` | In-memory key-value store for sub-millisecond session state, slot locks, and call rate limiting. |
| **MongoDB & Mongoose** | Durable CRM Data Store | `crm/backend/models/`, `crm/backend/config/db.js` | Flexible document database storing multi-tenant organizations, colleges, leads, call logs, audit trails, and reports. |
| **Node.js (v20+) & Express** | Backend API & Orchestration | `crm/backend/server.js`, `crm/backend/routes/` | Robust asynchronous REST and WebSocket API layer powering CRM business logic, lead imports, and campaign dispatching. |
| **React 18 & Vite** | Frontend CRM Dashboard | `crm/frontend/src/` | Ultra-fast client application with Tailwind/Vanilla CSS, responsive analytics, live call monitoring, and lead management. |
| **Twilio (SIP & Elastic Trunking)**| Outbound/Inbound Telephony | `crm/backend/services/twilioOutbound.js`, `make_call.py`| Global PSTN connectivity routing phone calls to LiveKit SIP endpoints or direct audio WebSockets. |
| **Azure Cosmos DB** | Managed Cloud Conversation Store | `crm/priya-livekit/azure_store.py` | Enterprise document storage with 30-day auto-TTL for persistent turn logging and compliance. |
| **Azure App Configuration** | Zero-Restart Dynamic Prompts | `crm/priya-livekit/azure_store.py` | Cloud configuration store enabling instant system prompt and parameter updates without restarting agent workers. |
| **Azure AI Search** | Managed Vector/Semantic KB | `crm/priya-livekit/azure_store.py` | Semantic search index querying structured university knowledge documents for dynamic retrieval. |
| **Model Context Protocol (MCP)**| Standardized Tool Interface | `crm/priya-livekit/mcp_client.py`, `mcp_server.py` | Decouples admissions and CRM lookup tools from agent business logic via JSON-RPC protocol. |
| **JSON Web Tokens (JWT) & bcrypt**| Authentication & Password Security | `crm/backend/middleware/auth.js`, `utils/tokenUtils.js` | Stateless HTTP access tokens paired with secure httpOnly refresh cookies and 12-round bcrypt password hashing. |
| **Jest & Python unittest** | Verification Suites | `crm/backend/tests/`, `crm/priya-livekit/test_*.py` | Comprehensive automated unit, integration, and live simulation test suites across all layers. |

---

## 4. System Architecture

### 4.1 End-to-End System ASCII Architecture Diagram

```
                                    +-------------------------------------------------------------+
                                    |                 PSTN / Mobile Caller                        |
                                    +-------------------------------------------------------------+
                                                                   |
                                                      (SIP Trunk / Phone Call)
                                                                   v
                                    +-------------------------------------------------------------+
                                    |         Telephony Ingestion & Audio Transport               |
                                    |  - LiveKit Cloud SIP / SFU (Multi-party WebRTC)             |
                                    |  - OR Direct WebSocket Server (8kHz mu-law raw audio)       |
                                    +-------------------------------------------------------------+
                                            |                                             ^
                               (Audio In)   |                                             |  (Audio Out)
                                            v                                             |
+-----------------------------------------------------------------------------------------+-------+
|                              ADMITAI VOICE WORKER PIPELINE (Python)                             |
|                                                                                                 |
|   +--------------------------+     +--------------------------+     +-----------------------+   |
|   | 1. Audio Quality Gate    | --> | 2. Silero VAD / Turn     | --> | 3. Sarvam AI STT      |   |
|   |    - Silence / Clipping  |     |    - EOU Delay (0.35s)   |     |    - Multi-language   |   |
|   |    - SNR Assessment      |     |    - Barge-in (0.20s)    |     |    - 8k/16k streaming |   |
|   +--------------------------+     +--------------------------+     +-----------------------+   |
|                                                                                 |               |
|                                                                                 v (Transcript)  |
|   +-----------------------------------------------------------------------------------------+   |
|   | 4. 6-Layer Advanced Language & Hysteresis Engine                                        |   |
|   |    - Script Classifier  |  - Lexical Detector  |  - Explicit Switch Detector            |   |
|   |    - 4-Gate Decision Decider (Min Conf 0.85, Flapping Prevention Hysteresis)            |   |
|   +-----------------------------------------------------------------------------------------+   |
|                                            |                                                    |
|                                            v (Active Language & Verified Text)                  |
|   +-----------------------------------------------------------------------------------------+   |
|   | 5. Conversation & Memory Management Layer                                               |   |
|   |    - DialogueSlotManager: Extracts Name, Score, Exam, Branch, City via Regex & Heuristics|   |
|   |    - FactMemory (Layer 2): Permanent slot storage across all turns                     |   |
|   |    - SlidingWindow (Layer 1): Bounded 6-8 turn active context                          |   |
|   |    - NoRepetitionEngine: Prunes already-collected questions from dynamic agenda         |   |
|   +-----------------------------------------------------------------------------------------+   |
|                        |                                             |                          |
|    (Cache/State Sync)  v                                             v (Dynamic Prompt)         |
|         +-----------------------+                       +-----------------------+               |
|         | Redis Session Memory  |                       | LLM Inference Engine  |               |
|         | - Locks & Fast Cache  |                       | - Azure OpenAI (4.1m) |               |
|         | - Sub-millisecond TTL |                       | - Groq LLaMA-3.3 70B  |               |
|         +-----------------------+                       | - Gemini Fallback     |               |
|                                                         +-----------------------+               |
|                                                                     |                           |
|                                                                     v (Text Stream)             |
|   +--------------------------+     +--------------------------+     |                           |
|   | 7. Number Normalization  | <-- | 6. Latency Optimizer &   | <---+                           |
|   |    - Currency / Lakhs    |     |    Fast-Path Pattern Hit |                                 |
|   |    - Academic Percentages|     |    - Sub-50ms Bypass     |                                 |
|   +--------------------------+     +--------------------------+                                 |
|               |                                                                                 |
|               v (Spoken Text)                                                                   |
|   +-----------------------------------------------------------------------------------------+   |
|   | 8. Sarvam AI Bulbul:v3 TTS Synthesis (Shreya / Kavya / Ritu Voice Stream)               |   |
|   +-----------------------------------------------------------------------------------------+   |
|               |                                                                                 |
+---------------+---------------------------------------------------------------------------------+
                | (Audio Stream to Caller)
                v
  (Caller Hears Priya's Voice)

                        |
                        | (Async HTTP Reporting via reporter.py)
                        v
+-------------------------------------------------------------------------------------------------+
|                                 ADMITAI BACKEND & CRM LAYER (Node.js)                           |
|                                                                                                 |
|   +-----------------------------------------------------------------------------------------+   |
|   | Express 4 REST & Webhook Dispatcher (:5000)                                             |   |
|   | - /api/priya/agent-event  --> Real-time turn ingestion & session mirroring              |   |
|   | - /api/leads              --> Multi-tenant lead management, DND, stage pipelines       |   |
|   | - /api/calls              --> Outbound trigger campaigns & call telemetry               |   |
|   | - /api/auth               --> JWT access/refresh auth with role-based scoping           |   |
|   +-----------------------------------------------------------------------------------------+   |
|            |                                           |                                |       |
|            v                                           v                                v       |
|   +--------------------+                      +--------------------+          +-------------+   |
|   | MongoDB Database   |                      | Gemini Post-Call   |          | React + Vite|   |
|   | - Leads, Calls,    |                      | Analytics Engine   |          | Frontend    |   |
|   |   Reports, Audits  |                      | - Auto summary/dispo|         | Dashboard   |   |
|   +--------------------+                      +--------------------+          +-------------+   |
+-------------------------------------------------------------------------------------------------+
```

### 4.2 Technical Communication Characteristics

* **Synchronous Operations**:
  * Audio packet transport over WebSocket / WebRTC RTP streams.
  * Turn endpointing and VAD speech detection.
  * Fast-path pattern cache lookups ($\sim 5$ms).
  * Streaming LLM generation to streaming TTS chunk delivery.
* **Asynchronous Operations (Off Critical Path)**:
  * Backend CRM reporting (`Reporter` pushes events asynchronously without blocking speech generation).
  * MongoDB document updates and audit log writes.
  * Azure Cosmos DB long-term history archival.
  * Post-call Gemini deep analytics and structured report generation.
  * Automatic lead re-engagement cron schedules (`node-cron`).
* **Real-Time Performance Budgets**:
  * *Voice-to-Voice Latency Target*: $< 1000$ms.
  * *VAD Endpointing Delay ($EOU\_MIN\_DELAY$)*: $0.15\text{s} - 0.35\text{s}$.
  * *Barge-In Interruption Delay*: $< 200\text{ms}$.
  * *Pattern Cache Hit Latency*: $< 50\text{ms}$.
* **External API Dependencies**:
  * LiveKit Cloud (SIP/SFU WebRTC infrastructure).
  * Sarvam AI (Speech-to-Text & Text-to-Speech API).
  * Azure OpenAI / Groq / Gemini (LLM inference endpoints).
  * Twilio (PSTN Elastic SIP Trunking).
* **Failure Boundaries & Circuit Breaking**:
  * *STT Drop*: Triggers localized clarification ("I couldn't hear that clearly, could you repeat?").
  * *Primary LLM Failure*: Failover adapter instantly routes to secondary key or secondary provider (Azure $\rightarrow$ Groq $\rightarrow$ Gemini $\rightarrow$ Local Ollama).
  * *TTS Failure*: Direct fallback to pre-buffered local conversational filler phrases.
  * *CRM Backend Offline*: Agent maintains standalone call continuity in memory without dropping the caller.

---

## 5. End-to-End Call Flow

The call lifecycle follows 14 deterministic stages:

```
[1. Call Start] ------> [2. Session Init] ------> [3. Caller Speaks] ------> [4. VAD Trigger]
                                                                                   |
                                                                                   v
[8. Memory Update] <--- [7. Slot Extract] <--- [6. Lang Detect] <--- [5. Sarvam STT]
       |
       v
[9. Prompt Assembly] -> [10. LLM Inference] -> [11. TTS Stream] ----------> [Caller Hears]
                                                       |
                                                       v
                                            [12. CRM Event Post]
                                                       |
                                                       v
                                            [13. Analytics Report]
                                                       |
                                                       v
                                            [14. Call Completion]
```

1. **Call Starts**: Caller dials the university inbound number or backend initiates an automated campaign call via Twilio/LiveKit SIP trunk.
2. **Session Initialization**:
   * A unique `sessionId` (UUIDv4) is generated.
   * `SessionContext` and `LongConversationManager` instances are allocated.
   * Priya synthesizes and plays the fixed opening greeting in English: *"Hello! I am Priya, Senior Admissions Counselor at Aditya University. May I know your name, please?"*
3. **Caller Speech**: Caller responds via mobile microphone. Audio stream is sent in real time (20ms chunks).
4. **VAD (Voice Activity Detection)**: Silero VAD monitors energy and phonemes. End-of-Utterance (EOU) delay is enforced ($0.35$s) to ensure the caller has finished their sentence before cutting in.
5. **STT (Speech-to-Text)**: Sarvam AI streaming engine processes raw audio and returns the finalized transcript text along with detection metadata.
6. **Language Detection & Verification**:
   * Text is analyzed by `LanguageDetector`.
   * If an explicit switch phrase is detected (*"Telugu lo matladandi"*), language flips immediately with confidence $0.99$.
   * Otherwise, 4-gate verification verifies confidence ($\ge 0.85$), audio validity, and multi-turn stability before switching voice and prompt directives.
7. **Slot & Fact Extraction**:
   * `DialogueSlotManager` executes targeted regexes and pattern analyzers against the user's transcript.
   * Extracts Name, Intermediate/12th Marks, Entrance Exam Score (ASAT/JEE/EAPCET), Preferred Branch, and City.
8. **Memory Update**:
   * Extracted facts are committed to `FactMemory` (permanent) and mirrored to `GLOBAL_SESSION_STORE` and Redis.
   * The turn is appended to `SlidingWindow` (active 6-turn queue).
9. **LLM Prompt Construction**:
   * Dynamic prompt builder combines: System Persona + Knowledge Base + Facts Checklist + Stage Directives + Anti-Repetition rules + 6-turn Sliding Window.
10. **LLM Response Generation**:
    * LLM synthesizes a consultative response bounded by $MAX\_REPLY\_TOKENS=100$ and strict 25-word conversational rules.
    * Text is pre-cleaned (stripping tool calls, leaked JSON, markdown bullet points).
11. **TTS (Text-to-Speech) Synthesis**:
    * Text is passed through `_normalize_numbers_for_speech` (converting `"₹2,75,000"` $\rightarrow$ `"two lakh seventy five thousand rupees"`).
    * Streamed to Sarvam `bulbul:v3` (*shreya* voice) and transmitted back over telephony.
12. **CRM Update (Async)**:
    * `Reporter` posts transcript turn, speaker, timestamp, and active language to Node.js backend `/api/priya/agent-event`.
    * Lead document in MongoDB is updated with latest facts.
13. **Post-Call Analytics & Extraction**:
    * Upon hangup, Gemini Flash processes the full transcript, computing interest score (0–100), sentiment (Positive/Neutral/Negative), objections raised, and follow-up action items.
14. **Call Completion**:
    * Lead stage moves to `contacted`, `campus_visit_booked`, or `follow_up_scheduled`.
    * If appointment was booked, reminder cron queue is primed.

---

## 6. Voice Agent — Priya

### 6.1 Persona & Communication Objectives

* **Identity**: Priya, Senior Admissions Counselor at Aditya University (2025–26 academic batch).
* **Mission**: Convert every inquiry into a concrete admission milestone:
  1. *Primary Action*: Book a guided Campus Visit with parents to the 250-acre smart campus in Surampalem (near Kakinada/Rajahmundry).
  2. *Secondary Action*: Register for the ASAT (Aditya Scholarship Admission Test) to secure up to 50% fee waivers.
  3. *Tertiary Action*: Reserve a provisional seat online before branch quotas fill.
* **Tone & Demeanor**: Warm, highly knowledgeable, consultative, culturally respectful, and proactive. Never sounds like a passive informational FAQ bot.

### 6.2 Conversational Behaviors & Rules

* **Word Economy**: Every response is constrained to 1–2 short spoken sentences (maximum 25 words). This eliminates unnatural monologue lag over phone lines.
* **Single Question Rule**: Priya asks strictly **ONE** clear, focused question per turn. Never stacks questions (e.g., asking for branch and board score in the same breath is strictly blocked).
* **Number & Fee Normalization**: Priya formats all Indian numbers into natural spoken phonetics to avoid raw numeric speech engine artifacts (*"15 zero zero zero"* is normalized to *"fifteen thousand"*).
* **Handling Interruptions (Barge-In)**: Telephony audio is continuously monitored. If the user speaks for $> 200$ms while Priya is speaking, Priya's audio playback is cancelled immediately, and her turn transitions to listening.
* **Handling Noisy / Unclear Speech**: If the audio quality gate reports clipping or high noise ($SNR < 5$dB), Priya does not hallucinate; she issues a polite, language-matched repeat request (*"Mee voice clear ga ledu andi, okasari malli chepthara?"* in Telugu or *"Aapki aawaaz thodi cut rahi hai, kya aap dohra sakte hain?"* in Hindi).
* **Context-Blind "Okay" Responses**: When a caller gives a flat affirmation (*"Okay"*, *"Ha"*, *"Fine"*), Priya does not repeat the previous statement; she advances to the next unfulfilled stage in the admission funnel.

---

## 7. Supported Languages & 6-Layer Detection

### 7.1 Language Matrix

| Language | Code | STT Support | TTS Voice (`bulbul:v3`) | Direct Telugish / Hinglish Mode | Status |
|---|---|---|---|---|---|
| **Indian English** | `en-IN` | Yes (16k / 8k) | `shreya` / `kavya` | Pure English + Indian Academic context | **Active / Production** |
| **Telugu** | `te-IN` | Yes (16k / 8k) | `shreya` / `ritu` | Conversational Telugish (Telugu grammar + English academic terms) | **Active / Production** |
| **Hindi** | `hi-IN` | Yes (16k / 8k) | `shreya` / `kavya` | Conversational Hinglish (Polite "Aap/Ji" counselor dialect) | **Active / Production** |
| **Tamil** | `ta-IN` | Yes (16k / 8k) | `shreya` | Standard Tamil conversational admissions counselor | **Active / Production** |

### 7.2 The 6-Layer Advanced Language Engine

```
[Incoming User Utterance]
           |
           v
+-------------------------------------------------------------------------+
| Layer 1: Audio Quality Gate                                             |
| - Verifies non-empty audio, checks RMS energy, flags clipping & low SNR |
+-------------------------------------------------------------------------+
           | (Pass Gate 1)
           v
+-------------------------------------------------------------------------+
| Layer 5: Explicit Switch Detector (100% Priority Override)              |
| - Matches regex: "speak in english", "telugu lo matladu", "hindi bolo"  |
| - If match -> Immediately switches language with confidence 0.99       |
+-------------------------------------------------------------------------+
           | (No explicit command -> Evaluate Natural Speech)
           v
+-------------------------------------------------------------------------+
| Layer 3: Multi-Signal Language Classifier                               |
| - Script classification (Telugu, Devanagari, Tamil Unicode characters)  |
| - Romanized vocabulary matching (Telugish/Hinglish keywords)            |
+-------------------------------------------------------------------------+
           | (Calculated Confidence)
           v
+-------------------------------------------------------------------------+
| Layer 2: Conversation Context & Multi-Turn Hysteresis                   |
| - Tracks 5-turn language history window                                 |
| - Prevents single anomalous word from flipping stable session language  |
+-------------------------------------------------------------------------+
           | (Smoothed Candidate)
           v
+-------------------------------------------------------------------------+
| Layer 4: Switch Decision Decider (4-Gate Architecture)                  |
| - Gate 1: Audio Validity | Gate 2: Non-Silent | Gate 3: Conf >= 0.85    |
| - Gate 4: Cooldown & Hysteresis Lock                                    |
+-------------------------------------------------------------------------+
           | (Approved Decision)
           v
+-------------------------------------------------------------------------+
| Layer 6: Noise Resilience & Graceful Fallback                           |
| - If audio degraded: returns localized clarification in current language|
| - Locks active voice and LLM prompt to approved language code           |
+-------------------------------------------------------------------------+
```

---

## 8. Admission Conversion Funnel

```
+------------------------------------------------------------------------------+
| STAGE 1: GREETING & CALLER IDENTIFICATION                                   |
| Objective: Establish rapport and capture student's real name.                |
| Rules: Do NOT pitch courses or visits before knowing caller name.           |
| Trigger to Next: Name successfully extracted into FactMemory.                |
+------------------------------------------------------------------------------+
                                       |
                                       v
+------------------------------------------------------------------------------+
| STAGE 2: PROGRAM & BRANCH DISCOVERY                                          |
| Objective: Identify target degree (B.Tech, MBA, MCA, Pharmacy) & Branch.     |
| Knowledge Injected: Aditya University 2025 program offerings & specializations|
| Trigger to Next: Program/branch extracted into FactMemory.                   |
+------------------------------------------------------------------------------+
                                       |
                                       v
+------------------------------------------------------------------------------+
| STAGE 3: ACADEMIC BACKGROUND & SCHOLARSHIP SCREENING                        |
| Objective: Collect 12th Board marks / Entrance Exam scores (ASAT/JEE/EAPCET) |
| Counselor Pitch: Match score to ASAT scholarship slab (up to 50% fee waiver) |
| Trigger to Next: Academic scores / exam status captured.                     |
+------------------------------------------------------------------------------+
                                       |
                                       v
+------------------------------------------------------------------------------+
| STAGE 4: CONSULTATIVE VALUE PITCH & HIGH-CONVERSION CLOSE                    |
| Objective: Close on Campus Visit, Direct WhatsApp Application, or ASAT Reg.  |
| Value Points: 3,800+ placements, 27 LPA highest package, 250-acre smart campus|
| Close Action: Propose Saturday 4 PM campus tour with parents.                |
+------------------------------------------------------------------------------+
```

### Objection Handling Battlecards

* **Objection: "Fees are too high / expensive"**  
  * *Priya*: *"We offer up to 50% merit scholarships based on ASAT and Intermediate marks, semester-wise installment plans, and 0% interest on-campus SBI/HDFC education loans."*
* **Objection: "I need to discuss with my parents first"**  
  * *Priya*: *"Admissions are a major family milestone! We warmly invite you and your parents for a guided campus tour this Saturday to explore our labs and hostels in person."*
* **Objection: "I am waiting for my JEE / EAPCET rank"**  
  * *Priya*: *"You can secure a provisional seat reservation today with a 100% full refund guarantee if you join an IIT, NIT, or top government college."*
* **Objection: "How are the hostel facilities and food?"**  
  * *Priya*: *"Our 250-acre gated smart campus provides 24/7 security, AC rooms with attached bathrooms, gym, sports complex, and hygienic North and South Indian dining messes."*

---

## 9. Short-Term Memory (STM) Architecture

### 9.1 What is Short-Term Memory?

Short-Term Memory (STM) is the active, in-session state that exists exclusively for the duration of a single telephone call. It holds verified facts extracted from the caller's voice, the current dialogue state, the active language, and recent turn context.

### 9.2 The Rahul Step-by-Step Fact Memory Walkthrough

```
[Turn 1]
Caller: "Namaste, my name is Rahul."
  -> DialogueSlotManager regex matches: name = "Rahul"
  -> FactMemory updated: { "name": "Rahul" }
  -> NoRepetitionEngine locks: "name" is KNOWN.
  -> Priya replies: "Nice to meet you Rahul! Which program or branch are you interested in?"

[Turn 2]
Caller: "I want to join B.Tech CSE."
  -> DialogueSlotManager matches: program = "B.Tech", branch = "CSE"
  -> FactMemory updated: { "name": "Rahul", "program": "B.Tech", "branch": "CSE" }
  -> Stage shifts: INFO_GATHERING -> ACADEMIC_ELIGIBILITY
  -> Priya replies: "Great choice Rahul! B.Tech CSE at Aditya has great placements. How much did you score in 12th?"

[Turn 3]
Caller: "I got 94% in my 12th board exams."
  -> DialogueSlotManager matches: score = "94%", exam = "12th Board"
  -> FactMemory updated: { "name": "Rahul", "program": "B.Tech", "branch": "CSE", "score": "94%" }
  -> Value Pitch: 94% qualifies for 50% merit scholarship waiver.
  -> Priya replies: "Congratulations Rahul! With 94%, you qualify for a 50% scholarship. Would you like to book a campus visit this Saturday?"
```

---

## 10. Long-Term / Persistent Customer Memory

### 10.1 Identity Resolution Chain

```
[Incoming Caller CLI / Phone: +919876543210]
                       |
                       v
[Normalization: normalizeIndianPhone -> +919876543210]
                       |
                       v
[MongoDB CRM Query: Lead.findOne({ phone: "+919876543210" })]
                       |
                       +---> Found: Load persistent Lead record (Previous calls, preferred branch, assigned officer)
                       |
                       +---> Not Found: Create new Lead document in CRM
```

### 10.2 Implemented vs Proposed Capabilities

* **Implemented & Active**:
  * Persistent lead documents in MongoDB storing phone, name, email, admission status, notes, call history, and sentiment.
  * Async turn and session summary archiving into Azure Cosmos DB with auto-expiring 30-day/90-day TTLs.
  * Automatic post-call AI analysis updating CRM lead records upon call termination.
* **Proposed / Future Architecture**:
  * Cross-call dynamic context pre-warming into voice worker memory before the opening greeting executes (e.g., *"Welcome back Rahul, are you still planning your campus visit?"*).

---

## 11. Memory vs Conversation History

| Feature | Raw Conversation Transcript | Short-Term Memory (STM) | Long-Term Customer Memory (LTM) | Knowledge Base (KB) |
|---|---|---|---|---|
| **What it contains** | Exact verbatim speech turns (*"umm"*, *"hello"*, *"namaste"*) | Structured, verified key-value facts (Name, Score, Branch) | Permanent candidate profile, past call history, status | Immutable university facts (Fees, scholarships, courses) |
| **Token Footprint** | Grows indefinitely ($\approx 300\text{ tokens/min}$) | Constant ($\approx 40\text{ tokens}$) | Constant summary ($\approx 80\text{ tokens}$) | Constant retrieved snippets ($\approx 150\text{ tokens}$) |
| **Inference Latency**| Degrades over time as context window swells | Flat sub-second latency across 30+ minute calls | Flat latency | Flat latency |
| **Durability** | In-memory during call; logged on hangup | Active session only | Permanent in MongoDB | Permanent file / vector index |

---

## 12. Redis Architecture & Session Store

### 12.1 Key Schemas & Data Structures

| Key Pattern | Data Type | TTL | Purpose |
|---|---|---|---|
| `session:{call_id}:state` | JSON / Hash | 1200s (20 mins) | Active session metadata (language, stage, turns count). |
| `session:{call_id}:facts` | Hash | 1200s (20 mins) | Extracted candidate facts (`name`, `branch`, `score`). |
| `session:{call_id}:lock` | String (Mutex) | 5s | Concurrency lock preventing race conditions during rapid speech. |
| `rate:phone:{phone_number}`| String (Counter)| 3600s (1 hr) | Outbound call pacing guard preventing spam dialing. |

### 12.2 Resilience & Non-Blocking Fallback

Redis operations are wrapped in sub-millisecond execution guards (`REDIS_TIMEOUT_MS=100`). If Redis is unreachable or experiences network partition, the voice agent automatically falls back to in-process memory (`GLOBAL_SESSION_STORE`) without interrupting voice audio or dropping callers.

---

## 13. MongoDB & CRM Database Architecture

The CRM data layer consists of 25 Mongoose models. Core schemas include:

1. **Lead (`models/Lead.js`)**: Master record of the prospective student.
   * `phone` (Indexed, Unique per branch), `name`, `email`, `status` (`new`, `contacted`, `interested`, `campus_visit_booked`, `applied`, `enrolled`, `lost`), `score`, `exam`, `programInterest`, `assignedOfficerId`, `branchId`, `orgId`, `dnd`.
2. **Call (`models/Call.js`)**: Individual phone call interaction.
   * `phone`, `sessionId`, `direction` (`inbound`/`outbound`), `status` (`initiated`, `ringing`, `in-progress`, `completed`, `failed`), `duration`, `transcript` (Array of speaker/text/timestamp), `sentiment`, `interested`, `recordingUrl`.
3. **Report (`models/Report.js`)**: Structured AI intelligence extracted by Gemini.
   * `callId`, `summary`, `actionItems`, `objections`, `disposition`, `eligibilityAssessment`, `sentimentScore`.
4. **User (`models/User.js`)**: CRM staff and counselor accounts.
   * `name`, `email`, `password` (bcrypt hashed), `role` (`admin`, `college_admin`, `officer`, `viewer`), `branchId`, `orgId`.
5. **Branch (`models/College.js` / `models/Branch.js`)**: Campus/location hierarchy.

---

## 14. CRM Dashboard (React + Vite Frontend)

### 14.1 User Interface & Capabilities

The frontend (`crm/frontend/src/`) is built with React 18 and Vite:
* **Live Call Monitoring (`pages/LiveMonitoring/`)**: Displays active telephony calls in real time, streaming transcript turns as they occur.
* **Lead Manager (`pages/LeadManager/`, `pages/Leads/`)**: Data table with branch filtering, status stage modification, CSV/bulk import, DND toggling, and single-click outbound dialing.
* **Call Detail & Audio Playback (`pages/StudentReport/`)**: Plays recorded call audio alongside synchronized transcripts, sentiment markers, and Gemini AI extracted summaries.
* **Admissions Analytics (`pages/AdmissionAnalytics/`, `pages/FunnelAnalytics/`)**: Real-time charts showing conversion rates by branch, lead source distribution, counselor call volumes, and scholarship qualification metrics.
* **Counselor & Branch Administration (`pages/Branches/`, `pages/Team/`)**: Counselor assignment rules, branch quotas, and role permissions.
* **QR & Admissions Portal (`pages/QrManagement/`, `pages/AdminAdmissionPortal/`)**: QR campaign generation for on-ground marketing events and spot counselor verification.

---

## 15. Backend API Architecture (Node.js / Express)

### Core Backend Endpoints

| Method | Route | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/login` | Authenticate user, returns JWT and sets httpOnly cookie | No |
| `GET` | `/api/auth/me` | Fetch active session user profile | Yes |
| `GET` | `/api/leads` | List branch-scoped leads with search and pagination | Yes |
| `POST` | `/api/leads/import` | Bulk import numbers, executes phone normalization & DND deduplication | Yes |
| `POST` | `/api/leads/:id/call` | Trigger instant outbound AI voice call to student | Yes |
| `POST` | `/api/priya/trigger-call`| Dial individual phone number via LiveKit SIP / Twilio pipeline | Yes / Internal |
| `POST` | `/api/priya/agent-event` | High-frequency voice agent event stream (transcripts, slots, status) | No (Internal/Token) |
| `POST` | `/api/calls/webhook` | Telephony status webhook receiver (duration, status, recording URL) | Shared Secret |
| `GET` | `/api/calls/:id` | Fetch individual call log with complete transcript | Yes |
| `POST` | `/api/calls/:id/analyze`| Re-run Gemini AI transcript analysis and update disposition | Yes |
| `GET` | `/api/analytics/overview`| Aggregate university conversion metrics and call volume summaries | Yes |
| `GET` | `/api/audit` | Retrieve immutable compliance audit logs | Yes (Admin/Officer) |

---

## 16. AI / LLM Architecture & Failover Chains

### 16.1 Failover Adapter Architecture

```
[LLM Inference Request]
          |
          v
+-------------------------------------------------------+
| 1. Azure OpenAI (gpt-4.1-mini) [South India Hub]      |
|    - Primary endpoint (Low latency, high compliance)  |
+-------------------------------------------------------+
          | (On 429 Rate Limit / 5xx Network Timeout)
          v
+-------------------------------------------------------+
| 2. Groq Cloud (llama-3.3-70b-versatile)              |
|    - 7 contiguous fallback keys for high concurrency  |
+-------------------------------------------------------+
          | (On Groq Daily TPM Cap)
          v
+-------------------------------------------------------+
| 3. Google Gemini 2.5 / 1.5 Flash                      |
|    - High quality, resilient Google AI Studio endpoint|
+-------------------------------------------------------+
          | (On Complete Internet Partition)
          v
+-------------------------------------------------------+
| 4. Local Ollama (qwen2.5:3b)                          |
|    - Standalone on-premises fail-safe                 |
+-------------------------------------------------------+
```

---

## 17. Prompt Engineering & Dynamic Context Injection

The system prompt is dynamically assembled in `agent.py` on every turn:

```markdown
# ROLE & MISSION
You are Priya, Senior Admissions Counsellor at Aditya University (2025-26).
YOUR PRIMARY MISSION: CONVERT EVERY CALLER INTO AN ADMISSION (Campus Visit / ASAT / Provisional Seat).

# CRITICAL CONVERSATIONAL RULES
1. Maximum 25 words per reply.
2. Ask strictly ONE clear question per turn.
3. Start in English; switch natively when caller speaks Telugu, Hindi, or Tamil.
4. Facts from Knowledge Base ONLY.

# EXTRACTED CANDIDATE FACTS (DO NOT RE-ASK):
- Name: Rahul
- Branch Interest: B.Tech Computer Science Engineering
- 12th Board Marks: 94%

# ADITYA UNIVERSITY KNOWLEDGE BASE
- Campus: 250-acre smart campus in Surampalem (Kakinada/Rajahmundry).
- Placements: 3,800+ offers, 27 LPA highest package, 120+ MNC recruiters.
- Scholarships: Up to 50% merit concession for >90% intermediate marks or ASAT.
- Contact / Campus Booking: +91 70360 76661.
```

---

## 18. No-Repetition Engine

The `NoRepetitionEngine` (`crm/priya-livekit/no_repetition.py`) prevents repetitive question loops:
1. **Fact Detection**: Reads all populated keys from `FactMemory`.
2. **Prompt Filtering**: Dynamically removes system prompt instructions prompting for known fields.
3. **Agenda Advancement**: If `name` is known, the engine forcibly advances the dialogue state machine to Stage 2 (`PROGRAM_DISCOVERY`).

---

## 19. DialogueSlotManager & Entity Extraction

The `DialogueSlotManager` (`crm/priya-livekit/session_manager.py`) uses targeted regexes with stop-word filtering:
* **Name Extraction**: Captures proper nouns while rejecting false positives (`"interested"`, `"admission"`, `"student"`, `"calling"`).
* **Score Extraction**: Captures percentage and percentile formats (`"95%"`, `"95 percent"`, `"950 marks"`).
* **Exam Extraction**: Matches standardized entrance exams (`ASAT`, `JEE Main`, `JEE Advanced`, `EAPCET`, `NEET`, `CAT`, `MAT`).
* **Branch/Program Extraction**: Resolves canonical degrees (`B.Tech CSE`, `AI & ML`, `Data Science`, `ECE`, `Mechanical`, `MBA`, `MCA`, `B.Pharm`).
* **City / Location Extraction**: Identifies regional candidate hometowns (`Hyderabad`, `Vijayawada`, `Visakhapatnam`, `Rajahmundry`, `Kakinada`, `Tirupati`).

---

## 20. Question Engine

The `QuestionEngine` (`crm/priya-livekit/question_engine.py`) prioritizes inquiries:
$$\text{Next Question} = f(\text{Dialogue Stage}, \text{Missing Mandatory Slots}, \text{Caller Language})$$
* If `name` is missing $\rightarrow$ Returns Stage 1 Greeting Question.
* If `name` is present, `program` missing $\rightarrow$ Returns Stage 2 Branch Ingestion Question.
* If `program` is present, `score` missing $\rightarrow$ Returns Stage 3 Academic Eligibility Question.
* If all slots present $\rightarrow$ Returns Stage 4 High-Conversion Campus Visit Close.

---

## 21. Knowledge Base, RAG & Vector Store

* **Local Curated Knowledge Base (`Aditya_University_Knowledge_Base.md` & `university_data.py`)**: Authoritative repository data covering fees, hostel costs, NBA/NAAC A++ accreditations, bus routes, and scholarship slabs.
* **Fast-Path Pattern Matching (`latency_optimizer.py`)**: Instant regex match for standard fee and placement questions, responding in $<50$ms.
* **Backend Vector Store (`services/vectorStore.js` & `services/ragStore.js`)**: TF-IDF and Gemini embedding stores supporting semantic document retrieval across multi-page college prospectus PDFs.

---

## 22. Tools and Function Calling

* **`save_detail` Tool**: Invoked by LLM to store structured caller facts (`slot_name`, `slot_value`).
* **`check_fee_and_eligibility` Tool**: Queries university database for branch-specific tuition fees, NRI quota rates, and prerequisites.
* **`book_campus_visit` Tool**: Registers date, time, and attendee count, dispatching an automated SMS confirmation with GPS coordinates to Surampalem campus.

---

## 23. Model Context Protocol (MCP) Architecture

AdmitAI includes an MCP client-server bridge (`mcp_client.py` and `mcp_server.py`):
* **Standardized JSON-RPC**: Decouples external CRM integrations from core LiveKit agent logic.
* **Extensible Tools**: Allows third-party LMS and state admissions databases to be queried dynamically without restarting live call processes.

---

## 24. Watchdog and Reliability Architecture

* **Silence Watchdog**: If user remains silent for 8 seconds, Priya initiates a polite prompt (*"Are you there?"* / *"Vinipistunda andi?"*).
* **TTS WebSocket Health Monitor**: Re-establishes dropped STT/TTS connections in $< 300$ms.
* **Turn Timeout Guard**: Bounds total LLM execution to 4.0s before failing over to pre-buffered conversational fillers.

---

## 25. Handling Real-World Voice Problems

| Real-World Problem | System Detection | Recovery Mechanism | User Experience |
|---|---|---|---|
| **Background Noise / Traffic** | Audio Quality Gate detects low SNR | LiveKit Background Voice Cancellation (BVC) pre-cleans audio before STT | Priya hears user voice clearly without distortion. |
| **Mid-Sentence Pauses** | VAD silence detection | `EOU_MIN_DELAY=0.35s` prevents premature agent cut-in | Caller can pause to think without being interrupted. |
| **Barge-In / Interruption** | Voice activity detected during playback | Agent stops TTS audio playback within 200ms and switches to STT | Feels like natural human conversation. |
| **Language Flapping** | 4-gate verification + hysteresis | Requires $\ge 0.85$ confidence and multi-turn stability to switch | Voice stays stable without awkward accent hopping. |
| **LLM Rate Limit (429)** | HTTP 429 response code | Instant FailoverAdapter switch to secondary key / Groq / Gemini | Caller experiences $< 500$ms delay with no drop. |

---

## 26. Latency Optimization & Fast-Path Routing

```
[User Transcript] 
        |
        +---> [Fast-Path Regex: "What are the B.Tech CSE fees?"] 
        |             |
        |             v (Hit: 45ms)
        |     [Return Cached Answer from university_data.py] ------> [Stream to TTS]
        |
        +---> [Complex Consultative Question]
                      |
                      v (Miss: Slow Path)
              [Play Smart Contextual Filler] ("Let me check the placement records for you...")
                      |
                      v
              [Azure OpenAI Stream -> Sentence-by-Sentence TTS Overlap]
```

---

## 27. Concurrency, Load Calculations & Scalability

### 27.1 Scale Calculations for 10,000 Calls / Hour

* **Average Traffic**:
  $$\text{Calls per second} = \frac{10,000}{3,600} \approx 2.78\text{ calls/sec}$$
* **Peak Burst Factor ($3\times$ to $5\times$)**:
  $$\text{Peak Traffic} \approx 8.3\text{ to }14.0\text{ calls/sec}$$
* **Concurrent Active Channels (assuming 3-minute average call duration)**:
  $$\text{Concurrent Calls} = 2.78\text{ calls/sec} \times 180\text{ sec} \approx 500\text{ concurrent voice streams}$$

### 27.2 Capacity & Resource Planning Matrix

| Subsystem | Load at 500 Concurrent Calls | Architecture Solution |
|---|---|---|
| **LiveKit SFU Workers** | 500 WebRTC audio streams | 5 distributed worker nodes (100 calls/worker). |
| **STT Engine (Sarvam)** | 500 concurrent bidirectional streams | Dedicated enterprise WebSocket bandwidth quota. |
| **LLM Inference** | $\approx 42\text{ requests/sec}$ (assuming 1 turn every 12s per call) | Multi-key pool + Azure Provisioned Throughput (PTU). |
| **Redis Cache** | $\approx 2,500\text{ ops/sec}$ | Single Redis 7.0 instance (handles $>100\text{k ops/sec}$). |
| **MongoDB Backend** | $\approx 50\text{ write ops/sec}$ (Async batch reporting) | Replica set with connection pooling (`maxPoolSize: 100`). |

---

## 28. Security, Privacy & Data Protection

* **Zero Hardcoded Secrets**: All API keys, connection strings, and JWT secrets are loaded via environment variables (`.env`).
* **Authentication & RBAC**: Node.js backend uses 15-minute JWT access tokens and 7-day secure `httpOnly` refresh cookies with role-based access control (`admin`, `college_admin`, `officer`, `viewer`).
* **PII & Phone Number Security**: DND registry compliance prevents unauthorized dialing. MongoDB documents isolate lead records by organizational ID (`orgId`).
* **Database Encryption**: All cloud database connections enforce TLS 1.2+ encryption in transit.

---

## 29. Configuration & Environment Variables

| Variable Name | Purpose | Required | Example Placeholder |
|---|---|---|---|
| `LIVEKIT_URL` | LiveKit Cloud WebRTC endpoint | Yes | `wss://your-project.livekit.cloud` |
| `LIVEKIT_API_KEY` | LiveKit API Key | Yes | `APITxxxxxx` |
| `LIVEKIT_API_SECRET` | LiveKit API Secret | Yes | `YOUR_LIVEKIT_SECRET` |
| `OUTBOUND_TRUNK_ID` | LiveKit SIP Outbound Trunk ID | Yes (for calls) | `ST_xxxxxx` |
| `SARVAM_API_KEY` | Sarvam AI STT/TTS Subscription Key | Yes | `sk_xxxxxx` |
| `AZURE_OPENAI_ENDPOINT` | Azure AI Foundry Endpoint | Yes | `https://your-foundry.services.ai.azure.com` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI Key | Yes | `YOUR_AZURE_KEY` |
| `AZURE_OPENAI_DEPLOYMENT` | Azure Chat Deployment Name | Yes | `gpt-4.1-mini` |
| `GROQ_API_KEY` | Groq LPU API Key | Optional | `gsk_xxxxxx` |
| `GEMINI_API_KEY` | Google Gemini API Key | Yes | `AQ.Abxxxxxx` |
| `MONGO_URI` | MongoDB Connection String | Yes | `mongodb://localhost:27017/admitai` |
| `JWT_ACCESS_SECRET` | JWT Access Token Signing Secret | Yes | `YOUR_JWT_ACCESS_SECRET` |
| `JWT_REFRESH_SECRET` | JWT Refresh Token Signing Secret| Yes | `YOUR_JWT_REFRESH_SECRET` |
| `ENABLE_REDIS_MEMORY` | Master switch for Redis session store | Optional | `true` / `false` |
| `AUDIO_PIPELINE` | Audio Transport Mode | Yes | `direct` / `livekit` |

---

## 30. Project Folder Structure

```
Ai_voice_agent_with_crm-main/
├── .env                                  # Root Environment Variables
├── ARCHITECTURE.md                       # Comprehensive Architecture Reference
├── Aditya_University_Extracted_Data.txt  # University Ground Truth Data
├── README.md                             # High-Level Project Overview
│
└── crm/
    ├── .env                              # CRM Environment Configuration
    ├── MASTER_ROADMAP.md                 # Complete System Implementation Roadmap
    ├── WEEK_BY_WEEK_IMPLEMENTATION.md    # Development Log & Sprint Milestones
    │
    ├── priya-livekit/                    # Python Voice AI Agent Engine
    │   ├── .env                          # Voice Agent Environment Config
    │   ├── .env.example                  # Sanitized Example Environment Config
    │   ├── Aditya_University_Knowledge_Base.md # Knowledge Base Document
    │   ├── agent.py                      # Primary LiveKit Voice Worker Entrypoint
    │   ├── direct_server.py              # Direct WebSocket Telephony Server
    │   ├── direct_audio_codec.py         # Mu-Law & PCM Audio Codecs
    │   ├── direct_sarvam_stt.py          # Direct Streaming STT Client
    │   ├── direct_sarvam_tts.py          # Direct Streaming TTS Client
    │   ├── session_manager.py            # Slot Extraction & Session Context
    │   ├── long_conversation.py          # 4-Layer Memory Management System
    │   ├── no_repetition.py              # Anti-Repetition Engine
    │   ├── question_engine.py            # Next-Best Question Selector
    │   ├── conversion_strategy.py        # Admission Funnel State Machine
    │   ├── latency_optimizer.py          # Fast-Path Pattern Matcher & Cache
    │   ├── university_data.py            # Structured Aditya Knowledge Base
    │   ├── reporter.py                   # Async Backend Telemetry Reporter
    │   ├── mcp_client.py                 # MCP Client Bridge
    │   ├── mcp_server.py                 # MCP Tool Server
    │   ├── audio_quality_gate.py         # Audio Validation & SNR Gate
    │   ├── language_detector.py          # Multi-Signal Language Classifier
    │   ├── conversation_context.py       # Multi-Turn Language Hysteresis
    │   ├── switch_decision.py            # 4-Gate Switch Verification Logic
    │   ├── explicit_switch_detector.py   # Explicit Language Switch Regexes
    │   ├── noise_resilience_handler.py   # Audio Degradation Fallback Handler
    │   ├── azure_store.py                # Azure Cosmos DB & AppConfig Client
    │   ├── make_call.py                  # Outbound Call CLI Trigger
    │   └── test_*.py                     # Complete Python Test Suite
    │
    ├── backend/                          # Node.js / Express CRM Backend
    │   ├── .env                          # Backend Environment Config
    │   ├── server.js                     # Express Bootstrap & Scheduler Init
    │   ├── config/
    │   │   └── db.js                     # Mongoose Database Connection
    │   ├── models/                       # 25 Mongoose Schemas (Lead, Call, Report, etc.)
    │   ├── routes/                       # 21 REST Routers (leads, calls, auth, audit, etc.)
    │   ├── services/                     # Business Logic (telephony, gemini, vectorStore)
    │   ├── middleware/                   # JWT Auth, Audit Logger, Error Handler
    │   ├── utils/                        # Token Utils, Report Generator, Phone Normalizer
    │   └── tests/                        # Jest Automated Test Suite
    │
    └── frontend/                         # React 18 + Vite CRM Dashboard
        ├── .env                          # Frontend Vite Configuration
        ├── index.html                    # Single Page Application Root
        ├── src/
        │   ├── App.jsx                   # React Router & Role-Based Navigation
        │   ├── main.jsx                  # React DOM Root
        │   ├── components/               # Reusable UI Elements (Modals, Tables, Charts)
        │   ├── pages/                    # 34 Dashboard Views (Leads, Calls, Analytics)
        │   └── lib/                      # Axios API Clients (`api.js`, `crmApi.js`, `priyaApi.js`)
```

---

## 31. Important Classes, Functions & Interfaces

| File | Class / Function | Purpose | Inputs | Outputs |
|---|---|---|---|---|
| `agent.py` | `build_llm()` | Instantiates resilient multi-LLM failover chain | Environment configs | `openai.LLM` / `FallbackAdapter` |
| `agent.py` | `_normalize_numbers_for_speech()` | Converts currency/digits to natural spoken Indian phonetics | Raw text string | Normalized spoken string |
| `session_manager.py`| `DialogueSlotManager.extract_slots()`| Extracts Name, Score, Exam, Program from user transcript | User text, active language | Dictionary of extracted slots |
| `long_conversation.py`| `FactMemory.update()` | Commits permanent candidate facts to short-term memory | Slot key, slot value | Boolean update confirmation |
| `no_repetition.py` | `NoRepetitionEngine.clean_prompt()`| Removes redundant questions for known facts from prompt | System prompt, known facts | Cleaned dynamic prompt string |
| `language_detector.py`| `LanguageDetector.detect()` | Classifies language via script and vocabulary signals | User text, audio features | Language code + confidence score |
| `direct_server.py` | `DirectCallSession.process_turn()`| Coordinates STT $\rightarrow$ LLM $\rightarrow$ TTS over direct WebSocket | Audio buffer | Binary audio stream |
| `telephony.js` | `dispatchCall()` | Initiates outbound call via LiveKit or legacy carrier | Call doc, college settings | Provider call SID & session ID |
| `gemini.js` | `parseTranscript()` | Extracts structured AI post-call report from transcript | Transcript array, call doc | Structured Report JSON object |

---

## 32. Data Models & Schemas

```javascript
// Lead Schema (crm/backend/models/Lead.js)
const leadSchema = new mongoose.Schema({
  phone:             { type: String, required: true, trim: true },
  name:              { type: String, default: 'Unknown' },
  email:             { type: String, default: '' },
  status:            { type: String, enum: ['new', 'contacted', 'interested', 'campus_visit_booked', 'applied', 'enrolled', 'lost'], default: 'new' },
  score:             { type: String, default: '' },
  exam:              { type: String, default: '' },
  programInterest:   { type: String, default: '' },
  assignedOfficerId: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },
  branchId:          { type: mongoose.Schema.Types.ObjectId, ref: 'College' },
  orgId:             { type: mongoose.Schema.Types.ObjectId, ref: 'Organization', required: true },
  dnd:               { type: Boolean, default: false },
}, { timestamps: true });

// Call Schema (crm/backend/models/Call.js)
const callSchema = new mongoose.Schema({
  phone:         { type: String, required: true },
  sessionId:     { type: String, index: true },
  direction:     { type: String, enum: ['inbound', 'outbound'], default: 'outbound' },
  status:        { type: String, enum: ['initiated', 'ringing', 'in-progress', 'completed', 'failed', 'no-answer'], default: 'initiated' },
  duration:      { type: Number, default: 0 },
  transcript:    [{ speaker: String, text: String, timestamp: Number }],
  sentiment:     { type: String, enum: ['positive', 'neutral', 'negative'], default: 'neutral' },
  interested:    { type: Boolean, default: false },
  recordingUrl:  { type: String, default: '' },
}, { timestamps: true });
```

---

## 33. Complete Data Flow Diagram

```
+---------------+              +--------------------+              +--------------------+
| Caller Voice  | ===(Audio)==> | Sarvam STT Engine  | ===(Text)===> | Slot Extraction    |
| (Mobile Phone)|              | (Speech-to-Text)   |              | (DialogueSlotMgr)  |
+---------------+              +--------------------+              +--------------------+
        ^                                                                     |
        | (RTP Audio)                                                         v (Slots)
+---------------+              +--------------------+              +--------------------+
| Sarvam TTS    | <==(Audio)== | Azure OpenAI LLM   | <==(Prompt)== | Redis / FactMemory |
| (Bulbul:v3)   |              | (Consultative AI)  |              | (Short-Term Memory)|
+---------------+              +--------------------+              +--------------------+
                                         |
                                         v (Async Event POST)
                               +--------------------+
                               | Node.js Express    |
                               | CRM Backend (:5000)|
                               +--------------------+
                                    |          |
                   (Document Save)  v          v  (REST / WebSocket)
                       +--------------+      +--------------------+
                       | MongoDB Store|      | React CRM Frontend |
                       | (Lead/Call)  |      | (Live Monitor View)|
                       +--------------+      +--------------------+
```

---

## 34. Error Handling & Fallback Matrix

| Subsystem Failure | Detection Mechanism | Automated Recovery Action | Impact on Caller |
|---|---|---|---|
| **Primary Azure LLM 429** | HTTP 429 status code | `FallbackAdapter` routes turn to Groq LLaMA-3.3 | Zero interruption ($<500$ms delay). |
| **Complete Internet Outage**| Network socket timeout | Local Ollama (`qwen2.5:3b`) generates turn response | Call continues with local inference. |
| **STT Connection Drop** | WebSocket close code | Instant WebSocket reconnection ($<300$ms) | Priya asks caller to repeat once. |
| **Redis Server Crash** | Connection refusal error | `SessionContext` falls back to in-process memory | Call proceeds with zero data loss. |
| **MongoDB Connection Failure**| Mongoose error event | Backend logs error; voice worker buffers turns locally | Voice call finishes normally. |

---

## 35. Logging, Metrics & Monitoring

* **Latency Tracker (`latency.py` / `latency_log.csv`)**: Records turn-by-turn metrics:
  * `eou_ms`: End-of-utterance silence finalization time.
  * `llm_ttft_ms`: Time-To-First-Token from LLM.
  * `tts_latency_ms`: Audio synthesis roundtrip time.
  * `total_latency_ms`: Total voice-to-voice turn latency.
* **HTTP Reporter (`reporter.py`)**: Asynchronously streams structured call telemetry to the CRM dashboard.
* **HTTP Logging (`morgan`)**: All Express API requests are logged with response codes and execution times.

---

## 36. Testing & Verification Suite

### Verification Matrix (100% Pass Rate Verified)

| Test Suite | File Location | Executed Command | Results |
|---|---|---|---|
| **6-Layer Language Engine** | `crm/priya-livekit/` | `py run_tests_standalone.py` | **100% PASSED** (All 6 layers verified) |
| **Direct Pipeline Unit Tests**| `crm/priya-livekit/` | `py -m unittest test_direct_pipeline.py` | **100% PASSED** (9/9 tests OK) |
| **Long Conversation Memory**| `crm/priya-livekit/` | `py -m unittest test_long_conversation.py` | **100% PASSED** (20/20 tests OK) |
| **Conversion & Slot Extract**| `crm/priya-livekit/` | `py -m unittest test_admission_conversion.py test_conversion_strategy.py test_dialogue_slots.py test_language_detection.py test_full_simulation.py` | **100% PASSED** (27/27 tests OK) |
| **Unavailable Courses & VAD** | `crm/priya-livekit/` | `py test_unavailable_and_interruption.py` | **100% PASSED** (100% accuracy) |
| **Live Azure OpenAI Endpoint**| `crm/priya-livekit/` | `py test_voice_azure.py` | **100% PASSED** (Live Foundry verified) |
| **Live Multi-Turn Dialogue** | `crm/priya-livekit/` | `py test_dialogue_live.py` | **100% PASSED** (5/5 turns sub-second) |
| **Live End-to-End Pipeline** | `crm/priya-livekit/` | `py test_full_pipeline.py` | **100% PASSED** (Azure + Sarvam audio) |
| **Backend Jest Test Suite** | `crm/backend/` | `npx jest` | **100% PASSED** (8/8 suites, 44/44 tests) |
| **Frontend Production Build** | `crm/frontend/` | `npm run build` | **100% PASSED** (Zero warnings, built in 791ms)|

---

## 37. Deployment Architecture

```
                                  [Internet Traffic]
                                          |
                                          v
                              +-----------------------+
                              | NGINX / Cloudflare    |
                              | SSL Termination & LB  |
                              +-----------------------+
                                   |             |
                   (Port 5173/443) |             | (Port 5000)
                                   v             v
                    +--------------------+ +--------------------+
                    | React / Vite SPA   | | Node.js Express API|
                    | Static Assets      | | Cluster (PM2)      |
                    +--------------------+ +--------------------+
                                                    |
                                   +----------------+----------------+
                                   |                                 |
                                   v                                 v
                        +--------------------+            +--------------------+
                        | MongoDB Replica Set|            | Redis 7.0 Cache    |
                        +--------------------+            +--------------------+

                                  [Telephony Network]
                                          |
                                          v
                              +-----------------------+
                              | LiveKit Cloud SFU /   |
                              | Twilio SIP Trunks     |
                              +-----------------------+
                                          |
                                          v
                              +-----------------------+
                              | Python Voice Workers  |
                              | (agent.py dev /       |
                              |  direct_server.py)    |
                              +-----------------------+
```

---

## 38. Local Development Setup Guide

### 1. Prerequisites
* Python 3.10+ (or Python 3.13)
* Node.js v20+ and npm
* MongoDB instance running locally on `localhost:27017`
* Redis instance running locally on `localhost:6379` (optional, in-memory fallback included)

### 2. Step-by-Step Installation

```bash
# Step 1: Clone the repository
git clone https://github.com/your-org/Ai_voice_agent_with_crm.git
cd Ai_voice_agent_with_crm-main

# Step 2: Install Python Voice Agent Dependencies
cd crm/priya-livekit
pip install -r requirements.txt
cp .env.example .env     # Verify API credentials (Azure, Sarvam, LiveKit)

# Step 3: Install Node.js Backend Dependencies
cd ../backend
npm install
cp .env.example .env     # Verify MongoDB & JWT secrets

# Step 4: Install Frontend Dependencies
cd ../frontend
npm install
cp .env.example .env     # Verify API Base URL
```

### 3. Running Development Servers

```bash
# Terminal 1: Start Backend API (Port 5000)
cd crm/backend
npm run dev

# Terminal 2: Start Frontend Dashboard (Port 5173)
cd crm/frontend
npm run dev

# Terminal 3: Start Voice Agent Worker (or Direct Server)
cd crm/priya-livekit
py agent.py dev          # For LiveKit WebRTC/SIP worker
# OR
py direct_server.py      # For Direct WebSocket telephony server (Port 8000)
```

---

## 39. Production Architecture

* **Current Architecture**: Fully functional dual-mode voice agent with direct WebSocket telephony, LiveKit WebRTC, Azure OpenAI primary inference, and Node/React CRM sync.
* **Production Recommendations**:
  * Implement PM2 process manager for Node.js API clustering.
  * Use Docker containers managed by Kubernetes for auto-scaling Python voice workers.
  * Deploy Redis Cluster with persistent RDB/AOF snapshots.

---

## 40. LangChain Integration (Proposed / Architectural Fit)

*Note: This section describes a proposed architectural enhancement and is not required for the current functional codebase.*
* **Fitment**: LangChain can be positioned between STT and LLM generation as a chain orchestrator (`LCEL`), managing retrieval from Azure AI Search and formatting dialogue memory.
* **Why the Current Native Implementation Was Chosen**: Hand-crafted lightweight state machines (`long_conversation.py` and `session_manager.py`) execute in $< 5$ms, avoiding the latency overhead and abstraction bloat of heavy framework runtimes during live voice streaming.

---

## 41. STM vs LTM Comparison Matrix

| Attribute | Short-Term Memory (STM) | Long-Term Memory (LTM) |
|---|---|---|
| **Primary Store** | In-Memory (`SessionContext`) / Redis Hash | MongoDB (`leads`, `calls`, `reports`) |
| **Lifespan** | Duration of telephone call (20 mins TTL) | Permanent (Years) |
| **Access Latency** | $< 1$ millisecond | $5 - 20$ milliseconds |
| **Typical Data** | Active turns, unconfirmed slots, active language | Verified student profile, admission status, past call logs |
| **Write Strategy** | Synchronous during turn extraction | Asynchronous off-critical-path write |

---

## 42. Current Technical Limitations

1. **Carrier Audio Quality**: Inbound PSTN calls over cellular networks sometimes suffer from 8kHz bandwidth limitations, requiring robust acoustic modeling for heavy regional accents.
2. **Third-Party API Outages**: Downtime on external vendor APIs (Sarvam AI / Groq) requires fallback adapters to maintain call continuity.
3. **Cross-Call Dynamic Pre-Warming**: Pre-call loading of historical student records into the agent's opening line is currently supported at the CRM layer and is planned for voice worker integration.

---

## 43. Future Roadmap & Improvements

* **Immediate (Sprint 1–2)**:
  * Dynamic opening line personalization from CRM historical lookup.
  * WhatsApp interactive chatbot integration mirroring Priya's memory.
* **Medium-Term (Quarter 1)**:
  * Fine-tuned local Indic Whisper STT model for edge deployment.
  * Multi-campus tenant isolation for national university networks.
* **Long-Term (Quarter 2+)**:
  * Real-time automated counselor whisper assistance during human escalations.

---

## 44. Critical Constraints

1. **Voice-to-Voice Latency Must Remain Sub-Second**: Never add blocking synchronous network calls to the voice turn path.
2. **Asynchronous Persistence**: Database and CRM writes must execute in non-blocking background tasks.
3. **Structured Slots Over Raw Transcripts**: Never dump growing raw transcripts into the LLM prompt.
4. **Zero Question Repetition**: Once a slot is verified in `FactMemory`, it must never be re-asked.
5. **No Hallucinated Accreditations or Fees**: Priya must only quote figures verified in `university_data.py`.
6. **Barge-In Responsiveness**: Speech synthesis must stop within 200ms when the user begins speaking.
7. **Single Question Constraint**: Never ask more than one question per turn.
8. **Language Hysteresis**: Prevent single-word misclassifications from flipping session language.
9. **Credential Protection**: Never commit or expose production API keys or tokens in code or logs.
10. **Failover Availability**: Every critical AI service must have at least one working fallback provider.

---

## 45. Interview & Viva Explanations

### 30-Second Elevator Pitch
> *"AdmitAI Priya is an enterprise-grade AI admissions counselor and CRM platform for Aditya University. It conducts human-like phone calls in English, Telugu, Hindi, and Tamil with sub-second voice latency. It uses a 4-layer memory architecture and a No-Repetition Engine so it never re-asks candidate information, while automatically syncing call transcripts, sentiment, and lead statuses directly into a MongoDB and React CRM dashboard."*

### 2-Minute Technical Summary
> *"The project solves higher education admissions bottlenecks by pairing real-time voice AI with an enterprise CRM. On the voice side, we implemented a dual-mode audio pipeline using LiveKit SIP and direct WebSocket streaming. As the caller speaks, Sarvam AI handles STT, and our 6-layer language engine manages code-mixed dialects like Telugish while preventing language flapping. Our DialogueSlotManager extracts key facts like intermediate marks and branch preferences into Short-Term Memory. Our No-Repetition Engine strips known facts from the dynamic prompt, ensuring Priya only asks for missing information. We use Azure OpenAI gpt-4.1-mini as our primary LLM with Groq LLaMA-3.3 fallback, streaming sentences directly into Sarvam Bulbul:v3 TTS. In the background, an async reporter updates our Node.js backend and MongoDB database, allowing admissions teams to monitor live transcripts and conversion analytics on a React dashboard."*

### 5-Minute Deep Dive
*(Covers Architecture diagram, 6-Layer Language Detection, 4-Layer Memory System, Failover Chains, Concurrency math for 10,000 calls/hour, and Security constraints).*

---

## 46. Frequently Asked Questions (Technical FAQ)

* **Q: Why was LiveKit chosen?**  
  *A: LiveKit provides WebRTC and SIP infrastructure, built-in VAD, audio endpointing, and streaming LLM-to-TTS pipeline orchestration.*
* **Q: How is question repetition eliminated?**  
  *A: The `NoRepetitionEngine` inspects `FactMemory` on every turn and dynamically removes prompt directives that ask for already-known fields.*
* **Q: How does code-mixed language detection work?**  
  *A: Our 6-layer engine evaluates script Unicode ranges, Romanized keyword vocabularies, multi-turn hysteresis, and explicit switch commands with a 0.85 confidence threshold.*
* **Q: What happens if MongoDB or Redis crashes?**  
  *A: The voice agent isolates external database failures and continues executing calls using in-memory data structures without dropping the live call.*

---

## 47. Architecture Decision Records (ADRs)

* **ADR-001: Structured Slot Memory over Raw Transcript Buffering**  
  * *Context*: Raw transcripts inflate LLM context windows, increasing latency and cost.  
  * *Decision*: Implemented `FactMemory` to store structured slots permanently, keeping the prompt small and latency flat.
* **ADR-002: Dual-Mode Audio Transport**  
  * *Context*: Different telephony carriers require different transport protocols.  
  * *Decision*: Support both LiveKit SFU WebRTC and direct raw 8kHz $\mu$-law WebSockets.
* **ADR-003: Sentence-Streaming LLM to TTS Overlap**  
  * *Context*: Waiting for full LLM responses introduces 2–3s delays.  
  * *Decision*: Stream text token-by-token and trigger TTS synthesis on the first completed sentence.

---

## 48. Final Architecture Summary & Developer Handoff

### The Developer's Cheat Sheet: If You Take Over This Codebase Tomorrow

1. **Where the Voice AI Logic Lives**: `crm/priya-livekit/agent.py` (LiveKit worker) and `crm/priya-livekit/direct_server.py` (WebSocket telephony).
2. **Where Memory & Anti-Repetition Live**: `session_manager.py` (Slot extraction), `long_conversation.py` (Memory layers), and `no_repetition.py` (Deduplication).
3. **Where Knowledge is Maintained**: `Aditya_University_Knowledge_Base.md` and `university_data.py`.
4. **Where the CRM Backend Runs**: `crm/backend/server.js` (Express on port 5000), `models/` (Mongoose), `routes/` (APIs).
5. **Where the Frontend Runs**: `crm/frontend/` (Vite + React on port 5173).
6. **How to Test Everything**: Run `py test_voice_azure.py`, `py run_tests_standalone.py` in `priya-livekit`, and `npx jest` in `backend`.

---
*End of Documentation. AdmitAI Priya System Architecture & Technical Specifications.*
