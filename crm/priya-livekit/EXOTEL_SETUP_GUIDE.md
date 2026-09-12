# Exotel Direct Audio Streaming Setup Guide (Option 2 — Sub-500ms Latency)

This guide walks you through connecting **Exotel** to Priya via **Option 2 (Direct Raw Audio WebSocket)**.
This option achieves the lowest possible latency (**<500ms voice-to-voice**) by streaming raw 8kHz mu-law audio directly between Exotel and `direct_server.py`, completely bypassing third-party SFU servers.

---

## 1. Architecture Overview

```
+──────────────────────────+         +──────────────────────────+         +──────────────────────────────+
|       CALLER PHONE       |         |      EXOTEL TELEPHONY    |         |    PRIYA DIRECT AUDIO SERVER |
|  (Any Indian Mobile/SIM) | ──────► |  (Indian Virtual Number) | ──────► |       (direct_server.py)     |
+──────────────────────────+   PSTN  +──────────────────────────+ WebSocket+──────────────────────────────+
                                                                             │
                                                                             ├── 7-Step Acoustic Pipeline (AEC, 0.85 Barge-In)
                                                                             ├── 4-Tier Language Resolver (en-IN, hi-IN, te-IN)
                                                                             ├── Fast-Path Cache (<15ms instant answers)
                                                                             └── Streaming Neural STT/TTS (Sarvam / Azure)
```

---

## 2. Step 1 — Expose Your Local Server (`direct_server.py`)

Exotel requires a public HTTPS / WSS endpoint to deliver the audio stream.

1. In a terminal, run **Ngrok** (or Cloudflare Tunnel):
   ```bash
   ngrok http 8000
   ```
2. Copy the forwarding URL (e.g. `https://your-subdomain.ngrok-free.app`).
3. Your endpoints are now:
   - **ExoML Webhook**: `https://your-subdomain.ngrok-free.app/exoml`
   - **WebSocket Stream**: `wss://your-subdomain.ngrok-free.app/media-stream`

---

## 3. Step 2 — Configure Inbound Calls in Exotel Dashboard

### A. If using Exotel Call Flow (App Bazaar)
1. Log in to your **Exotel Dashboard** (`https://my.exotel.com/<your_subdomain>`).
2. Go to **App Bazaar** $\rightarrow$ **Create Flow**.
3. Add a **Voice Streaming / Audio Stream** applet (or a **Passthru Applet** pointing to your URL):
   - **Stream URL**: `wss://your-subdomain.ngrok-free.app/media-stream`
   - **Audio Format**: `audio/x-mulaw;rate=8000` (8kHz mu-law)
   - **Bidirectional**: `true`
4. Attach your **ExoPhone** (`08047XXXXXX`) to this flow.

### B. If using Passthru / ExoML Webhook
1. In your Exotel Applet, select **Passthru Applet**.
2. Set the HTTP URL to:
   ```
   https://your-subdomain.ngrok-free.app/exoml
   ```
   Method: `POST`
3. When someone dials your ExoPhone, Exotel queries `/exoml`, and Priya returns:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
       <Connect>
           <Stream url="wss://your-subdomain.ngrok-free.app/media-stream">
               <Parameter name="agent" value="priya" />
           </Stream>
       </Connect>
   </Response>
   ```
4. Exotel immediately connects the bidirectional audio WebSocket to Priya.

---

## 4. Step 3 — Configure Environment Variables (`.env`)

Add your Exotel credentials to `crm/priya-livekit/.env`:

```env
# Telephony Mode
TELEPHONY_CARRIER=exotel
AUDIO_PIPELINE=direct
USE_LIVEKIT=false

# Exotel Credentials (from Exotel Dashboard -> API Details)
EXOTEL_ACCOUNT_SID=your_exotel_subdomain
EXOTEL_API_KEY=your_exotel_api_key
EXOTEL_API_TOKEN=your_exotel_api_token
EXOTEL_CALLER_ID=08047XXXXXX
DIRECT_PUBLIC_URL=https://your-subdomain.ngrok-free.app

# Audio Server Port
DIRECT_SERVER_PORT=8000
```

---

## 5. Step 4 — Run the Direct Audio Server

Start the direct audio server:
```bash
cd crm/priya-livekit
py direct_server.py
```
You will see:
```
[INFO] priya.direct_server: LangGraph pipeline successfully initialized for direct audio server
[INFO] uvicorn.error: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 6. Step 5 — Testing Inbound and Outbound Calls

### Test Inbound Calling:
Dial your **ExoPhone** (`08047XXXXXX`) from your mobile phone.
- Exotel connects to `wss://.../media-stream`.
- Priya greets you immediately in English/Hindi/Telugu.
- Try asking: *"What is the fee for CSE?"* $\rightarrow$ Answered via Fast-Path in **<15ms**!
- Try switching language: *"हिंदी में बात करो"* $\rightarrow$ Priya seamlessly locks into Hindi with Devanagari responses.

### Test Outbound Calling:
To have Priya call a student's number using Exotel:
```bash
cd crm/priya-livekit
py make_call.py +91XXXXXXXXXX
```
Exotel will dial the student's phone, connect the call to Priya's WebSocket stream, and start the consultative admissions dialogue.
