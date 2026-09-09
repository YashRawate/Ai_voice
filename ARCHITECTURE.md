# AdmitAI + Priya — Architecture Report

Read-only architecture analysis of the voice-AI admissions calling system at `e:\Final - Copy`.

---

## 1. PROJECT MAP

### Root
- `Aditya_University_Extracted_Data.txt` — raw source text used to hand-author `backend/data/knowledgeBase.js`.
- `.claude/settings.local.json` — Claude Code local settings (not part of app).

### `backend/` (Node.js + Express)

**Entry point**: `backend/server.js`
- Loads `dotenv`, creates `express()` app + raw `http.Server`.
- `connectDB().then(() => startScheduler())` — connects MongoDB (`backend/config/db.js`), then starts the cron scheduler (`backend/services/scheduler.js`) only after DB connects.
- Ensures `backend/audio/` exists (Priya TTS output dir), served statically at `/audio`.
- Middleware: `cors` (open, "tighten in production" comment), `express.json({limit:'2mb'})`, `express.urlencoded({extended:true})` (required for Twilio form-encoded webhooks), `cookie-parser`, `morgan('dev')`.
- Mounts routes (see below), then `errorHandler` middleware (`backend/middleware/errorHandler.js`).
- `mediaStream.setup(httpServer)` attaches the `/ws/media-stream` WebSocket server to the same HTTP server.
- `requiring services/vectorStore.js` (transitively, via groqService) auto-initializes the TF-IDF index at boot (see §4).
- `requiring services/ragStore.js` auto-loads BM25 chunks from `backend/data/*.txt` at boot via `loadDirectory()`.
- Start command: `npm start` → `node server.js` (or `npm run dev` → `node --watch server.js`). Listens on `PORT` env var, default `5000`.

**`backend/config/`**
- `db.js` — `connectDB()`, Mongoose connection to MongoDB.

**`backend/data/`**
- `knowledgeBase.js` — hand-curated array of 24 semantic documents (`id`, `text`, `metadata.section`) covering university overview/rankings/collaborations, courses (B.Tech, M.Tech, BCA/MCA, BBA, MBA, Executive MBA, Pharmacy), fees, scholarships, and facilities/placements. This is the corpus for `vectorStore.js`.
- `brochure.txt`, `courses.txt`, `facilities.txt`, `fee_structure.txt`, `scholarships.txt` — plain-text docs loaded by `ragStore.js` (BM25) at boot.

**`backend/db/`** (runtime data, JSON files acting as a lightweight persistence layer)
- `priya-calls.json` — call history (last 100 calls), written by `sessionStore.saveToHistory()`.
- `vectors.json` — cached TF-IDF vectors for `vectorStore.js` (versioned cache, `CACHE_VERSION = 3`).

**`backend/middleware/`**
- `auth.js` — JWT auth middleware for the AdmitAI platform routes.
- `errorHandler.js` — global Express error handler.

**`backend/models/`** (Mongoose schemas)
- `User.js`, `Organization.js` — auth/org structure.
- `College.js` — college entity.
- `Call.js` — AI call record (used by the non-Priya "platform" call/report flow).
- `Report.js` — structured post-call report (profile, summary, enrollmentProbability, topicAnalysis, sentimentTimeline, followUpRecommendations) — shape matches Gemini's JSON schema.

**`backend/routes/`**
- `auth.js` — login/register/JWT, uses `express-validator`.
- `orgs.js` — organization CRUD.
- `colleges.js` — college CRUD.
- `calls.js` — AdmitAI platform calls; `calls.js:6` requires `gemini.parseTranscript`, called at `calls.js:174` from a webhook handler that builds a `Report` from a transcript.
- `reports.js` — report retrieval endpoints.
- `analytics.js` — analytics/aggregation endpoints.
- `documents.js` — `/api/priya/documents` — admin endpoints for managing RAG source docs (likely wraps `ragStore.addDocument`/`loadDirectory`).
- `priya.js` — **Priya admin API**: `POST /trigger-call`, `GET /sessions/:session_id`, `GET /calls`; contains `FALLBACK_SCRIPT` (12-step canned script) and mock-call simulation (`runMockSimulation`).
- `priyaWebhook.js` — **Twilio webhooks**: `GET /test`, `POST /call-start`, `POST /call-respond` (legacy `<Record>`-based turn loop, still present but largely superseded by the WebSocket Media Stream path), `POST /call-status`.

**`backend/scripts/`**
- `seed.js` — DB seeding script for orgs/colleges/users.
- `testPipeline.js` — manual test harness for the STT/LLM/TTS pipeline.

