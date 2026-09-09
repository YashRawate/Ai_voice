# 🎙️ AdmitAI — AI Voice Calling Agent with CRM

> **A production-ready AI-powered voice calling agent integrated with a full-stack CRM platform for university admissions.**

AdmitAI is an end-to-end admission automation system built for **Aditya University**. At its core is **Priya** — an intelligent AI voice agent that makes real phone calls to prospective students, conducts natural multilingual conversations, collects admission details, and syncs everything to a live CRM dashboard in real-time.

---

## ✅ Working & Complete: The AI Calling Agent

The **AI Voice Calling Agent (Priya)** is the flagship feature of this project — fully functional and battle-tested with real phone calls.

### What It Does

| Capability | Status | Details |
|---|---|---|
| **Real Phone Calls** | ✅ Working | Inbound & outbound calls via Twilio + LiveKit SIP |
| **Multilingual Conversations** | ✅ Working | Telugu, Hindi, Tamil, English + auto-detection & code-switching |
| **Live STT → LLM → TTS Pipeline** | ✅ Working | Streaming speech-to-text, LLM reasoning, text-to-speech with sub-second overlap |
| **Lead Data Collection** | ✅ Working | Captures name, program interest, exam scores, city, visit preferences |
| **Knowledge-Grounded Answers** | ✅ Working | Answers ONLY from the university knowledge base — never hallucinates fees/stats |
| **Scholarship Lookup** | ✅ Working | Real-time scholarship calculation based on entrance exam scores |
| **Follow-Up Calls** | ✅ Working | Warm re-engagement calls with full context from previous conversations |
| **Auto Hang-Up** | ✅ Working | Gracefully ends the call after booking confirmation |
| **Live Dashboard Sync** | ✅ Working | Pushes transcript + collected details to the CRM dashboard in real-time |
| **LLM Failover Chain** | ✅ Working | Multi-provider fallback (Groq → Gemini → OpenRouter → Azure → Cerebras) |
| **Latency Tracking** | ✅ Working | Per-turn EOU/LLM/TTS latency logging to CSV |

### How the Voice Pipeline Works

```
📞 Phone Call (Twilio PSTN)
    │
    ▼
🔗 LiveKit SIP Bridge
    │
    ▼
🎤 Sarvam STT (saaras:v3)          ← Real-time speech recognition (11 Indian languages)
    │                                   Auto-detects Telugu/Hindi/Tamil/English per turn
    ▼
🧠 LLM (Groq llama-3.3-70b)       ← Admission counsellor persona with knowledge base
    │   + Function Tools:               Streams reply sentence-by-sentence
    │     • save_detail()               Max 25 words/reply, one question per turn
    │     • list_branches()             Uses university_data.py for exact facts
    │     • list_programs()
    │     • get_fee_structure()
    │     • check_scholarship()
    │     • schedule_visit()
    │     • end_call()
    ▼
🔊 Sarvam TTS (bulbul:v3)          ← Natural Indian voice synthesis
    │                                   Language-matched to caller (Telugu/Hindi/Tamil/English)
    ▼
📞 Back to Phone Call               ← ~1-2 second end-to-end latency
```

### Supported LLM Providers

The agent supports **9 LLM providers** with automatic failover:

| Provider | Model | Use Case |
|---|---|---|
| **Groq** (default) | llama-3.3-70b-versatile | Fast cloud inference (~1s) |
| **Gemini** | gemini-2.5-flash | Google AI alternative |
| **Azure OpenAI** | gpt-4.1-mini | Enterprise deployments |
| **Cerebras** | llama-3.3-70b / gpt-oss | Ultra-fast inference |
| **OpenRouter** | Any model | Multi-model access |
| **Anthropic** | claude-3.5-haiku | High-quality reasoning |
| **AWS Bedrock** | Various | AWS infrastructure |
| **HuggingFace** | Llama-3.3-70B | Open-source models |
| **Local (Ollama)** | qwen2.5:3b | Offline/dev testing |

### Making a Phone Call

```bash
# 1. Start the agent worker
cd priya-livekit
python agent.py dev

# 2. Make an outbound call (in another terminal)
python make_call.py +919876543210

# 3. Or test without a phone (uses your computer mic)
python agent.py console
```

### Call Flow

The agent follows a structured admission counselling flow:

1. **Greeting** — Introduces herself as Priya from Aditya University
2. **Program Interest** — Asks about preferred course (B.Tech, MBA, Pharmacy, etc.)
3. **Specialization** — Narrows down to specific branches (CSE, AI/ML, Data Science, etc.)
4. **Entrance Exams** — Asks about ASAT/JEE/EAPCET scores, calculates scholarship eligibility
5. **Academics** — Collects Class 10/12 percentages (one per turn)
6. **Location** — Current city for campus visit planning
7. **Next Step** — Books campus visit, virtual tour, or counselling session with exact date/time
8. **Closing** — Confirms booking and ends call gracefully

