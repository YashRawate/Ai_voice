import asyncio
import time
import os
import wave
import sys
from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 on Windows stdout for clean output
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from direct_sarvam_tts import DirectSarvamTTS
from direct_audio_codec import mulaw_to_pcm16

async def main():
    tts = DirectSarvamTTS(
        api_key=os.getenv("SARVAM_API_KEY"),
        speaker="shreya",
        language_code="en-IN",
        pace=1.12,
        sample_rate=8000,
        output_audio_codec="mulaw",
    )
    
    text = "Hello! This is Priya from Aditya University Admissions Office. May I know your good name, please?"
    print(f"Synthesizing test phrase: '{text}'")
    
    t0 = time.monotonic()
    first_byte_time = None
    chunks = []
    
    try:
        async for chunk in tts.synthesize_stream(text, language="en-IN"):
            if first_byte_time is None:
                first_byte_time = time.monotonic()
                ttfb = round((first_byte_time - t0) * 1000, 1)
                print(f"TTFB (Time-To-First-Byte): {ttfb} ms")
            chunks.append(chunk)
    finally:
        await tts.close()
        
    total_time = round(time.monotonic() - t0, 2)
    raw_mulaw = b"".join(chunks)
    print(f"Total time: {total_time}s, received {len(chunks)} chunks ({len(raw_mulaw)} bytes mulaw)")
    
    if raw_mulaw:
        # Convert 8kHz mu-law to 16-bit linear PCM and save as test_output.wav
        pcm16_data = mulaw_to_pcm16(raw_mulaw)
        wav_path = "test_output.wav"
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(pcm16_data)
        duration_sec = len(pcm16_data) / (8000 * 2)
        print(f"Saved {wav_path} ({duration_sec:.2f}s of audio). TTS OK!")
    else:
        print("ERROR: No audio chunks received!")

if __name__ == "__main__":
    asyncio.run(main())
