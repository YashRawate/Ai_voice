"""
Test Azure OpenAI / AI Foundry with the deployed model and streaming.
"""
import os
import sys
import io
from dotenv import load_dotenv
from openai import AzureOpenAI

# Fix Windows console UTF-8 printing for Indian currency symbol (₹)
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv()

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://aditya-foundry-hub.openai.azure.com/").strip()
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini").strip()

client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version="2024-05-01-preview"
)

SYSTEM_PROMPT = """You are Priya, an admissions counsellor for Aditya University.
Answer concisely in 1 to 2 spoken sentences.
B.Tech in CSE with SAP fee is ₹2.75 lakh + ₹0.60 lakh per year.
Hostel fee: Non-AC ₹1.15 lakh/yr, AC ₹1.30 lakh/yr.
Scholarships: ASAT >= 95% gives 50% scholarship on B.Tech Tier 1."""

def ask_azure(query: str):
    print(f"\nUser: {query}")
    print(f"Connecting to Azure Model ({AZURE_DEPLOYMENT})...")

    response = client.chat.completions.create(
        model=AZURE_DEPLOYMENT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ],
        temperature=0.4,
        max_tokens=150,
        stream=True
    )

    print("\nPriya: ", end="", flush=True)
    full_reply = []
    for chunk in response:
        if chunk.choices and len(chunk.choices) > 0:
            content = chunk.choices[0].delta.content or ""
            print(content, end="", flush=True)
            full_reply.append(content)
    print("\n")
    return "".join(full_reply)

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "What is the fee for B.Tech in CSE with SAP?"
    ask_azure(query)
