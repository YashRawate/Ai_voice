"""
Comprehensive test for Azure OpenAI Chat & Realtime models.
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini").strip()
REALTIME_DEPLOYMENT = os.getenv("AZURE_OPENAI_REALTIME_DEPLOYMENT", "gpt-realtime-mini").strip()
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21").strip()

print(f"=== TESTING AZURE ENDPOINT CONFIGURATION ===")
print(f"Endpoint: {ENDPOINT}")
print(f"Chat Deployment: {CHAT_DEPLOYMENT}")
print(f"Realtime Deployment: {REALTIME_DEPLOYMENT}")
print(f"API Version: {API_VERSION}")
print(f"API Key: {KEY[:8]}...{KEY[-6:]}\n")

# 1. Test Chat Completion (gpt-4.1-mini)
def test_chat():
    from openai import AzureOpenAI
    print("1. Testing Azure Chat Completion (gpt-4.1-mini)...")
    try:
        client = AzureOpenAI(
            azure_endpoint=ENDPOINT,
            api_key=KEY,
            api_version=API_VERSION,
        )
        response = client.chat.completions.create(
            model=CHAT_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are Priya from Aditya University."},
                {"role": "user", "content": "What is the fee for B.Tech in CSE?"}
            ],
            max_tokens=60,
        )
        reply = response.choices[0].message.content
        print(f"   [SUCCESS] Response from {CHAT_DEPLOYMENT}:")
        print(f"   \"{reply}\"\n")
        return True
    except Exception as e:
        print(f"   [FAILED] Chat completion error: {e}\n")
        return False

# 2. Test Realtime Model Initialization
def test_realtime():
    from livekit.plugins.openai.realtime import RealtimeModel
    print("2. Testing Azure Realtime Model Initialization (gpt-realtime-mini)...")
    try:
        model = RealtimeModel.with_azure(
            azure_endpoint=ENDPOINT,
            azure_deployment=REALTIME_DEPLOYMENT,
            api_key=KEY,
            api_version="2024-10-01-preview",
            voice="coral",
        )
        print(f"   [SUCCESS] RealtimeModel initialized: {model}\n")
        return True
    except Exception as e:
        print(f"   [FAILED] Realtime model error: {e}\n")
        return False

# 3. Test Agent.py LLM Builder
def test_agent_llm():
    print("3. Testing agent.py LLM builder...")
    try:
        from agent import build_llm
        llm = build_llm()
        print(f"   [SUCCESS] agent.py build_llm() instantiated successfully: {llm}\n")
        return True
    except Exception as e:
        print(f"   [FAILED] build_llm() error: {e}\n")
        return False

if __name__ == "__main__":
    t1 = test_chat()
    t2 = test_realtime()
    t3 = test_agent_llm()

    if t1 and t2 and t3:
        print("=== ALL TESTS PASSED! Everything is connected and working. ===")
    else:
        print("=== SOME TESTS FAILED. Check details above. ===")
