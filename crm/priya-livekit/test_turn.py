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

from direct_server import DirectCallSession

class MockWebSocket:
    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def send_json(self, data):
        self.sent_messages.append(data)

    async def close(self):
        self.closed = True

async def main():
    print("Initializing test DirectCallSession...")
    mock_ws = MockWebSocket()
    session = DirectCallSession(ws=mock_ws, stream_sid="test_stream_123")
    
    # We do not call session.initialize() because we don't need real STT websocket or greeting playback here
    # Test run_turn directly
    print("\n--- Running standalone turn: 'My name is Karthik.' [en-IN] ---")
    t0 = time.monotonic()
    
    try:
        await session.run_turn("My name is Karthik.", "en-IN", turn_num=1)
        elapsed = round(time.monotonic() - t0, 2)
        print(f"\n[PASS] Turn completed in {elapsed}s")
        print(f"Total media frames dispatched: {len(mock_ws.sent_messages)}")
        print(f"Facts extracted: {dict(session.long_mgr.fact_memory.facts)}")
    except Exception as e:
        print(f"\n[FAIL] Turn raised exception: {repr(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await session.tts.close()

if __name__ == "__main__":
    asyncio.run(main())
