# crm/priya-livekit/checkpointer.py
"""
Checkpointing provider for AdmitAI Priya LangGraph StateGraph.
Provides in-memory checkpointer with Redis fallback support.
"""

import os
import logging
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("priya.checkpointer")


def get_checkpointer():
    """
    Get graph checkpointer.
    Uses MemorySaver by default, with optional Redis checkpointer if configured.
    """
    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        try:
            from langgraph.checkpoint.redis import RedisSaver
            checkpointer = RedisSaver.from_conn_string(redis_url)
            logger.info("Using RedisSaver checkpointer for LangGraph")
            return checkpointer
        except Exception as e:
            logger.warning(f"Could not initialize RedisSaver ({e}), falling back to MemorySaver")

    logger.info("Using MemorySaver checkpointer for LangGraph")
    return MemorySaver()