**`backend/services/`**
- `mediaStream.js` — **core real-time voice handler**. `MediaSession` class: μ-law codec (G.711, correct BIAS=0x84), WAV build/parse/resample, RMS-based VAD, per-turn pipeline (`_runPipeline`), Polly/Sarvam TTS routing, WebSocket server setup at `/ws/media-stream`.
- `groqService.js` — Groq LLM turn handler (`callPriyaAPI`): extraction → smartAdvance → RAG → system prompt → Groq call → step-question enforcement.
- `flowController.js` — 12-step flow definitions (`STEPS`, `STEP_QUESTIONS`), `extractDataFromText()`, `isQuestion()`, `smartAdvance()`, `buildSystemPrompt()`.
- `priya.js` — thin delegator: `callPriyaAPI` → `groqService.callPriyaAPI`. Used by both `mediaStream.js` and `routes/priyaWebhook.js`/`routes/priya.js`.
- `sessionStore.js` — in-memory session store + `priya-calls.json` history file.
- `sarvam.js` — Sarvam AI STT (`transcribe`), TTS (`synthesize`), Translate (`translate`).
- `ragStore.js` — BM25 lexical search over `backend/data/*.txt`.
- `vectorStore.js` — TF-IDF cosine-similarity "vector" search over `knowledgeBase.js`, cached to `db/vectors.json`.
- `gemini.js` — Gemini 1.5 Flash transcript-to-structured-report extraction (`parseTranscript`) — **not used in the live call loop**; used by `routes/calls.js` and `services/call-orchestrator.js`.
- `call-orchestrator.js` — orchestrates the AdmitAI platform's AI-call → transcript → Gemini report pipeline (separate from Priya's live-call system).
- `scheduler.js` — `node-cron` based: sweeps `Call` docs with `status:'scheduled'` whose time has passed and dispatches via `telephony.js`; also supports one-shot per-call cron jobs.
- `sttService.js` — (platform) STT helper for the non-Priya call pipeline.
- `telephony.js` — `dispatchCall()` — generic telephony dispatch used by the scheduler/orchestrator (separate from `twilioOutbound.js`).
- `twilioOutbound.js` — `makeOutboundCall()` — Priya-specific Twilio outbound call creation, sets up `call-start`/`call-status` webhook URLs.

**`backend/tests/`** — Jest test suite: `analytics.test.js`, `auth.test.js`, `call-orchestrator.test.js`, `gemini.test.js`, `telephony.test.js`, `webhook.test.js`. Uses `mongodb-memory-server` + `supertest`. **No tests target `mediaStream.js`, `groqService.js`, `flowController.js`, or `priyaWebhook.js`'s call-start/call-respond/call-status routes** (the live Priya call flow).

**`backend/utils/`**
- `reportGenerator.js` — heuristic fallback report generator (keyword-based topic scoring, sentiment timeline, enrollment-probability heuristic, follow-up recommendations) used when Gemini is unavailable or returns no transcript.
- `tokenUtils.js` — JWT helper utilities.

### `frontend/` (React + Vite)
- `vite.config.js`, `eslint.config.js`, `package.json` — Vite/React/ESLint config.
- `src/main.jsx` — React root render.
- `src/App.jsx` — router setup (`react-router-dom`), route guards (`ProtectedRoute`, `OrgOnlyRoute`, `CollegeScopedRoute`) based on Zustand `useStore` user/role.
- `src/theme.js` — UI theme config.
- `src/store/useStore.js` — Zustand global store (user/auth/session state).
- `src/lib/api.js` — generic AdmitAI platform API client (axios wrapper).
- `src/lib/priyaApi.js` — Priya-specific API client (`trigger-call`, `sessions/:id`, `calls`).
- `src/lib/csv.js` — CSV export helper.
- `src/lib/dummyData.js` — mock/demo data for UI.
- `src/components/DashboardLayout.jsx` — shared dashboard shell/layout.
- `src/pages/Landing/`, `Login/`, `CreateOrg/` — auth/onboarding pages.
- `src/pages/OrgDashboard/`, `CollegeDashboard/`, `Colleges/`, `CollegeDetail/`, `Analytics/`, `Team/`, `Settings/`, `Profile/` — AdmitAI platform pages.
- `src/pages/StudentReport/` — renders a `Report` (Gemini/heuristic output).
- `src/pages/LiveMonitoring/` — live call monitoring view.
- `src/pages/PriyaDashboard/`:
  - `index.jsx` — main Priya dashboard page.
  - `TriggerCall.jsx` — form to call `POST /api/priya/trigger-call`.
  - `StepProgressBar.jsx` — visualizes the 12-step flow progress (`step_index`).
  - `TranscriptViewer.jsx` — renders `session.transcript`.
  - `ConversationStats.jsx` — call stats/metrics.
  - `CallHistory.jsx` — renders `GET /api/priya/calls` (from `priya-calls.json`).

---

## 2. CALL FLOW (END-TO-END)

This traces the **live (Media Streams) path**, which is the active design per `mediaStream.js:1-8` and `priyaWebhook.js:104-144`. The older `<Record>`-based `/webhook/call-respond` loop in `priyaWebhook.js:146-292` remains in the codebase as a secondary/legacy path but is bypassed once `<Connect><Stream>` takes over.

### Step-by-step sequence

1. **Trigger call** — `backend/routes/priya.js:167` `POST /api/priya/trigger-call`
   - Input: `{ phone, name, language, style, audience, gender, smart_mode }` from `TriggerCall.jsx`.
   - Creates a session via `sessionStore.create()` (`backend/services/sessionStore.js:30`) — `step:'greeting'`, `step_index:0`, empty `collected`.
   - Calls `twilioOutbound.makeOutboundCall()` (`backend/services/twilioOutbound.js:22`) → **Twilio API** `client.calls.create()` with `url: /webhook/call-start?session_id=<id>` and `statusCallback: /webhook/call-status?session_id=<id>`.
   - `sessionStore.mapCallSid(callSid, sessionId)` links Twilio's CallSid to the session.
   - If Twilio isn't configured, falls back to mock mode (`runMockSimulation`).

2. **Twilio connects the call → `POST /webhook/call-start`** — `backend/routes/priyaWebhook.js:110`
   - Input: Twilio form body (`CallSid`), query `session_id`.
   - Maps `CallSid → sessionId` again (defensive) via `sessionStore.mapCallSid`.
   - Output: TwiML with `<Say voice="Polly.Aditi">` (greeting, via **Twilio/Polly TTS**) immediately, followed by `<Connect><Stream url="wss://.../ws/media-stream">`.
   - No external AI call yet — this responds instantly.

