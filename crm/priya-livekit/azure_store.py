"""
Azure Cloud Services Integration for Priya Voice Agent:
- Azure Cosmos DB: Managed Conversation History & Lead State with 30-day auto-TTL
- Azure App Configuration: Dynamic System Prompts & Parameter Management (Zero-restart prompt updates)
- Azure AI Search: Managed Semantic & Vector Knowledge Base

Designed with resilient fallbacks:
- If Azure services are configured, it seamlessly synchronizes conversation data to Azure Cloud.
- If offline or running locally without credentials, it gracefully uses local memory/cache without blocking voice turns.
"""

from __future__ import annotations

import os
import time
import logging
import asyncio
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("priya.azure")

# Mute verbose Azure SDK HTTP request/response header logs so console stays clean
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)

# ── 1. Azure Cosmos DB (Conversation History & State) ──────────────────────────
try:
    from azure.cosmos import CosmosClient, PartitionKey
    from azure.cosmos.exceptions import CosmosHttpResponseError
    COSMOS_AVAILABLE = True
except ImportError:
    COSMOS_AVAILABLE = False


class AzureCosmosStore:
    """Manages persistent conversation history and lead state in Azure Cosmos DB."""

    def __init__(self):
        self.enabled = False
        self.client = None
        self.database = None
        self.container = None
        
        conn_str = os.getenv("AZURE_COSMOS_CONNECTION_STRING", "").strip()
        db_name = os.getenv("AZURE_COSMOS_DATABASE", "priya_db").strip()
        container_name = os.getenv("AZURE_COSMOS_CONTAINER", "conversations").strip()

        if COSMOS_AVAILABLE and conn_str:
            try:
                self.client = CosmosClient.from_connection_string(conn_str)
                self.database = self.client.get_database_client(db_name)
                self.container = self.database.get_container_client(container_name)
                self.enabled = True
                logger.info(f"[AZURE COSMOS] Connected to database: '{db_name}', container: '{container_name}'")
            except Exception as e:
                logger.warning(f"[AZURE COSMOS] Initialization failed (running local fallback): {e}")
                self.enabled = False
        else:
            logger.info("[AZURE COSMOS] Not configured (using local in-memory session store)")

    def save_turn_async(self, session_id: str, turn_number: int, speaker: str, text: str,
                        language: str = "en-IN", confidence: float = 1.0):
        """Non-blocking background save of a single conversation turn."""
        if not self.enabled or not self.container:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._do_save_turn(session_id, turn_number, speaker, text, language, confidence))
        except RuntimeError:
            import threading
            threading.Thread(
                target=lambda: asyncio.run(self._do_save_turn(session_id, turn_number, speaker, text, language, confidence)),
                daemon=True
            ).start()

    async def _do_save_turn(self, session_id: str, turn_number: int, speaker: str, text: str,
                            language: str, confidence: float):
        try:
            doc = {
                "id": f"{session_id}_turn_{turn_number}_{speaker}",
                "session_id": session_id,
                "turn_number": turn_number,
                "speaker": speaker,
                "text": text,
                "timestamp": time.time(),
                "language": language,
                "confidence": confidence,
                "ttl": 2592000,  # 30 days auto-expiry
            }
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.container.upsert_item, doc)
        except Exception as e:
            logger.debug(f"[AZURE COSMOS] Failed to save turn: {e}")

    def save_session_complete_async(self, session_dict: Dict[str, Any]):
        """Non-blocking save of the full completed session summary."""
        if not self.enabled or not self.container:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._do_save_session(session_dict))
        except RuntimeError:
            import threading
            threading.Thread(
                target=lambda: asyncio.run(self._do_save_session(session_dict)),
                daemon=True
            ).start()

    async def _do_save_session(self, session_dict: Dict[str, Any]):
        try:
            doc = {
                "id": f"{session_dict.get('session_id')}_summary",
                "session_id": session_dict.get("session_id"),
                "type": "session_summary",
                "duration_sec": session_dict.get("duration_sec"),
                "total_turns": session_dict.get("total_turns"),
                "collected": session_dict.get("collected", {}),
                "topics_discussed": session_dict.get("topics_discussed", []),
                "active_language": session_dict.get("active_language", "en-IN"),
                "timestamp": time.time(),
                "ttl": 7776000,  # 90 days retention for completed leads
            }
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.container.upsert_item, doc)
            logger.info(f"[AZURE COSMOS] Session summary stored for: {session_dict.get('session_id')}")
        except Exception as e:
            logger.debug(f"[AZURE COSMOS] Failed to save session summary: {e}")


