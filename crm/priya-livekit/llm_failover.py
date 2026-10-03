# crm/priya-livekit/llm_failover.py
"""
LangChain Multi-Provider Failover LLM Chain for AdmitAI Priya Voice Agent.
Supports Azure OpenAI -> Groq -> Gemini -> Ollama with standardized tool binding
and automatic fallback on rate limit (429), auth error (401), or outage.
"""

import os
import logging
from typing import Optional, List, Any
from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger("priya.llm_failover")


def build_langchain_llm(tools: Optional[List[Any]] = None) -> BaseChatModel:
    """
    Builds a primary LLM model with automatic fallback chains across providers.
    Uses .with_fallbacks() to provide resilient multi-provider failover.
    """
    models: List[BaseChatModel] = []

    # 1. Primary: Azure OpenAI
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    if azure_endpoint and azure_key:
        try:
            from langchain_openai import AzureChatOpenAI
            azure_llm = AzureChatOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=azure_key,
                azure_deployment=azure_deployment,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
                temperature=0.4,
                max_tokens=int(os.getenv("MAX_REPLY_TOKENS", "100")),
                request_timeout=3.5,
            )
            models.append(azure_llm)
            logger.info("Configured AzureChatOpenAI as primary LLM")
        except Exception as e:
            logger.warning(f"Could not initialize AzureChatOpenAI: {e}")

    # 2. Fallback 1: Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
            groq_llm = ChatGroq(
                api_key=groq_key,
                model_name=groq_model,
                temperature=0.4,
                max_tokens=int(os.getenv("MAX_REPLY_TOKENS", "100")),
                request_timeout=3.0,
            )
            models.append(groq_llm)
            logger.info(f"Configured ChatGroq as fallback LLM ({groq_model})")
        except Exception as e:
            logger.warning(f"Could not initialize ChatGroq: {e}")

    # 3. Fallback 2: Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            gemini_llm = ChatGoogleGenerativeAI(
                google_api_key=gemini_key,
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                temperature=0.4,
                max_output_tokens=int(os.getenv("MAX_REPLY_TOKENS", "100")),
            )
            models.append(gemini_llm)
            logger.info("Configured ChatGoogleGenerativeAI as fallback LLM")
        except Exception as e:
            logger.warning(f"Could not initialize ChatGoogleGenerativeAI: {e}")

    # 4. Fallback 3: Local Ollama / Mock fallback
    try:
        from langchain_community.chat_models import ChatOllama
        local_llm = ChatOllama(
            base_url=os.getenv("LOCAL_BASE_URL", "http://localhost:11434"),
            model=os.getenv("LOCAL_MODEL", "qwen2.5:3b"),
            temperature=0.4,
        )
        models.append(local_llm)
    except Exception:
        pass

    # 5. Zoho Catalyst QuickML
    if os.getenv("CATALYST_ENDPOINT_URL") and os.getenv("CATALYST_CLIENT_ID"):
        try:
            from catalyst_llm import ChatCatalyst
            cat_llm = ChatCatalyst(
                model_name="glm-4.7-flash",
                temperature=0.4,
                max_tokens=int(os.getenv("MAX_REPLY_TOKENS", "100")),
            )
            models.append(cat_llm)
            logger.info("Configured ChatCatalyst as LLM (glm-4.7-flash)")
        except Exception as e:
            logger.warning(f"Could not initialize ChatCatalyst: {e}")

    # Prioritize preferred provider
    preferred = os.getenv("LLM_PROVIDER", "").lower().strip()
    if preferred == "catalyst":
        cat_models = [m for m in models if "ChatCatalyst" in type(m).__name__]
        other_models = [m for m in models if "ChatCatalyst" not in type(m).__name__]
        if cat_models:
            # If user explicitly requested only catalyst, restrict to catalyst
            if os.getenv("LLM_FALLBACK", "").strip().lower() in ("", "none", "false"):
                models = cat_models
                logger.info("Operating in Catalyst-only LLM mode (no fallbacks)")
            else:
                models = cat_models + other_models
                logger.info("Configured ChatCatalyst as primary LLM")
    elif preferred == "groq":
        models.sort(key=lambda m: 0 if "ChatGroq" in type(m).__name__ else 1)

    if not models:
        # Minimal dummy model for testing/dry-run environments
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        logger.warning("No live LLM credentials found, falling back to FakeMessagesListChatModel")
        dummy = FakeMessagesListChatModel(responses=[])
        return dummy

    # Bind tools if provided
    if tools:
        bound_models = []
        for m in models:
            try:
                bound_models.append(m.bind_tools(tools))
            except Exception:
                bound_models.append(m)
        models = bound_models

    if len(models) == 1:
        return models[0]

    primary = models[0]
    fallbacks = models[1:]
    return primary.with_fallbacks(fallbacks, exceptions_to_handle=(Exception,))