3. **WebSocket connects → `wss.on('connection')`** — `backend/services/mediaStream.js:516`
   - Twilio sends a `start` event containing `callSid`/`streamSid`.
   - `sessionStore.getByCallSid(callSid)` resolves the session (`mediaStream.js:532`).
   - Creates a `MediaSession` instance, calls `mss.greet()` (`mediaStream.js:483`).
   - On the **first connection** (`step_index === 0`), `greet()` just updates session state (`status:'in-progress'`, `step:'greeting'`, appends the greeting to `transcript`) — the actual greeting audio was already spoken by `<Say>` in step 2.
   - On **mid-call reconnects** (after a Polly `<Say>`), `greet()` sets a 900ms cooldown then `state='listening'`.

4. **Student speaks → VAD chunking** — `MediaSession.onChunk()` (`mediaStream.js:180`)
   - Input: base64 μ-law 20ms audio chunks (`media` events, `track:'inbound'`).
   - Decodes μ-law → PCM16, computes RMS energy (`rms()`, `mediaStream.js:140`).
   - State machine: `listening` → `recording` (energy > `SPEECH_RMS_THRESHOLD=200`) → accumulates chunks until 800ms silence (`SILENCE_CHUNKS_END=40`) with at least 200ms of voice (`MIN_SPEECH_CHUNKS=10`), or hits `MAX_SPEECH_CHUNKS=500` (10s cap).
   - On end-of-speech → `_onEndOfSpeech()` → `_pipeline(chunks)`.

5. **Pipeline step 1 — STT** — `_runPipeline()` (`mediaStream.js:243`)
   - Assembles PCM chunks into a WAV buffer (`buildWav`).
   - Calls **Sarvam STT**: `sarvam.transcribe(wavBuffer, preferredLang)` (`mediaStream.js:268`), 7s timeout (`T_STT`).
   - Output: `{ transcript, language_code }`. On failure, increments persisted `sttFailCount`; after 3 consecutive failures, says a goodbye via Polly and marks session `status:'failed'`.
   - Appends `{ role:'Student', text }` to `session.transcript`.

6. **Pipeline step 2 — Translate-in** (non-English only)
   - Calls **Sarvam Translate**: `sarvam.translate(studentText, detectedLang, 'en-IN', opts)` (`mediaStream.js:313`), 4s timeout (`T_TRANSLATE`). On failure, falls through with original text.

7. **Pipeline step 3 — Groq LLM turn** — `priyaService.callPriyaAPI(sessionId, englishText)` (`mediaStream.js:328`, delegates to `backend/services/groqService.js:33`)
   - `flow.extractDataFromText()` — regex extraction of name/marks/course/exam/location.
   - `flow.isQuestion()` + fee-step affirmative override.
   - `flow.smartAdvance()` — determines next `step`/`step_index`/`collected`.
   - `vectorStore.search()` — TF-IDF RAG retrieval (skipped for early steps).
   - `flow.buildSystemPrompt()` — builds the Groq system prompt.
   - **Groq API**: `groq.chat.completions.create({ model:'llama-3.1-8b-instant', messages, max_tokens:60, temperature:0.65 })` (`groqService.js:87`), 5s timeout (`T_GROQ`).
   - Step-question enforcement (`groqService.js:97-112`).
   - Output: `{ reply, step, step_index, collected }`. On Groq failure, falls back to `flow.STEP_QUESTIONS[step]`.
   - Session updated: `step`, `step_index`, merged `collected`, appends `{ role:'Priya', text: reply }` to transcript.

8. **Pipeline step 4 — Translate-out + TTS**
   - If target language needs translation and isn't Polly-supported (not `en-IN`/`hi-IN`), calls **Sarvam Translate** again (`mediaStream.js:358`) — but only translates the mandatory `STEP_QUESTIONS[step]`, not the full reply, to bound audio length.
   - `_say()` (`mediaStream.js:389`) routes TTS:
     - `en-IN`/`hi-IN` and `pollyFailCount < 2` → `_sayPolly()`: **Twilio `calls(callSid).update({ twiml })`** with `<Say voice="Polly.Aditi">` + `<Connect><Stream>` (re-attaches the WS). This is **Polly via Twilio**.
     - Otherwise → `_sayWithSarvam()`: **Sarvam TTS** `sarvam.synthesize()`, then streams μ-law-encoded audio back over the existing WebSocket as `media` events.

9. **Loop or end**
   - If `step === 'end'` or `step_index >= 11`: `sessionStore.update({status:'completed'})`, `sessionStore.saveToHistory()`, then `ws.close()` after 2s.
   - Otherwise: `state = 'listening'` and the loop returns to step 4 (VAD) for the next turn.

10. **Hangup / disconnect** — `ws.on('close')` (`mediaStream.js:558`)
    - If `session.pendingReconnect` is true (expected post-`calls.update()` reconnect), clears the flag and does nothing.
    - Otherwise, if session was `in-progress`/`calling`, marks `status:'completed'`, computes `duration`, and calls `saveToHistory()`.

