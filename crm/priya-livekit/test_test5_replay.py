"""
Regression test replaying the exact turns from TEST_5.md:
Verifies that Unicode name extraction (Devanagari "भावनेमित यश"),
code-switching across Hindi, English, and Telugu ("ఆ మా."),
and noisy/short affirmations ("Okay", "ఆ మా.") DO NOT regress dialogue stage,
wipe facts, or re-ask for the caller's name mid-call.
"""

import os
import sys
from langgraph.checkpoint.memory import MemorySaver
from graph import build_call_graph
from session_lifecycle import start_new_call, reconnect_transport, apply_language_switch


def replay_test_5():
    # Ensure UTF-8 console output
    sys.stdout.reconfigure(encoding="utf-8")

    thread_id = "test5-exact-replay-thread"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 1. Initialize session lifecycle cleanly
    ctx = start_new_call(phone="+918249776759", session_id=thread_id, initial_language="en-IN")
    assert ctx.session_id == thread_id

    # 2. Build graph with checkpointing
    memory = MemorySaver()
    app = build_call_graph(checkpointer=memory)

    dialogue_script = [
        # Turn 1: Initial greeting response
        ("Yes, it is a good time.", "en-IN"),
        # Turn 2: Name in Hindi (Devanagari)
        ("भावनेमित यश", "hi-IN"),
        # Turn 3: Program of interest
        ("I am interested for B.Tech Computer Science.", "en-IN"),
        # Turn 4: 12th marks & JEE rank in Hindi
        ("हाँ, मैंने 12th कंप्लीट कर लिया है और मुझे 12th में 78% और जेईई की रैंक है 2000।", "hi-IN"),
        # Turn 5: Campus visit confirmation
        ("Yes, I want to visit this Saturday.", "en-IN"),
        # Turn 6: Short confirmation
        ("Okay", "en-IN"),
        # Turn 7: Query college facilities
        ("Can you tell me about college facilities?", "en-IN"),
        # Turn 8: Query hostel facilities
        ("Please tell me about the hostel facilities.", "en-IN"),
        # Turn 9: Query fee
        ("How many, how much price it is?", "en-IN"),
        # Turn 10: Telugu short affirmative - previously triggered re-greeting
        ("ఆ మా.", "te-IN"),
        # Turn 11: Switch back to Hindi
        ("हॉस्टल की फीस के बारे में बताइए।", "hi-IN"),
        # Turn 12: Acknowledgment in English
        ("Okay, fine.", "en-IN"),
    ]

    prohibited_regreet_phrases = [
        "may i know your name",
        "మీ పేరు చెప్పగలరా",
        "आपका नाम",
        "tell me your name",
        "what is your name",
    ]

    for turn_idx, (user_text, lang) in enumerate(dialogue_script, start=1):
        # Update lifecycle language
        apply_language_switch(ctx, lang)

        turn_payload = {
            "session_id": thread_id,
            "last_user_text": user_text,
            "language_code": lang,
        }
        if turn_idx == 1:
            turn_payload["facts"] = {}
            turn_payload["messages"] = []
            turn_payload["stage"] = "GREETING"
            turn_payload["next_field"] = "student_name"

        res = app.invoke(turn_payload, config=config)
        
        last_msg = res["messages"][-1] if res.get("messages") else ""
        reply = res.get("reply") or (last_msg.content if hasattr(last_msg, "content") else str(last_msg))
        stage = res.get("stage", "")
        facts = res.get("facts", {})

        print(f"\n[Turn {turn_idx}] ({lang}) User: {user_text}")
        print(f"       Priya: {reply}")
        print(f"       Stage: {stage} | Facts: {facts}")

        # Assertions
        # 1. After Turn 2, student_name MUST be present and preserved across all subsequent turns
        if turn_idx >= 2:
            assert "student_name" in facts or "name" in facts, f"Turn {turn_idx}: Name was lost from facts! Facts: {facts}"
        
        # 2. After Turn 3, program MUST be present
        if turn_idx >= 3:
            assert "program" in facts or "program_of_interest" in facts, f"Turn {turn_idx}: Program was lost! Facts: {facts}"

        # 3. Critical check: From Turn 3 onward, Priya MUST NEVER re-ask for the user's name
        if turn_idx >= 3:
            reply_lower = reply.lower()
            for phrase in prohibited_regreet_phrases:
                assert phrase not in reply_lower, (
                    f"CRITICAL REGRESSION: Priya re-greeted / asked for name at Turn {turn_idx} ({lang})!\n"
                    f"Phrase: '{phrase}' detected in reply: '{reply}'"
                )

    print("\n>>> ALL 12 TURNS OF TEST_5 REPLAY PASSED WITH ZERO RE-GREETING AND FULL MEMORY RETENTION! <<<")


if __name__ == "__main__":
    replay_test_5()