# ── 2. Azure App Configuration (Dynamic System Prompts) ────────────────────────
try:
    from azure.appconfiguration import AzureAppConfigurationClient
    APPCONFIG_AVAILABLE = True
except ImportError:
    APPCONFIG_AVAILABLE = False


class AzureAppConfigManager:
    """Fetches and caches dynamic prompts and configurations from Azure App Configuration."""

    def __init__(self):
        self.enabled = False
        self.client = None
        self._cache: Dict[str, Tuple[float, Any]] = {}  # key -> (timestamp, value)
        self._cache_ttl = 300  # cache configs locally for 5 minutes (zero latency during calls)

        conn_str = os.getenv("AZURE_APPCONFIG_CONNECTION_STRING", "").strip()
        if APPCONFIG_AVAILABLE and conn_str:
            try:
                self.client = AzureAppConfigurationClient.from_connection_string(conn_str)
                self.enabled = True
                logger.info("[AZURE APPCONFIG] Connected to Azure App Configuration")
            except Exception as e:
                logger.warning(f"[AZURE APPCONFIG] Initialization failed (using local defaults): {e}")
                self.enabled = False
        else:
            logger.info("[AZURE APPCONFIG] Not configured (using local environment and defaults)")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Fetch setting from Azure App Config with local in-memory caching."""
        if not self.enabled or not self.client:
            return default

        now = time.time()
        if key in self._cache:
            cache_time, val = self._cache[key]
            if now - cache_time < self._cache_ttl:
                return val

        try:
            setting = self.client.get_configuration_setting(key=key)
            val = setting.value
            self._cache[key] = (now, val)
            return val
        except Exception as e:
            logger.debug(f"[AZURE APPCONFIG] Setting '{key}' not found or error: {e}")
            return default


# ── 3. Azure AI Search (Managed Knowledge Base) ────────────────────────────────
try:
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False


class AzureAISearchKB:
    """Queries indexed university knowledge from Azure AI Search."""

    def __init__(self):
        self.enabled = False
        self.client = None
        
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
        key = os.getenv("AZURE_SEARCH_KEY", "").strip()
        index_name = os.getenv("AZURE_SEARCH_INDEX", "university-kb").strip()

        if SEARCH_AVAILABLE and endpoint and key:
            try:
                credential = AzureKeyCredential(key)
                self.client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
                self.enabled = True
                logger.info(f"[AZURE AI SEARCH] Connected to index: '{index_name}'")
            except Exception as e:
                logger.warning(f"[AZURE AI SEARCH] Initialization failed (using local udata): {e}")
                self.enabled = False
        else:
            logger.info("[AZURE AI SEARCH] Not configured (using local university_data knowledge base)")

    async def search(self, query: str, top: int = 3) -> List[Dict[str, Any]]:
        """Search knowledge base with semantic / keyword matching."""
        if not self.enabled or not self.client:
            return []
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: list(self.client.search(search_text=query, top=top))
            )
            return results
        except Exception as e:
            logger.debug(f"[AZURE AI SEARCH] Search query failed: {e}")
            return []


# Global instances
AZURE_COSMOS_STORE = AzureCosmosStore()
AZURE_APPCONFIG = AzureAppConfigManager()
AZURE_AI_SEARCH = AzureAISearchKB()
