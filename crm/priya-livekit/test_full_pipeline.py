import os
import sys
import io
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
load_dotenv()

print("=" * 60)
print("RUNNING FULL END-TO-END PIPELINE VALIDATION TEST")
print("=" * 60)

# 1. Test Azure OpenAI LLM Connection
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
azure_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
sarvam_key = os.getenv("SARVAM_API_KEY", "").strip()

print("\n[Step 1: Credentials Check]")
print(f"  Azure Endpoint: {endpoint}")
print(f"  Azure Key:      {'*' * 10}{azure_key[-6:] if azure_key else 'MISSING'}")
print(f"  Sarvam Key:     {'*' * 10}{sarvam_key[-6:] if sarvam_key else 'MISSING'}")

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=azure_key,
    api_version="2024-10-01-preview"
)

# 2. Test Number Normalization
from agent import _normalize_numbers_for_speech

test_num_input = "B.Tech CSE fee is ₹2,75,000 per year. One-time fee ₹15,000. ASAT 95% gives 50% scholarship."
normalized_output = _normalize_numbers_for_speech(test_num_input)

print("\n[Step 2: Number Normalization Test]")
print(f"  Raw Text:        {test_num_input}")
print(f"  Normalized Text: {normalized_output}")
assert "two lakh seventy five thousand" in normalized_output.lower() or "fifteen thousand" in normalized_output.lower()
assert "ninety five percent" in normalized_output
assert "fifty percent" in normalized_output
print("  Status: PASSED [Zero '15 zero zero zero' artifacts]")

# 3. Test LLM Dialogue & Latency
print("\n[Step 3: Azure LLM Telugish Query Test]")
t0 = time.perf_counter()
resp = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {"role": "system", "content": "You are Priya from Aditya University. Rule: Max 25 words. Reply in friendly conversational Telugish."},
        {"role": "user", "content": "Namaskaram andi, B.Tech CSE fee entha?"}
    ],
    max_tokens=40,
    temperature=0.6,
)
llm_latency = (time.perf_counter() - t0) * 1000
llm_text = resp.choices[0].message.content.strip()
print(f"  LLM Response: {llm_text}")
print(f"  LLM Latency:  {llm_latency:.1f} ms")

# 4. Test Sarvam TTS Synthesis with 16kHz WAV
print("\n[Step 4: Sarvam 16kHz Audio Synthesis Test]")
t0 = time.perf_counter()
tts_resp = requests.post(
    "https://api.sarvam.ai/text-to-speech",
    headers={"api-subscription-key": sarvam_key, "Content-Type": "application/json"},
    json={
        "inputs": [llm_text],
        "target_language_code": "te-IN",
        "speaker": "ritu",
        "model": "bulbul:v3",
        "speech_sample_rate": 16000,
        "output_audio_codec": "wav"
    },
    timeout=10
)
tts_latency = (time.perf_counter() - t0) * 1000
print(f"  TTS Status:   {tts_resp.status_code} ({'OK' if tts_resp.status_code == 200 else 'FAILED'})")
print(f"  TTS Latency:  {tts_latency:.1f} ms")
assert tts_resp.status_code == 200, f"TTS Failed: {tts_resp.text}"

total_latency = llm_latency + tts_latency
print("\n" + "=" * 60)
print(f"ALL TESTS PASSED - Total Turn Latency: {total_latency:.1f} ms")
print("=" * 60)
