# ⚡ LATENCY OPTIMIZATION PROMPT (Phase 2: Reaching <500ms Human-Like Latency)

Use this detailed prompt with your AI assistant or agent to execute Phase 2 deep latency optimization.

---

## 🎯 Optimization Goal
Transform Priya voice agent response latency from **~1.2s** down to **<500ms** (perceived human conversational pace).

```
Target Latency Breakdown:
├─ EOU (Endpointing):          ~150ms - 250ms
├─ Time-to-First-Token (LLM):  ~150ms - 200ms
├─ Time-to-First-Byte (TTS):   ~100ms - 150ms
└─ Perceived Total:            < 500ms ✅
```

---

## 📋 Phase 2 Core Tasks & Architecture Requirements

### 1. Token-Level & Sentence-Level Streaming LLM Pipeline
- Stream tokens directly from Azure GPT-4.1-mini / Groq Llama-3.3 into the TTS queue as soon as the first syntactic punctuation or clause boundary (4–7 words) is reached.
- Eliminate full-sentence waiting when the first phrase can already begin synthesis.

### 2. Live Concurrent Pre-warming & Websocket Pooling
- Maintain open, warm websockets for Sarvam Bulbul TTS and STT.
- Ensure zero connection handshake delay on turn onset.

### 3. Aggressive 70+ Intent Fuzzy-Match Cache
- Expand `LatencyOptimizer` cache to 70+ topics covering:
  - Branch-specific specializations (SAP, Google Cloud, Microsoft, Deloitte, KPMG, PwC)
  - Detailed merit slabs (12th Board, JEE, EAPCET, ASAT)
  - Fee structures (Tuition, Hostel, Transport, Examination, Admissions)
  - Placements by department (Walmart, Amazon, TCS, Cisco)
  - Campus life, rules, bus routes, and accreditation facts

### 4. Dynamic Prompt Token Truncation
- Keep system prompt payload under 450 tokens.
- Cache tool definitions and dynamically attach only relevant tool schemas per turn.

### 5. Speculative Pre-generation
- On high-confidence partial STT hypothesis (e.g., student starts with "Can you tell me the fees for..."), start pre-fetching course fee data before the student finishes speaking.

---

## 🛠️ Verification & Latency Tracking
- Log per-turn TTFT, TTFB, and EOU in `latency_log.csv`.
- Run `plot_latency.py` to graph and verify median latency < 500ms.
