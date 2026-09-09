import asyncio
import time
import sys
import io

# Ensure UTF-8 stdout on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from latency_optimizer import LatencyOptimizer

async def test_fast_path_fees():
    t0 = time.time()
    resp = await LatencyOptimizer.try_fast_path("What are the fees for B.Tech?")
    elapsed_ms = (time.time() - t0) * 1000
    assert resp is not None
    assert "₹2,75,000" in resp or "tuition" in resp.lower()
    assert elapsed_ms < 50, f"Fast-path took {elapsed_ms:.2f}ms, expected <50ms"
    print(f"\n[Test 1] Fast-path Fees: {elapsed_ms:.3f}ms -> '{resp}'")

async def test_fast_path_scholarship():
    t0 = time.time()
    resp = await LatencyOptimizer.try_fast_path("Tell me about scholarships available")
    elapsed_ms = (time.time() - t0) * 1000
    assert resp is not None
    assert "scholarship" in resp.lower() or "waiver" in resp.lower()
    assert elapsed_ms < 50
    print(f"[Test 2] Fast-path Scholarship: {elapsed_ms:.3f}ms -> '{resp}'")

async def test_fast_path_hostel():
    resp = await LatencyOptimizer.try_fast_path("Is hostel available and what is the cost?")
    assert resp is not None
    assert "hostel" in resp.lower() or "30,000" in resp

async def test_fast_path_telugu():
    resp = await LatencyOptimizer.try_fast_path("హాస్టల్ వివరాలు ఏమిటి?", lang="te-IN")
    assert resp is not None
    assert "Hostel" in resp or "30 thousand" in resp
    print(f"[Test 3] Telugu (Teluglish) Fast-path: '{resp}'")

async def test_fast_path_hindi():
    resp = await LatencyOptimizer.try_fast_path("प्लेसमेंट कैसा है?", lang="hi-IN")
    assert resp is not None
    assert "placement" in resp.lower() or "27 lakh" in resp
    print(f"[Test 4] Hindi (Hinglish) Fast-path: '{resp}'")

async def test_response_chunking():
    long_response = (
        "Aditya University offers world class B.Tech programs in CSE, AIML, and Data Science. "
        "The annual tuition fee is 2 lakh 75 thousand rupees. "
        "We also provide merit scholarships up to 50 percent for deserving students."
    )
    chunks = LatencyOptimizer.chunk_response(long_response, chunk_size=10)
    assert len(chunks) >= 2
    for idx, c in enumerate(chunks):
        assert len(c.strip()) > 0
        print(f"  Chunk {idx+1}: '{c}'")
    print(f"[Test 5] Response Chunking: split into {len(chunks)} streaming chunks.")

async def test_process_optimized_pipeline():
    # Mock LLM and TTS functions
    async def mock_llm(query: str):
        await asyncio.sleep(0.05)
        return f"LLM generated response for: {query}"

    async def mock_tts(chunk: str):
        await asyncio.sleep(0.01)
        return f"audio_bytes({len(chunk)})"

    # 1. Fast-path hit
    t0 = time.time()
    audio_chunks_fast = await LatencyOptimizer.process_optimized(
        "What are the fees?",
        llm_func=mock_llm,
        tts_func=mock_tts
    )
    time_fast = (time.time() - t0) * 1000
    assert len(audio_chunks_fast) > 0
    print(f"[Test 6] Fast query total pipeline: {time_fast:.2f}ms (Hits Cache + Chunked TTS)")

    # 2. Complex fallback
    t0 = time.time()
    audio_chunks_complex = await LatencyOptimizer.process_optimized(
        "My cousin studied mechanical and wants advice on robotics research lab projects",
        llm_func=mock_llm,
        tts_func=mock_tts
    )
    time_complex = (time.time() - t0) * 1000
    assert len(audio_chunks_complex) > 0
    print(f"[Test 7] Complex fallback query total pipeline: {time_complex:.2f}ms")

if __name__ == "__main__":
    asyncio.run(test_fast_path_fees())
    asyncio.run(test_fast_path_scholarship())
    asyncio.run(test_fast_path_hostel())
    asyncio.run(test_fast_path_telugu())
    asyncio.run(test_fast_path_hindi())
    asyncio.run(test_response_chunking())
    asyncio.run(test_process_optimized_pipeline())
    print("\n✅ ALL LATENCY OPTIMIZER TESTS PASSED SUCCESSFULLY!")
