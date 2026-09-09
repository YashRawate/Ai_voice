import os
import sys
import io
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-10-01-preview"
)

kb_path = Path(__file__).parent / "Aditya_University_Knowledge_Base.md"
kb_text = kb_path.read_text(encoding="utf-8") if kb_path.exists() else ""

from azure_realtime_agent import BASE_INSTRUCTIONS

print("=" * 60)
print("TESTING MULTILINGUAL CODE-MIXING (ODIA, HINDI, TELUGU)")
print("=" * 60)

test_cases = [
    ("Odia Test", "Namaskar agyan! Mo naa Karthik. Mora B.Tech CSE re interest achhi."),
    ("Hindi Test", "Namaste! Mera naam Rahul hai, mujhe B.Tech CSE ki fee janni hai."),
    ("Telugu Test", "Namaskaram andi! Naa peru Sai, naku B.Tech AIML gurinchi cheppandi."),
]

for lang_name, user_query in test_cases:
    messages = [
        {"role": "system", "content": BASE_INSTRUCTIONS},
        {"role": "user", "content": user_query}
    ]
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        max_tokens=45,
        temperature=0.6
    )
    latency_ms = (time.perf_counter() - t0) * 1000
    reply = resp.choices[0].message.content.strip()
    print(f"\n[{lang_name}]")
    print(f"  Caller:  {user_query}")
    print(f"  Priya:   {reply}")
    print(f"  Latency: {latency_ms:.1f} ms")

print("\n" + "=" * 60)
print("ALL MULTILINGUAL TESTS COMPLETED")
print("=" * 60)