Every detail is saved to the CRM in real-time as it's collected.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AdmitAI Platform                         │
├──────────────┬──────────────────────┬───────────────────────────┤
│              │                      │                           │
│  Frontend    │     Backend          │   Voice Agent             │
│  (React)     │     (Express/Node)   │   (Python/LiveKit)        │
│              │                      │                           │
│  • Dashboard │  • REST API          │  • Priya AI Agent         │
│  • Analytics │  • JWT Auth + RBAC   │  • Sarvam STT/TTS        │
│  • Call Logs │  • MongoDB/Mongoose  │  • Multi-LLM Support     │
│  • Reports   │  • Gemini Extraction │  • Twilio SIP Bridge     │
│  • Team Mgmt │  • Webhook Handlers  │  • MCP Protocol          │
│  • CRM Views │  • Cron Scheduler    │  • University KB         │
│              │                      │                           │
└──────┬───────┴──────────┬───────────┴───────────┬───────────────┘
       │                  │                       │
       │     REST API     │    Webhook + WS       │  SIP/PSTN
       │                  │                       │
       ▼                  ▼                       ▼
   Browser            MongoDB              Twilio + LiveKit
```

---

## 📁 Project Structure

```
.
├── priya-livekit/               # 🎙️ AI Voice Calling Agent (Python)
│   ├── agent.py                 # Main agent — 1400 lines of production voice AI
│   ├── make_call.py             # Outbound call trigger script
│   ├── create_outbound_trunk.py # LiveKit SIP trunk setup
│   ├── university_data.py       # Complete Aditya University knowledge base
│   ├── reporter.py              # Real-time CRM dashboard sync
│   ├── latency.py               # Per-turn latency tracker
│   ├── translate.py             # Sarvam translation pipeline
│   ├── mcp_client.py            # Model Context Protocol bridge
│   ├── mcp_server.py            # MCP server for CRM tools
│   ├── TELEPHONY.md             # Twilio + LiveKit SIP setup guide
│   ├── Aditya_University_Knowledge_Base.md
│   ├── requirements.txt
│   └── sip/                     # SIP trunk & dispatch rule configs
│
├── backend/                     # ⚙️ Express + MongoDB API
│   ├── server.js                # Express bootstrap + scheduler
│   ├── config/db.js             # MongoDB connection
│   ├── middleware/               # JWT auth + RBAC + error handling
│   ├── models/                  # Mongoose schemas (User, Call, Report, etc.)
│   ├── routes/                  # REST endpoints (auth, calls, reports, analytics)
│   ├── services/                # Telephony, Gemini AI, scheduler
│   ├── scripts/seed.js          # Demo data seeder
│   └── utils/                   # JWT helpers, report generator
│
├── frontend/                    # 🖥️ React + Vite Dashboard
│   ├── src/
│   │   ├── App.jsx              # Router + RBAC route guards
│   │   ├── pages/               # Dashboard, Analytics, Reports, CRM views
│   │   ├── components/          # Shared layout components
│   │   ├── store/               # Zustand state management
│   │   └── lib/                 # API client, CSV export, demo data
│   └── vite.config.js
│
└── README.md                    # You are here
```

---

## 🚀 Quick Start

### Prerequisites

- **Node.js 20+** and **npm**
- **Python 3.9+**
- **MongoDB** (local or Atlas)
- API keys (see Environment Variables below)

### 1. Voice Agent Setup (the core feature)

```bash
cd priya-livekit
python -m venv .venv
.venv\Scripts\activate              # Windows (use: source .venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
python agent.py download-files      # One-time: fetch model files

# Test immediately (no phone needed)
python agent.py console

# Or run as a worker for real phone calls
python agent.py dev
```

### 2. Backend Setup

```bash
cd backend
npm install
cp .env.example .env               # Fill in real values
npm run dev                         # Runs on http://localhost:5000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env               # Set VITE_API_BASE_URL
npm run dev                         # Runs on http://localhost:5173
```

---

## 🔑 Environment Variables

### Voice Agent (`priya-livekit/.env`)

| Variable | Required | Description |
|---|---|---|
| `LIVEKIT_URL` | ✅ | `wss://<project>.livekit.cloud` |
| `LIVEKIT_API_KEY` | ✅ | LiveKit Cloud API key |
| `LIVEKIT_API_SECRET` | ✅ | LiveKit Cloud API secret |
| `SARVAM_API_KEY` | ✅ | Sarvam AI key (STT + TTS) |
| `GROQ_API_KEY` | ✅ | Groq API key (primary LLM) |
| `LLM_PROVIDER` | | `groq` (default), `gemini`, `azure`, `openrouter`, `local` |
| `LLM_FALLBACK` | | Comma-separated fallback providers |
| `MULTILANG` | | `true` to enable auto language detection |
| `OUTBOUND_TRUNK_ID` | | For outbound phone calls |

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `MONGO_URI` | ✅ | MongoDB connection string |
| `JWT_ACCESS_SECRET` | ✅ | JWT signing key |
| `GEMINI_API_KEY` | ✅ | For transcript AI extraction |
| `TELEPHONY_API_URL` | | External calling provider URL |
| `TELEPHONY_API_KEY` | | External calling provider key |

