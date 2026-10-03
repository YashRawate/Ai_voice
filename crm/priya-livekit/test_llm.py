import asyncio
import time
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 on Windows stdout for clean output
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from llm_failover import build_langchain_llm

async def main():
    print("Initializing LLM chain...")
    llm = build_langchain_llm()
    t0 = time.monotonic()
    try:
        r = await asyncio.wait_for(llm.ainvoke("Say hello in one short sentence."), 10)
        elapsed = round(time.monotonic() - t0, 2)
        print(f"LLM OK in {elapsed}s: {r.content}")
    except Exception as e:
        print(f"LLM FAILED: {repr(e)}")

if __name__ == "__main__":
    asyncio.run(main())
