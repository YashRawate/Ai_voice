"""
Place an OUTBOUND call — Priya dials a phone number through Twilio and talks.
(Like the old Node trigger-call, but via LiveKit SIP.)

Prereqs:
  1. Twilio Termination set up (Termination SIP URI + a Credential List). See TELEPHONY.md.
  2. A LiveKit OUTBOUND trunk created from that — its ID goes in .env as OUTBOUND_TRUNK_ID.
  3. The agent worker running:  python agent.py dev

Usage:
  python make_call.py +918249776759       # call this number
  python make_call.py                      # calls CALL_TO from .env
"""
import os
import sys
import time
import asyncio
from dotenv import load_dotenv
from livekit import api

load_dotenv()


async def dial_direct_twilio(number: str):
    """Dial caller directly via Twilio REST API with raw WebSocket stream (No LiveKit SFU)."""
    import aiohttp
    import urllib.parse
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number = os.getenv("TWILIO_PHONE_NUMBER", "")
    public_url = os.getenv("DIRECT_PUBLIC_URL", "")
    
    if not (account_sid and auth_token and from_number):
        sys.exit("Direct outbound dialing requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in .env")
    
    # If public URL is provided, stream to it; else construct default
    stream_url = public_url if public_url else "wss://your-domain.ngrok-free.app/media-stream"
    twiml = f'<Response><Connect><Stream url="{stream_url}"><Parameter name="agent" value="priya"/></Stream></Connect></Response>'
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
    auth = aiohttp.BasicAuth(account_sid, auth_token)
    data = {
        "To": number,
        "From": from_number,
        "Twiml": twiml,
    }
    
    print(f"📞 [DIRECT MODE] Dialing {number} via Twilio REST API -> {stream_url}...")
    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.post(url, data=data) as resp:
            if resp.status in (200, 201):
                res_data = await resp.json()
                call_sid = res_data.get("sid")
                print(f"✅ Call Initiated! Call SID: {call_sid} (Direct 1:1 Audio Active)")
            else:
                err = await resp.text()
                print(f"❌ Twilio dial error ({resp.status}): {err}")


async def dial_livekit_sip(number: str):
    """Dial caller via LiveKit SIP trunk (Multi-party SFU)."""
    trunk = os.getenv("OUTBOUND_TRUNK_ID")
    if not trunk:
        sys.exit(
            "OUTBOUND_TRUNK_ID is not set in .env yet.\n"
            "Outbound needs: (1) Twilio Termination (URI + Credential List), then\n"
            "(2) a LiveKit outbound trunk created from it."
        )
    room = f"call-{number.lstrip('+')}-{int(time.time())}"
    lk = api.LiveKitAPI()
    try:
        await lk.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(agent_name="priya", room=room)
        )
        await lk.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk,
                sip_call_to=number,
                room_name=room,
                participant_identity="phone_user",
                participant_name="Prospect",
                wait_until_answered=True,
            )
        )
        print(f"📞 [LIVEKIT MODE] Connected — calling {number}, Priya is in room {room}")
    finally:
        await lk.aclose()


async def main():
    number = sys.argv[1] if len(sys.argv) > 1 else os.getenv("CALL_TO", "")
    if not number:
        sys.exit("Give a number: python make_call.py +918249776759  (or set CALL_TO in .env)")

    audio_pipeline = os.getenv("AUDIO_PIPELINE", "livekit").lower().strip()
    use_livekit = os.getenv("USE_LIVEKIT", "true").lower().strip()

    if audio_pipeline == "direct" or use_livekit == "false":
        await dial_direct_twilio(number)
    else:
        await dial_livekit_sip(number)


if __name__ == "__main__":
    asyncio.run(main())