---

## 📞 Telephony Setup (Real Phone Calls)

The voice agent uses **LiveKit SIP** + **Twilio** for real phone calls:

### Inbound Calls
```
Caller dials your Twilio number
  → Twilio routes via Elastic SIP Trunk
  → LiveKit SIP endpoint accepts the call
  → Dispatches Priya agent to the room
  → Priya greets and conducts the admission call
```

### Outbound Calls
```bash
# After setting up Twilio Termination + LiveKit outbound trunk:
python make_call.py +919876543210
```

See [`priya-livekit/TELEPHONY.md`](priya-livekit/TELEPHONY.md) for the complete setup guide.

---

## 🧠 Key Technical Features

### Streaming Speech Pipeline
- **STT → LLM → TTS overlap** is built into LiveKit — Priya starts speaking on the first sentence, not after the full reply
- **Turn detection** is model-driven (Sarvam STT endpointing at ~70ms), not a fixed silence timer
- **Phonetic number normalization** converts digits to spoken words (₹2,75,000 → "two lakh seventy five thousand rupees")

### Multilingual Intelligence
- **Auto-detects** Telugu, Hindi, Tamil, English per turn via Sarvam STT
- **Code-switches** naturally (Telugish, Hinglish) — mirrors how urban Indians actually speak
- **Optional translate-out** mode: LLM composes in English, Sarvam localizes before TTS

### Safety & Reliability
- **Knowledge-grounded**: Every fact comes from the university knowledge base — never hallucinates
- **LLM failover chain**: Up to 9 providers with automatic fallback on 429/401 errors
- **Tool syntax stripping**: Prevents leaked JSON/function calls from being spoken aloud
- **History windowing**: Caps conversation context to keep latency flat on long calls
- **Graceful hang-up**: Waits for the goodbye line to finish before disconnecting

### CRM Integration
- **Real-time sync**: Collected details push to the dashboard as they're captured
- **AI transcript extraction**: Gemini 1.5 Flash parses call transcripts into structured reports
- **RBAC**: Four-role access control (admin, college_admin, officer, viewer)
- **Scheduled calls**: Cron-based scheduler with per-call timers

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Voice Agent** | Python, LiveKit Agents SDK, Sarvam AI (STT + TTS) |
| **LLM** | Groq (llama-3.3-70b), Gemini, Azure OpenAI, + 6 more providers |
| **Telephony** | Twilio SIP + LiveKit SIP Bridge |
| **Backend** | Node.js, Express 4, MongoDB + Mongoose |
| **AI Extraction** | Google Gemini 1.5 Flash |
| **Frontend** | React 19, Vite 8, Zustand, Recharts, Framer Motion |
| **Auth** | JWT (access + refresh tokens) with httpOnly cookies |
| **Styling** | Tailwind CSS v4 + glassmorphism |

---

## 📊 CRM Dashboard Features

- **Organization & College Management** — Multi-tenant with RBAC
- **Call Campaign Triggers** — Bulk or individual call dispatch
- **Live Call Monitoring** — Real-time transcript and status updates
- **AI-Generated Reports** — Post-call analysis with interest probability, topic breakdown, follow-up suggestions
- **Analytics Dashboard** — Call volume, conversion rates, response trends
- **CSV Export** — Download call data for external analysis
- **Team Management** — Invite and manage admission officers

---

## 🧪 Testing

```bash
# Voice agent tests
cd priya-livekit
python test_greetings.py            # Test greeting generation
python test_full_pipeline.py        # Full STT→LLM→TTS pipeline test
python test_dialogue_live.py        # Live multi-turn conversation test
python test_multilingual_live.py    # Multilingual switching test
python test_azure_agent.py          # Azure OpenAI integration test

# Backend
cd backend
node scripts/seed.js                # Seed demo data
```

---

## 📄 License

This project is proprietary software built for Aditya University admissions.

---

## 👨‍💻 Author

**Teki Karthik**

Built as a complete AI-powered admission automation platform — from voice AI to CRM dashboard.
