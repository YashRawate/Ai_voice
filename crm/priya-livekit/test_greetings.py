"""
Test Priya's greeting in Indian English, Telugish, and Hinglish with Azure OpenAI.
"""
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini").strip()
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21").strip()

client = AzureOpenAI(
    azure_endpoint=ENDPOINT,
    api_key=KEY,
    api_version=API_VERSION,
)

SYSTEM_PROMPT = """You are Priya, a polite, warm Indian admissions counsellor for Aditya University in Andhra Pradesh.
You naturally converse in Indian English, Telugish (Telugu-English mix), and Hinglish (Hindi-English mix).
Keep your replies concise (1 to 2 spoken sentences). No bullet points."""

def test_greetings():
    scenarios = [
        ("Outbound / Default Opening Greeting", "Generate the opening greeting when the student picks up the call."),
        ("User speaks in Indian English", "Hello, I wanted to know about admissions for this year."),
        ("User speaks in Telugish", "Namaskaram andi, B.Tech CSE lo admission ela tesukovali?"),
        ("User speaks in Hinglish", "Hello ma'am, Aditya University me hostel facilities kaisa hai?"),
    ]

    print("=== PRIYA GREETING & MULTI-DIALECT TEST ===\n")
    for title, prompt in scenarios:
        print(f"--- Scenario: {title} ---")
        print(f"Caller: \"{prompt}\"")
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=80,
        )
        reply = response.choices[0].message.content.strip()
        print(f"Priya: \"{reply}\"\n")

if __name__ == "__main__":
    test_greetings()
