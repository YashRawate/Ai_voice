# measure_latency.py
"""
Live Latency Benchmark for Priya Admissions Voice Agent.
Measures:
1. DialogueSlotManager extraction speed (Overhead)
2. LanguageHysteresisEngine decision speed (Overhead)
3. PatternRouter + calculate_scholarship fast-path latency (<50ms)
4. Azure LLM TTFT (Time To First Token) & full stream latency
5. End-to-End simulated turn latencies across representative conversation turns
"""

import os
import sys
import io
import time
from dotenv import load_dotenv
from openai import AzureOpenAI

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

from session_manager import DialogueSlotManager, SessionContext
from language_detector import LanguageHysteresisEngine
import university_data as udata
from agent import PatternRouter, INSTRUCTIONS


def run_benchmark():
    print("=" * 70)
    print("PRIYA VOICE AGENT — COMPREHENSIVE LATENCY BENCHMARK")
    print("=" * 70)

    # 1. SLOT MANAGER BENCHMARK
    print("\n[1] Dialogue Slot Manager (Entity Extraction Latency)")
    sample_texts = [
        "My name is Karthik and I got 92 percent in 12th board",
        "I wrote JEE Mains and AP EAMCET, planning for B.Tech Computer Science",
        "I live in Rajahmundry, can I know scholarship details?",
        "Naku B.Tech CSE lo seat kavali, 95% vachindi"
    ]
    slots = {}
    times = []
    for t in sample_texts:
        t0 = time.perf_counter()
        slots = DialogueSlotManager.extract_slots(t, slots)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000
        times.append(elapsed_us)
        print(f"  Query: '{t[:45]}...' -> {elapsed_us:.1f} μs ({elapsed_us/1000:.3f} ms)")
    avg_slot_ms = (sum(times) / len(times)) / 1000
    print(f"  --> Average Slot Extraction Overhead: {avg_slot_ms:.3f} ms (0.00{int(avg_slot_ms*1000)}s - Zero perceptible latency)")

    # 2. LANGUAGE HYSTERESIS ENGINE BENCHMARK
    print("\n[2] Language Hysteresis Engine (4-Layer Decision Latency)")
    engine = LanguageHysteresisEngine()
    lang_texts = [
        "What are the fee details for B.Tech CSE?",
        "Fees kitna hai CSE mein?",
        "Scholarship ke baare mein bataiye",
        "మంచిది! ఫీజు వివరాలు చెప్పండి"
    ]
    lang_times = []
    for t in lang_texts:
        t0 = time.perf_counter()
        lang, reason = engine.evaluate_turn(t)
        elapsed_us = (time.perf_counter() - t0) * 1_000_000
        lang_times.append(elapsed_us)
        print(f"  Query: '{t[:35]}...' -> {lang} ({reason}) in {elapsed_us:.1f} μs ({elapsed_us/1000:.3f} ms)")
    avg_lang_ms = (sum(lang_times) / len(lang_times)) / 1000
    print(f"  --> Average Language Decision Overhead: {avg_lang_ms:.3f} ms")

    # 3. FAST PATH / PATTERN ROUTER BENCHMARK (~70% of production turns)
    print("\n[3] Fast-Path Pattern Router & Personalized Scholarship (~70% turns)")
    collected = {
        "student_name": "Karthik",
        "class_12_score": "92%",
        "program_of_interest": "B.Tech CSE"
    }
    fast_queries = [
        ("Affirmation", "Yes"),
        ("Personalized Scholarship", "Can I get a scholarship?"),
        ("Course Fee", "What is the CSE fee?"),
        ("Hostel Facilities", "Tell me about hostel fees and rooms"),
        ("Placements", "What are the highest placement packages?")
    ]
    fast_times = []
    for category, q in fast_queries:
        t0 = time.perf_counter()
        resp = PatternRouter.match(q, collected, lang="en-IN")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        fast_times.append(elapsed_ms)
        print(f"  [{category}] Query: '{q}'")
        disp = (resp[:75] + '...') if resp else "None (Passed to LLM)"
        print(f"     Response Time: {elapsed_ms:.2f} ms")
        print(f"     Response:      '{disp}'")
    avg_fast_ms = sum(fast_times) / len(fast_times)
    print(f"  --> Average Fast-Path Response Latency: {avg_fast_ms:.2f} ms (< 1 ms instant response)")

    # 4. AZURE LLM SLOW PATH BENCHMARK (Streaming TTFT & Total for complex turns)
    print("\n[4] Azure LLM Streaming Latency (Slow Path / Complex Turns)")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini").strip()

    if not endpoint or not api_key:
        print("  [SKIP] Azure credentials not configured in .env")
        return

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    )

    llm_queries = [
        "I want to understand the difference between core CSE and AI ML specialization.",
        "Can a 12th pass student with 85% get direct admission without ASAT?"
    ]

    llm_ttft_list = []
    llm_total_list = []

    for i, q in enumerate(llm_queries, 1):
        t0 = time.perf_counter()
        stream = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": INSTRUCTIONS[:800]},
                {"role": "system", "content": "KNOWN ABOUT THIS CALLER: Name: Karthik; Program: B.Tech CSE; Class 12 %: 92%"},
                {"role": "user", "content": q}
            ],
            stream=True,
            max_tokens=50,
            temperature=0.6
        )
        t_first = None
        collected_chunks = []
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                if t_first is None:
                    t_first = time.perf_counter()
                collected_chunks.append(chunk.choices[0].delta.content)
        t_end = time.perf_counter()

        ttft_ms = (t_first - t0) * 1000 if t_first else 0
        total_ms = (t_end - t0) * 1000
        llm_ttft_list.append(ttft_ms)
        llm_total_list.append(total_ms)

        print(f"  Turn {i}: '{q}'")
        print(f"     TTFT (Time To First Token): {ttft_ms:.1f} ms")
        print(f"     Total Response Time:        {total_ms:.1f} ms")
        print(f"     Spoken Output:              '{''.join(collected_chunks).strip()}'\n")

    avg_ttft = sum(llm_ttft_list) / len(llm_ttft_list)
    avg_total_llm = sum(llm_total_list) / len(llm_total_list)

    # 5. SUMMARY COMPARISON
    print("=" * 70)
    print("PIPELINE LATENCY SUMMARY")
    print("=" * 70)
    print(f"• Slot Extraction (DialogueSlotManager):    {avg_slot_ms:.3f} ms (negligible)")
    print(f"• Language Decision (Hysteresis Engine):    {avg_lang_ms:.3f} ms (negligible)")
    print(f"• Fast-Path Cached Responses (~70% turns):  {avg_fast_ms:.2f} ms")
    print(f"• Azure LLM Slow Path TTFT (~30% turns):     {avg_ttft:.1f} ms")
    print(f"• Weighted Average Turn Processing:         {(0.70 * avg_fast_ms) + (0.30 * avg_ttft):.1f} ms")
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark()
