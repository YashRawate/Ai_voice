import time
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
)
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")

test_queries = [
    "Yes, my name is Aditya Kumar.",
    "What is the B.Tech CSE fee?",
    "What is the hostel fee for AC rooms?",
]

print(f"=== BENCHMARKING AZURE LATENCY ({deployment}) ===")
print(f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}\n")

for i, q in enumerate(test_queries, 1):
    t0 = time.time()
    res = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are Priya, an admissions counsellor for Aditya University. Keep replies under 20 words in spoken conversational voice."},
            {"role": "user", "content": q}
        ],
        stream=True,
        max_tokens=40
    )
    t_first = None
    parts = []
    for chunk in res:
        if chunk.choices and chunk.choices[0].delta.content:
            if t_first is None:
                t_first = time.time()
            parts.append(chunk.choices[0].delta.content)
    t_end = time.time()
    ttft = t_first - t0 if t_first else 0
    total = t_end - t0
    print(f"Turn {i}: '{q}'")
    print(f"   [TTFT - Time to First Token]: {ttft:.3f}s")
    print(f"   [Total Generation Time]:     {total:.3f}s")
    print(f"   [Priya Reply]:               '\"{''.join(parts).strip()}\"'\n")