11. **Twilio call-status webhook** — `POST /webhook/call-status` (`priyaWebhook.js:297`)
    - Input: `CallStatus`, `CallDuration`, query `session_id`.
    - Maps Twilio status (`completed`/`failed`/`busy`/`no-answer`/`canceled`) to session `status`, updates `duration`, calls `saveToHistory()` again (overwrites the WS-close estimate with Twilio's authoritative duration).

12. **Dashboard polling** — `GET /api/priya/sessions/:session_id` (`priya.js:228`) and `GET /api/priya/calls` (`priya.js:253`) are polled by `PriyaDashboard` pages to show live transcript/step/duration and call history.

### ASCII sequence diagram

```
 Twilio                Backend (Express + WS)              External APIs
   |                         |                                   |
   |--POST /api/priya/trigger-call (admin) ----------------------|
   |                         |--calls.create()------------------>| Twilio REST
   |<--CallSid---------------|<----------------------------------|
   |                         |
   |--POST /webhook/call-start (session_id)-->|
   |                         |--sessionStore.mapCallSid()
   |<--TwiML <Say Polly.Aditi>+<Connect><Stream>--|              Polly (via Twilio)
   |==WS connect /ws/media-stream================>|
   |--{event:start, callSid, streamSid}---------->|
   |                         |--sessionStore.getByCallSid()
   |                         |--mss.greet() (state update only)
   |
   |==media (20ms mu-law chunks, inbound)========>|
   |                         |--VAD: listening->recording->detect end of speech
   |                         |
   |                         |--sarvam.transcribe(wav)----------->| Sarvam STT
   |                         |<--{transcript, language_code}------|
   |                         |
   |                         |--sarvam.translate(in)------------->| Sarvam Translate
   |                         |<--english text----------------------|
   |                         |
   |                         |--groqService.callPriyaAPI()
   |                         |   extract -> smartAdvance -> RAG (vectorStore TF-IDF, local)
   |                         |   buildSystemPrompt -> groq.chat.completions.create()
   |                         |--------------------------------->| Groq LLM (llama-3.1-8b-instant)
   |                         |<--{reply, step, step_index}-------|
   |                         |
   |                         |--sarvam.translate(out, step question only)->| Sarvam Translate
   |                         |<--translated step question--------|
   |                         |
   |   (Polly path)          |--calls(callSid).update(twiml <Say>+<Connect><Stream>)-->| Twilio REST (Polly TTS)
   |<==WS disconnect==========|  (pendingReconnect=true)
   |==WS reconnect============>|  cooldown 900ms -> listening
   |
   |   (Sarvam path)          |--sarvam.synthesize(text)--------->| Sarvam TTS
   |                         |<--wav audio-------------------------|
   |<==media (mu-law chunks)==|  streamed over open WS
   |
   |  ... loop steps 4-9 per turn until step === 'end' ...
   |
   |--{event:stop} / WS close-->|
   |                         |--sessionStore: status='completed', saveToHistory()
   |--POST /webhook/call-status (CallDuration)-->|
   |                         |--sessionStore: status mapped, duration set, saveToHistory()
   |
 [Dashboard]---GET /api/priya/sessions/:id / /api/priya/calls --> sessionStore (poll)
```

---

## 3. LLM PROCESS

### System prompt construction — `flowController.js:206` `buildSystemPrompt(session, ragResults, prevStep)`

For each turn it assembles:
- **Persona/tone**: "You are Priya, an enthusiastic admission counsellor at Aditya University... speak naturally and warmly, like a real person." + **"Reply in 1-2 short sentences maximum."** (`flowController.js:234-235`).
- **Persuasive goal**: explicit instruction to "gently convince this student that Aditya University is a great choice... be positive, confident, and encouraging" (`flowController.js:237`).
- **Mandatory step-question enforcement**: `YOUR REPLY MUST ALWAYS END WITH THIS EXACT QUESTION (copy it word for word): "${nextQ}"` where `nextQ = STEP_QUESTIONS[step]` (`flowController.js:239-240`).
- **Response-type guidance**: how to react if the student gave info vs. asked a question vs. went off-topic, plus "NEVER invent information not in FACTS or the student's own words" (`flowController.js:242-247`).
- **Early-step fact suppression**: for `greeting/name/10th/inter/course` steps, an extra instruction `noFacts` forbids sharing any university info/fees/scholarships at that point (`flowController.js:224-227`).
- **Fee-delivery transition logic**: when `prevStep === 'fee'`, an extra `feeDelivery` instruction tells the LLM to "Start your reply by sharing the fee structure from FACTS, then ask the mandatory question" (`flowController.js:230-232`).
- **Student profile** (collected fields so far — name, marks_10, marks_inter, interest, exam/score, location) is appended "for context only — do not reference it in your reply" (`flowController.js:249`).
- **FACTS**: top RAG results (`ragResults`), each truncated to 200 chars and joined with `|` (`flowController.js:220-222`).

### Tool/function calling — NONE

`groqService.js:87` calls `groq.chat.completions.create({ model, messages, max_tokens: 60, temperature: 0.65 })` with **no `tools` or `function_call`/`tool_choice` parameter**. There is no Groq-side tool/function calling at all.

Instead, the system implements a **regex-based extraction + deterministic step machine**:
1. `flow.extractDataFromText(message)` (`flowController.js:64`) — regex-extracts `name`, `marks_10`, `marks_inter`, `interest` (course), `entrance_exam`, `entrance_score`, `location` from the raw student utterance (after spoken-number normalization).
2. `flow.isQuestion(message)` (`flowController.js:120`) — keyword/`?`-based question detection, with a fee-step affirmative override in `groqService.js:48-51`.
3. `flow.smartAdvance(session, extracted, studentAskedQuestion)` (`flowController.js:130`) — merges extracted data into `collected`, enforces a required-field gate (name → marks_10 → marks_inter → interest, in that order), then advances `step_index` (holding at `index >= 5` if the student asked a question).
4. Post-LLM, `groqService.js:104-112` **forcibly rewrites** the LLM's reply if it doesn't end with the exact `STEP_QUESTIONS[step]` string — stripping any trailing question the model invented and appending the canonical one.

So the LLM is used purely for **natural-language acknowledgement generation**; all flow control, data capture, and the final question are deterministic/regex-driven.

### Conversation history

- `session.transcript` is an array of `{ role: 'Student'|'Priya', text, timestamp }`, appended after every STT result and every LLM reply (`mediaStream.js:298-300`, `345-346`).
- Per-turn, `groqService.js:78-84` builds `messages` as: 1 system message + the **last 2 transcript turns** (`session.transcript.slice(-2)`, mapped to `user`/`assistant` roles) + the current student message as the final `user` message. So at most 4 messages total (system + 2 history + 1 current) are sent to Groq — a deliberately tiny context window to keep latency and token usage low.

### Agent loop

- **One LLM call per conversational turn** — no internal agent loop, no retries-with-reasoning, no multi-step planning. The "loop" is the outer VAD→STT→LLM→TTS cycle in `mediaStream.js`, driven by audio chunks, not by the LLM.
- `temperature: 0.65`, `max_tokens: 60` (`groqService.js:30-31`, comment: "60 tokens: enough for a 1-sentence answer + the step question").
- **Stopping condition**: `step === 'end'` or `step_index >= 11` (`mediaStream.js:374`, `priyaWebhook.js:278`) → session marked `completed`, history saved, WS closed after 2s.
- **Fallback on Groq error/empty reply**:
  - Empty/falsy completion content → default `'Thank you for that. Could you please tell me more?'` (`groqService.js:94-95`).
  - Groq API error or timeout (`T_GROQ=5000ms`) → caught in `mediaStream.js:333-339`, replies with `flow.STEP_QUESTIONS[step]` (re-asks the current step's question) rather than a generic error message.
  - In `priyaWebhook.js:259-265` (legacy `<Record>` path), Groq failure falls back to `'Thank you for that. Please go on.'` and keeps the previous step.

### Where Gemini fits — NOT part of the live call loop

- `backend/services/gemini.js` defines `parseTranscript({ call, transcript, webhookPayload })`, which sends the full call transcript to **Gemini 1.5 Flash** (`gemini-1.5-flash`, `responseMimeType:'application/json'`, `temperature:0.2`) with a strict JSON-schema prompt (`gemini.js:37-74`) to extract: profile (name, phone, email, exam, course interest, marks, entrance score, city), summary, enrollment probability, sentiment, topic-analysis scores, sentiment timeline, and follow-up recommendations.
- **Callers**: `backend/routes/calls.js:6,174` (a webhook handler for the AdmitAI platform's AI-call pipeline) and `backend/services/call-orchestrator.js:4,22`. **Neither is part of `mediaStream.js`, `groqService.js`, `flowController.js`, or the Priya webhook/trigger-call routes.**
- Confirmed: Gemini is used **only for post-call structured report generation** for the separate AdmitAI "platform" calling system (`Call`/`Report` Mongoose models), feeding `frontend/src/pages/StudentReport`. If Gemini fails or the transcript is empty, `gemini.js:86-87,144-146` falls back to the heuristic `generateReport()` in `backend/utils/reportGenerator.js`.
- Priya's live conversational loop uses **Groq exclusively**.

---

## 4. RAG / KNOWLEDGE GROUNDING

There are **two separate retrieval systems** in this codebase, both purely lexical/statistical — **neither uses embeddings from an embedding API**.

### `vectorStore.js` — TF-IDF cosine similarity (used live)
- `backend/services/vectorStore.js` builds, for each of the 24 documents in `backend/data/knowledgeBase.js`, a **TF-IDF term-weight vector** (`toVector()`, `vectorStore.js:65-84`): term frequency (log-normalized) × smoothed IDF, L2-normalized so cosine similarity = dot product.
- `search(query, topK)` (`vectorStore.js:153-163`) tokenizes the query the same way and computes cosine similarity against every document vector, returning the top-K by score.
- This is **NOT a real embedding-based vector DB** (no OpenAI/Sarvam/Cohere embeddings, no ANN index like FAISS/Chroma/Pinecone). It is a from-scratch TF-IDF implementation; the comment block (`vectorStore.js:1-14`) explicitly frames it as "Behaves like ChromaDB's local mode" but the underlying math is classic TF-IDF, not dense embeddings.
- Cached to `backend/db/vectors.json` (`CACHE_VERSION=3`) for fast reload; `initialize()` auto-runs at module load (boot time), `rebuild()` is available for manual refresh.
- **This is the store actually queried in the live call**: `groqService.js:70` calls `vectorStore.search(ragQuery, ragTopK)`.

### `ragStore.js` — BM25 (loaded but largely unused in the live path)
- `backend/services/ragStore.js` chunks `backend/data/*.txt` files (`brochure.txt`, `courses.txt`, `facilities.txt`, `fee_structure.txt`, `scholarships.txt`) into ≤500-char chunks at paragraph/sentence boundaries, computes classic **BM25** (k1=1.5, b=0.75, true IDF) over them.
- `loadDirectory()` auto-runs at module load.
- It is `require`d by `groqService.js:20` and commented as "BM25 fallback while vectors build", but `groqService.js` **never calls `ragStore.search()`** in the code as written — only `vectorStore.search()` is invoked (`groqService.js:70`). So `ragStore` is effectively dead weight in the live pipeline (loaded, indexed, but unused for retrieval) unless `routes/documents.js` exercises it for document management.

### How retrieval flows into the prompt
- `groqService.js:60-70`: RAG is **suppressed entirely** (`ragTopK = 0`) for `DATA_COLLECTION_STEPS = {greeting, name, 10th, inter, course}`. For other steps, `ragTopK = 3` if the student asked a question, else `2`.
- `ragQuery = [message, collected.interest, step].filter(Boolean).join(' ')`.
- `ragResults = vectorStore.search(ragQuery, ragTopK)`.
- `flowController.js:220-222`: `facts = ragResults.map(r => r.text.substring(0,200)).join(' | ')`, injected into the prompt as `FACTS: ${facts}` (`flowController.js:250`).

### Factual info categories — grounding source

| Category | Source | Grounded via |
|---|---|---|
| University overview/rankings/collaborations | `knowledgeBase.js` (`university_*`) | TF-IDF RAG (`vectorStore`) |
| Courses (B.Tech, M.Tech, BCA/MCA, BBA, MBA, Pharmacy) | `knowledgeBase.js` (`courses_*`) | TF-IDF RAG (`vectorStore`) |
| Fees | `knowledgeBase.js` (`fees_*`); also `backend/data/fee_structure.txt` for BM25 store | TF-IDF RAG (live); BM25 store loaded but unused |
| Scholarships | `knowledgeBase.js` (`scholarships_*`); also `scholarships.txt` | TF-IDF RAG (live) |
| Facilities/hostel/placements | `knowledgeBase.js` (`facilities_*`); also `facilities.txt` | TF-IDF RAG (live) |
| Fallback fee/scholarship/transport figures (₹1.2L tuition, ₹80K hostel, 30% scholarship, ₹18K transport pass) | `backend/routes/priya.js` `FALLBACK_SCRIPT` (`priya.js:52-75`) | **Hardcoded**, used only when Groq is unreachable (mock-mode fallback path) |
| Step questions / flow goals | `flowController.js` `STEPS`, `STEP_QUESTIONS` | **Hardcoded** (deterministic flow, not RAG) |

### Where a real embedding-based pipeline would slot in

There is no embedding-API-backed vector DB; if one were added:
- Replace `vectorStore.toVector()`/`build()` (`backend/services/vectorStore.js:65-149`) with calls to an embedding API (e.g., Sarvam's embedding endpoint if available, or any provider) to produce dense vectors for each `knowledgeBase.js` document, and store them in a real vector DB (Chroma/FAISS/pgvector) instead of `db/vectors.json`.
- `vectorStore.search()` (`vectorStore.js:153-163`) would call the embedding API on the query and perform ANN search against the vector DB.
- To ingest PDF brochures directly, `backend/data/knowledgeBase.js` (currently a hand-written JS array) would be replaced/augmented by a PDF ingestion step using `pdf-parse` (already a dependency, currently unused for this purpose) — chunk PDF text, embed, and upsert into the vector DB. `backend/routes/documents.js` would be the natural place to add an upload-and-ingest endpoint.
- `groqService.js:70` (`vectorStore.search(ragQuery, ragTopK)`) and `flowController.js:220-222` (fact formatting) would need no structural change — only the underlying `search()` implementation changes, since the calling contract (`{source, text, score}` array) can remain the same.

---

## 5. FLOW CONTROL

**The backend deterministic state machine (`flowController.js` `smartAdvance`) is in control**, not the LLM. The LLM only phrases the acknowledgement; the step, question, and data-collection gating are fully backend-driven (and forcibly re-applied post-hoc, see §3).

### Session object shape — `sessionStore.create()` (`sessionStore.js:30-57`)

In-memory object `sessions[sessionId]`, persisted (partially, summarized) to `backend/db/priya-calls.json`:

| Field | Purpose |
|---|---|
| `session_id` | UUID, primary key |
| `call_sid` | Twilio CallSid (set via `mapCallSid`) |
| `phone`, `name` | Student contact/name from trigger-call |
| `status` | `'calling'` → `'in-progress'` → `'completed'`/`'failed'` |
| `preferred_language` | Admin-locked language (`en-IN`/`hi-IN`/`te-IN`/null=auto) |
| `detected_language` | Runtime-detected language (from Sarvam STT) |
| `style`, `audience`, `gender`, `smart_mode` | Voice/translation configuration for Sarvam |
| `step`, `step_index` | Current position in the 12-step flow (0-11) |
| `collected` | `{ name, marks_10, marks_inter, interest, location, entrance_exam, entrance_score }` |
| `transcript` | `[{ role:'Student'|'Priya', text, timestamp }]` — full conversation log |
| `start_time` | ISO timestamp, used to compute live duration |
| `duration` | Final call duration (seconds) |
| `sttFailCount` | Consecutive Sarvam STT failures (persisted across WS reconnects) |
| `pollyFailCount` | Consecutive Polly `calls.update()` failures (persisted) |
| `pendingReconnect` | Flag set after a successful Polly `<Say>` so `ws.on('close')` doesn't treat the expected reconnect as a hangup |

**Persistence**: All live state lives in the in-memory `sessions`/`callSidMap` objects in `sessionStore.js:9-10`. `saveToHistory()` (`sessionStore.js:80-100`) writes a **summary** (`session_id, phone, name, started_at, duration, steps_completed, status, detected_language` — NOT the full transcript or `collected`) to `backend/db/priya-calls.json`, capped at the most recent 100 calls.

### `smartAdvance()` logic (`flowController.js:130-184`)

1. Merges `extracted` fields into `collected` (`c`), with two guards:
   - `name` is only accepted while `currentStep` is `greeting` or `name` (prevents later "I am ..." phrases from overwriting the collected name).
   - The generic `_pct` fallback (a bare percentage with no keyword context) is only applied during `greeting/name/10th/inter` steps, and is routed to `marks_inter` first if `currentStep === 'inter'`.
2. **Required-field gate** (`flowController.js:163-169`): checks `has(c.name)`, then `has(c.marks_10)`, then `has(c.marks_inter)`, then `has(c.interest)` — each must be a non-empty trimmed string. The first missing field forces `step`/`step_index` back to that field's collection step (`name`→1, `10th`→2, `inter`→3, `course`→4), **regardless of where the conversation otherwise is**.
3. Once all four required fields are present, the **optional phase** begins: `idx = max(session.step_index, 4)`.
4. **studentAskedQuestion hold**: if the student asked a question AND `idx >= 5` (fee/exam/scholarship/location/transport/queries), the step **holds** (`next = idx`) so the LLM can answer the question using RAG facts before advancing. At `idx === 4` (course), holding is disabled because the required-field gate already guarantees `interest` is set.
5. Otherwise `next = min(idx + 1, 11)`; `step = STEPS[next].name` (or `'end'` if out of range).

### Student-vs-parent branching

A search for `"parent"` across `backend/` (excluding `node_modules`) returned **no matches in source code**. The only "parent/student" distinction appears in `gemini.js:38` ("a prospective student (or parent)") inside the Gemini extraction prompt for the **separate** AdmitAI platform — there is no parent-specific flow, field, or branching logic anywhere in the Priya call flow (`flowController.js`, `mediaStream.js`, `groqService.js`, `sessionStore.js`).

### Guardrails

- **Input validation**: `express-validator` is used only in `backend/routes/auth.js`. **Priya's webhook/trigger-call routes (`priyaWebhook.js`, `priya.js`) have no request validation** beyond basic existence checks (e.g., `if (!phone) return res.status(400)...` in `priya.js:179`).
- **Turn/iteration caps**:
  - `MAX_SPEECH_CHUNKS = 500` (10s max recording per turn) (`mediaStream.js:151`).
  - `MIN_SPEECH_CHUNKS = 10` (200ms minimum before STT) (`mediaStream.js:150`).
  - `MAX_TOKENS = 60` per Groq reply (`groqService.js:31`).
  - `T_PIPELINE = 15_000ms` hard ceiling per turn — resets `state = 'listening'` if exceeded (`mediaStream.js:158, 227-231`).
  - 12-step flow itself caps total conversation length (`step_index` 0-11).
- **Escalation/human-handoff**: none found. No transfer-to-human, no `<Dial>` to a human agent, no "escalate" logic in the live call path (the heuristic `reportGenerator.js:54` mentions "Escalate to senior admission counsellor" but that's only a *post-call follow-up recommendation* for the admin dashboard, not a live-call action).
- **Forced call-ending**: `step === 'end' || step_index >= 11` → `status:'completed'`, `saveToHistory()`, `ws.close()` after a 2s delay (`mediaStream.js:374-380`); same condition triggers `playAndHangup()`/`sayAndHangup()` in the legacy `<Record>` path (`priyaWebhook.js:278-281`).

### Failure-mode behavior

- **Silence (VAD)**: If recording never reaches `MIN_SPEECH_CHUNKS` before 800ms of silence, `_onEndOfSpeech()` isn't triggered — state simply stays `recording` until either real speech resumes or `MAX_SPEECH_CHUNKS` (10s) forces an end-of-speech. If the resulting clip is `<500ms`, the pipeline aborts and returns to `listening` (`mediaStream.js:254-259`).
- **Hangup**: `ws.on('close')` (`mediaStream.js:558-580`) — if `pendingReconnect` is set, treated as expected (Polly reconnect); otherwise marks session `completed` with computed `duration` and saves history. The subsequent `call-status` webhook (`priyaWebhook.js:297`) overwrites with Twilio's authoritative `CallDuration`.
- **Invalid/empty STT**: If `sttResult.transcript` is empty, `state = 'listening'` and the turn is silently dropped — no reply spoken, no transcript entry (`mediaStream.js:294`).
- **Groq failure**: caught in `mediaStream.js:333-339` — re-asks `flow.STEP_QUESTIONS[step]` rather than a generic apology, preserving the current step.
- **Sarvam STT failure**: persisted `sttFailCount`; after 3 consecutive failures, says a goodbye message via Polly and sets `status:'failed'` (`mediaStream.js:271-289`).
- **Sarvam TTS failure**: `_sayWithSarvam()` retries once on `ECONNRESET`/`ECONNREFUSED` after a 600ms backoff (`mediaStream.js:448-453`); otherwise logs and falls through to `state='listening'` without speaking (silent turn).
- **Polly failure → `pollyFailCount`**: `_say()` (`mediaStream.js:389-409`) tries Polly via `calls.update()` for `en-IN`/`hi-IN` if `pollyFailCount < 2`; on failure increments the persisted counter and falls back to Sarvam TTS for that turn. After 2 consecutive failures, Polly is **disabled for the rest of the call** to avoid repeated ~5s TCP timeouts.

---

## 6. GAPS AND RISKS

### TODO/FIXME/XXX comments
None found in project source (`backend/**/*.js` excluding `node_modules`) — only matches were inside third-party `node_modules` packages, which are irrelevant.

### Error handling completeness
- `mediaStream.js`: well-covered — `_pipeline()` wraps `_runPipeline()` in try/catch with a hard `T_PIPELINE` timeout fallback (`mediaStream.js:223-241`); each external call (STT/translate/Groq/TTS) has its own try/catch + timeout via the `race()` helper.
- `groqService.js`: the Groq call itself (`groqService.js:87-92`) has **no try/catch** — errors propagate to the caller (`mediaStream.js`'s `race(...)` wrapper), which is the actual error-handling point. This is fine for the live path but means `groqService.callPriyaAPI` is not safe to call without a wrapping try/catch (the legacy `priyaWebhook.js:247-265` path does wrap it correctly).
- `priyaWebhook.js`: `call-respond` has a top-level try/catch (`priyaWebhook.js:180-291`) plus per-stage try/catches; `call-start` and `call-status` have try/catch around session updates. Generally solid.

### In-memory session store — restart = total data loss
- `backend/services/sessionStore.js:9-10` — `sessions` and `callSidMap` are plain JS objects with **no persistence**. A server restart mid-call:
  - Drops all active session state (the WS connection also drops, so the call effectively dies).
  - Drops `callSidMap`, so any pending Twilio webhook (`call-status`, or a Polly reconnect's `start` event) for an in-flight call will find `getByCallSid()` returning `null` and the WS handler will `ws.close()` (`mediaStream.js:533-537`).
  - Only `backend/db/priya-calls.json` (call history *summaries*, written via `saveToHistory()`) and `backend/db/vectors.json` (RAG cache) survive restarts. **Full transcripts and `collected` data for in-progress calls are lost** — there is no recovery path.

### Webhook signature validation — MISSING (security gap)
- `backend/routes/priyaWebhook.js` does **not** validate Twilio's `X-Twilio-Signature` header (no `twilio.webhook()` middleware or `validateRequest` call found anywhere in `routes/` or `server.js`). Any party who knows (or guesses) a `session_id` and the webhook URLs can POST forged `call-start`/`call-respond`/`call-status` requests, manipulate session state, or trigger TTS generation (cost) via `/webhook/call-respond`. **This should be added** via Twilio's `express` middleware (`twilio.webhook({validate: true})`) on all `/webhook/*` routes.

### Latency
- Per-turn budget documented in `mediaStream.js:153-158`: `T_STT=7s`, `T_TRANSLATE=4s`, `T_GROQ=5s`, `T_TTS=8s`, hard ceiling `T_PIPELINE=15s`. Actual logged timings (`[WS] 1.STT`, `2.Translate-in`, `3.Groq`, `4.TTS`) typically show STT ~1-2s, Groq sub-second (8b-instant), TTS ~0.5-1.5s for Sarvam or near-instant dispatch for Polly — but **Polly turns incur a full WebSocket teardown/reconnect** (`calls.update()` → Twilio drops and re-opens the media stream), plus a **900ms cooldown** (`mediaStream.js:490`) before listening resumes, adding real wall-clock latency per Polly turn beyond the raw TTS time. Each `_sayPolly()` call also carries a 5s internal timeout risk (`mediaStream.js:426`) on `calls.update()`.

### Other risks
- **Secrets**: `backend/.env` exists (23 entries) alongside `backend/.env.example`. **No `.gitignore` exists in `backend/`** (only `frontend/.gitignore` was found) — if this repo is ever committed to version control as-is, `backend/.env` (containing `GROQ_API_KEY`, `SARVAM_API_KEY`, `TWILIO_AUTH_TOKEN`, `GEMINI_API_KEY`, Mongo URI, JWT secret, etc.) would be checked in. No hardcoded API keys were found directly in `.js` source files (all keys read via `process.env.*`), which is good — but the missing `.gitignore` is a real exposure risk.
- **No rate limiting**: no `express-rate-limit` or similar found in `server.js` or routes — `/webhook/call-respond` (which triggers Sarvam/Groq calls) and `/api/priya/trigger-call` (which places real outbound Twilio calls, billable) are both unprotected against abuse/flooding.
- **No automated tests for the live call flow**: `backend/tests/` covers `analytics`, `auth`, `call-orchestrator`, `gemini`, `telephony`, `webhook` — but none exercise `mediaStream.js` (WS/VAD/μ-law), `groqService.js`, or `flowController.js` directly. The core voice pipeline is essentially untested.
- **Regex extraction fragility**: `flowController.js:98-101` explicitly documents a recently-fixed bug where the case-insensitive course regex matched "IT" inside "It's"/"It is" — now handled by a separate case-sensitive `\bIT\b` match. This class of bug (regex false positives on common English words/contractions colliding with course/exam abbreviations like "IT", "ME", "CS") remains a structural fragility — any future course code that's also a common word (e.g., a hypothetical "AS" or "OR" program) could reintroduce similar bugs. Similarly, `extractDataFromText()`'s name regex (`flowController.js:69`) could misfire on phrases like "I am sure" → captures "Sure" as a name if capitalized by STT.
- **CORS**: `server.js:28-36` has a comment "open for now — tighten in production" — `cb(null, true)` is called unconditionally regardless of origin, effectively disabling CORS restriction.
- **Mongoose version**: `package.json:26` lists `"mongoose": "^9.6.1"` — this is unusually high (current stable Mongoose is v8.x as of mid-2025); worth verifying this isn't a typo/non-existent version that could break `npm install` in a clean environment.

### Top 5 improvements (priority order)

1. **Add Twilio webhook signature validation** (`twilio.webhook({validate:true})` on `/webhook/*` in `priyaWebhook.js`/`server.js`). Highest priority because it's a direct, low-effort security gap that allows session/state manipulation and billable-API abuse via forged requests.
2. **Persist live session state** (e.g., periodic snapshot of `sessions`/`callSidMap` to disk/Redis, or write-through on each `sessionStore.update()`), so a server restart or crash mid-call doesn't silently lose the transcript and collected data, and so in-flight Twilio webhooks can still resolve a session after a restart.
3. **Add rate limiting** on `/api/priya/trigger-call` (prevents abuse of billable outbound Twilio calls) and `/webhook/call-respond`/the WS pipeline (prevents Sarvam/Groq cost abuse from forged or replayed webhook traffic) — pairs naturally with item 1.
4. **Add automated tests for the live call pipeline** — at minimum, unit tests for `flowController.extractDataFromText`/`smartAdvance`/`buildSystemPrompt` (pure functions, easy to test, and exactly where regressions like the "IT"/"It's" bug occur) and integration tests for `groqService.callPriyaAPI` with a mocked Groq client.
5. **Tighten CORS in production** and add a `.gitignore` to `backend/` covering `.env`, `db/*.json`, and `audio/*` — low-effort hygiene fixes that close an accidental-secret-leak and stale-data-leak vector before any deployment/version-control step.
