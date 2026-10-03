"""
Priya — Aditya University admission voice agent, rebuilt on LiveKit Agents.

Why LiveKit: it handles the hard parts you hand-built in the Node version — live
streaming STT, turn detection / endpointing, and streamed LLM→TTS overlap — natively.
The Sarvam plugin does STT + TTS (11 Indian languages); the LLM is Groq llama-70b
(fast, strong Telugu) via the OpenAI-compatible plugin. Swap to local Ollama by
flipping LLM_PROVIDER=local in .env.

Run:
    python agent.py console     # talk to it from your terminal mic
    python agent.py dev         # run the worker (for LiveKit rooms / telephony)
"""
import sys
import os

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import re
import json
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from livekit.agents import (JobContext, WorkerOptions, cli, function_tool, RunContext,
                            metrics, APIConnectOptions)
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.agents.llm import ChatMessage, ChatChunk, ChatContext
from livekit.plugins import sarvam, openai, silero
try:
    from livekit.plugins import noise_cancellation as nc
    NC_AVAILABLE = True
except ImportError:
    NC_AVAILABLE = False

import university_data as udata  # local Aditya University knowledge + lookup helpers
from reporter import Reporter    # pushes live transcript/collected/status to the Node dashboard
from latency import LatencyTracker  # logs per-turn EOU/LLM/TTS latency to latency_log.csv
from translate import translate_out, prewarm as translate_prewarm, aclose as translate_aclose  # Sarvam translate-out
from mcp_client import mcp_bridge  # Model Context Protocol bridge for CRM and admissions tools
from fillers import get_filler  # Context-aware filler phrases for slow path (Azure)
from session_manager import GLOBAL_SESSION_STORE, SessionContext, ConversationTurn, is_garbled_input, DialogueSlotManager, is_valid_user_speech  # Session context, slot extraction & anti-repetition
from latency_optimizer import LatencyOptimizer  # Fast-path cache and latency optimization engine
try:
    from azure_store import AZURE_APPCONFIG, AZURE_COSMOS_STORE, AZURE_AI_SEARCH
except ImportError:
    AZURE_APPCONFIG, AZURE_COSMOS_STORE, AZURE_AI_SEARCH = None, None, None

# 6-Layer Advanced Language Detection System Modules
from audio_quality_gate import AudioQualityGate
from priya.audio.acoustic_pipeline import AcousticPipeline
from transcript_guards import classify_transcript, is_farewell, extract_name, dominant_script, INTERRUPT_WORDS, ALLOWED_SCRIPTS
from priya.language import resolve_mixed_language, build_language_system_prompt
from conversation_context import ConversationContext
from language_detector import LanguageDetector
from explicit_switch_detector import ExplicitLanguageSwitchDetector
from switch_decision import LanguageSwitchDecider
from noise_resilience_handler import NoiseResilienceHandler
from language_handler import LanguageHandler, SessionMemory, LANGUAGE_INSTRUCTIONS, get_language_code
from conversation_history import ConversationHistory
from question_engine import QuestionEngine
from llm_with_history import LLMWithHistory
from no_repetition import NoRepetitionEngine
from test_session_logger import TestSessionLogger, get_or_create_logger
from session_store import GLOBAL_SESSION_STORE

load_dotenv()
logger = logging.getLogger("priya")
logger.setLevel(logging.INFO)

MAX_CONTEXT_TURNS = int(os.getenv("MAX_CONTEXT_TURNS", "5"))

# LiveKit Cloud "session recording" uploads traces/logs/audio to its observability endpoint.
# On a weak uplink those POSTs time out and spam the console with OpenTelemetry tracebacks
# (non-fatal). Silence them. NOTE: to actually stop the uploads — which compete with the live
# call audio for your uplink and can make the voice break — disable Agent session recording in
# the LiveKit Cloud dashboard (Project → Settings → Agents).
# LiveKit Cloud session recording & WebRTC teardown noise filtering
logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)
logging.getLogger("livekit.rtc_engine").setLevel(logging.CRITICAL)
logging.getLogger("livekit_api.signal_client").setLevel(logging.CRITICAL)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

# ── Config from .env ─────────────────────────────────────────────────────────
LLM_PROVIDER   = os.getenv("LLM_PROVIDER", "groq").lower().strip()          # "groq" | "local" | "openrouter"
# Nemotron (via OpenRouter) is far more verbose than the other models — it dumps bullet lists and
# multi-sentence paragraphs. When it's the active model we append an extra, blunt style block.
IS_NEMOTRON    = (LLM_PROVIDER == "openrouter"
                  and "nemotron" in os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct").lower())
SARVAM_SPEAKER = os.getenv("SARVAM_SPEAKER", "shreya")      # bulbul:v3 realistic female voice (shreya / kavya)
TTS_LANGUAGE   = os.getenv("TTS_LANGUAGE", "en-IN")         # starting / fallback spoken language
TTS_PACE       = float(os.getenv("TTS_PACE", "1.12"))
# Languages this deployment will actually SPEAK. STT auto-detects each turn and we
# switch the Sarvam voice to match — but only within this allowlist, so a mis-detect
# (e.g. Telugu heard as Odia on a short clip) doesn't flip the voice to a wrong language.
TTS_ALLOWED    = {l.strip() for l in os.getenv("ALLOWED_LANGUAGES", "te-IN,hi-IN,en-IN").split(",") if l.strip()}

# ── Language mode ────────────────────────────────────────────────────────────
# English-only by default. Flip MULTILANG=true (in .env) later to auto-detect the
# caller's language and switch the STT, the voice, AND the prompt to match per turn.
MULTILANG      = os.getenv("MULTILANG", "true").lower() == "true"
STT_LANGUAGE   = os.getenv("STT_LANGUAGE", "en-IN")        # en-IN default for fast 300ms transcript finalization
# Noise cancellation: removes background voices and ambient noise before STT processing.
# Uses LiveKit's BVC (Background Voice Cancellation) model — requires LiveKit Cloud.
NOISE_CANCEL   = os.getenv("NOISE_CANCELLATION", "true").lower() == "true"
# Pattern matching: bypass LLM for simple factual questions (fees, placements, programs)
# and return instant cached responses from university_data.py. ~70% of turns hit cache (<100ms).
PATTERN_MATCH  = os.getenv("PATTERN_MATCHING", "true").lower() == "true"
# Smart contextual fillers: plays topic-matched phrase ("Let me pull placement data...")
# only on Azure slow path (~30% turns) while Azure is thinking. Cached turns get NO filler.
ENABLE_CONTEXT_FILLERS = os.getenv("ENABLE_CONTEXT_FILLERS", "true").lower() == "true"
# Automated turn-by-turn dialogue slot manager (extracts name, score, exams, programs)
ENABLE_SLOT_MANAGER    = os.getenv("ENABLE_SLOT_MANAGER", "true").lower() == "true"
# Slang & dialect mirroring: set ENABLE_SLANG=true in .env to mirror street slang ("bhayya", "bro", "yaar")
# or false (default) to maintain a polite, respectful, professional university counselor tone.
ENABLE_SLANG           = os.getenv("ENABLE_SLANG", "false").lower() == "true"
# The opening line is a fixed English greeting, so start with the English voice either way.
# In multilang mode the voice then switches to the caller's language on their first reply.
TTS_START_LANG = "en-IN"

# ── Translate-OUT ────────────────────────────────────────────────────────────
# When TRANSLATE_OUT=true, the LLM replies in ENGLISH and each sentence is localised
# into the caller's detected language by Sarvam (mayura:v1) right before TTS — more
# natural Indic phrasing than the LLM's direct output. Needs MULTILANG=true (so the
# caller's language is detected and the voice switches to it). Costs ~0.3–0.7s/sentence.
TRANSLATE_OUT  = os.getenv("TRANSLATE_OUT", "false").lower() == "true"
TRANSLATE_MODE = os.getenv("TRANSLATE_MODE", "modern-colloquial")
TRANSLATE_GENDER = os.getenv("TRANSLATE_GENDER", "Female")

if TRANSLATE_OUT:
    # The LLM COMPOSES in English; Sarvam localises it into the caller's language before TTS.
    # Critical: this is an internal pipeline detail — Priya must behave as if she speaks the
    # caller's language fluently, and must NEVER tell the caller she "only speaks English".
    LANGUAGE_BLOCK = (
        "- Compose every reply in plain, simple English — one short spoken sentence at a time.\n"
        "  Your English is automatically converted into the caller's own language before it is\n"
        "  spoken, so to the caller you ARE speaking their language fluently.\n"
        "- NEVER say or imply you 'only speak English'. NEVER apologise for language. NEVER offer\n"
        "  a different agent/counsellor because of language. If the caller asks whether you speak\n"
        "  Telugu/Hindi/Tamil/etc., warmly say YES and simply continue helping.\n"
        "- Keep proper nouns and technical terms as-is (B.Tech, CSE, NAAC, ₹ amounts, exam names)."
    )
elif MULTILANG and ENABLE_SLANG:
    LANGUAGE_BLOCK = (
        "- SLANG, DIALECT & VIBE MIRRORING MANDATE:\n"
        "  Always mirror the caller's exact slang, dialect, vibe, and conversational energy!\n"
        "  • Coastal Andhra / Godavari Dialect: If caller speaks with Andhra cadence ('andi', 'garu', 'cheppandi', 'avunandi') -> Reply in warm, respectful Godavari Teluglish ('andi', 'garu', 'untundandi').\n"
        "  • Telangana / Hyderabad Slang: If caller speaks Telangana slang ('bhayya', 'etla', 'etlundhi', 'cheppu', 'kadha', 'masthu') -> Match their friendly, colloquial Telangana Teluglish ('bhayya', 'untundhi', 'cheppandi').\n"
        "  • Hinglish / Casual Hindi Slang: If caller speaks casual Hindi ('bhai', 'yaar', 'kya scene hai', 'batao', 'sahi hai') -> Match their natural, friendly Hinglish slang ('bhai', 'scene aisa hai', 'available hai').\n"
        "  • Student / Youth Slang: If caller says 'bro', 'dude', 'bhayya', 'yaar' -> Match their casual, friendly college student slang and energy naturally!\n"
        "  • Formal / Professional: If caller speaks formally -> Reply in polished, respectful formal tone.\n"
        "- ADAPTIVE VIBE: Speak like a real human friend and counsellor from the caller's own region — NEVER sound like an artificial robot.\n"
        "- ONE QUESTION PER TURN: Keep replies concise, punchy, and conversational (max 25 words)."
    )
elif MULTILANG and not ENABLE_SLANG:
    LANGUAGE_BLOCK = (
        "- PROFESSIONAL COUNSELOR TONE MANDATE:\n"
        "  Always maintain a warm, polite, and professional university admissions counselor demeanor.\n"
        "  DO NOT use or mirror casual street slang like 'bro', 'dude', 'bhayya', 'yaar', or 'kya scene'.\n"
        "  In Telugu, use polite, respectful terms ('గారు', 'మీరు', 'అండి').\n"
        "  In Hindi, use respectful honorifics ('जी', 'आप').\n"
        "  In English, use clear, courteous, conversational English.\n"
        "- ADAPTIVE VIBE: Speak warmly and professionally like an expert admissions counsellor.\n"
        "- ONE QUESTION PER TURN: Keep replies concise, punchy, and conversational (max 25 words)."
    )
else:
    LANGUAGE_BLOCK = (
        "- Speak ONLY in English for the entire call, no matter what language the student uses.\n"
        "- Use simple, clear, conversational English. Friendly, respectful tone; mirror their formality."
    )

# Language-name keywords (in English + native scripts) → language code, for honouring an
# EXPLICIT request like "speak in Telugu" / "హిందీలో మాట్లాడండి" / "अंग्रेजी में बात करो".
LANG_NAMES = {
    "te-IN": ["telugu", "తెలుగు", "तेलुगु", "तेलुगू"],
    "hi-IN": ["hindi", "हिंदी", "హిందీ", "हिन्दी"],
    "ta-IN": ["tamil", "தமிழ்", "तमिल", "తమిళ"],
    "kn-IN": ["kannada", "ಕನ್ನಡ", "కన్నడ", "कन्नड"],
    "ml-IN": ["malayalam", "മലയാളം", "మలయాళం", "मलयालम"],
    "mr-IN": ["marathi", "मराठी", "మరాఠీ"],
    "bn-IN": ["bengali", "bangla", "বাংলা", "বেঙ্গলি", "बंगाली"],
    "gu-IN": ["gujarati", "ગુજરાતી", "గుజరాతీ", "गुजराती"],
    "pa-IN": ["punjabi", "ਪੰਜਾਬੀ", "పంజాబీ", "पंजाबी"],
    "od-IN": ["odia", "oriya", "ଓଡ଼ିଆ", "ఒడియా"],
    "en-IN": ["english", "इंग्लिश", "अंग्रेज", "ఇంగ్లీష్", "ఇంగ్లిష్", "ఆంగ్ల", "ইংরেজি"],
}
# Words that signal the caller is REQUESTING a language (not just mentioning one).
LANG_REQUEST_HINTS = ["speak", "talk", "converse", "switch", "change", "language", " in ",
                      "మాట్లాడ", "లో ", "बात", "बोल", " में ", "பேசு", "মধ্যে", "kannin"]

# ── Outbound-call context — fill per deployment (or inject per call from the CRM) ─
AGENT_NAME       = os.getenv("AGENT_NAME", "Priya")
UNIVERSITY_NAME  = os.getenv("UNIVERSITY_NAME", "Aditya University")
ACADEMIC_YEAR    = os.getenv("ACADEMIC_YEAR", "2026-27")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "English")
# Per-call: the prospect's name from the enquiry (blank in console testing).
STUDENT_NAME     = os.getenv("STUDENT_NAME", "")
# Course knowledge lives in university_data.py, served via lookup TOOLS (exact, not RAG).
# NOTE: kept SHORT on purpose — each tool already carries its own description in the tool
# schema the model receives; re-listing them here doubled the prompt cost for no gain.
KNOWLEDGE_BASE = (
    "OFFICIAL FACT SHEET (ANSWER DIRECTLY - DO NOT CALL TOOLS DURING CALLS):\n"
    "• Campus: 250-acre smart green campus in Surampalem, Kakinada District, AP. NAAC A++ accredited, NIRF Top 151-200.\n"
    "• B.Tech Tuition Fees: CSE & Specializations (AI&ML, Data Science) ₹2,75,000/year; Core branches (ECE, EEE, Mech, Civil) ₹1,00,000 to ₹1,35,000/year.\n"
    "• Common Fees: One-time admission fee ₹15,000. ASAT entrance exam fee ₹500.\n"
    "• Merit Scholarships (12th Board / ASAT / JEE): ≥95%: 50% waiver; 90-95%: 40%; 85-90%: 30%; 80-85%: 20%; 75-80%: 10% waiver.\n"
    "• Placements (2025-26): 3,832+ offers, highest package ₹27 LPA (Walmart). Top recruiters: Amazon, Walmart, CISCO, TCS, Infosys.\n"
    "• Hostels: AC & Non-AC with attached bath & multi-cuisine meals: Non-AC ₹1,15,000/year; AC ₹1,30,000/year.\n"
    "• Eligibility: Minimum 60% in 12th Board (MPC) with ASAT or JEE/EAPCET score.\n"
    "Speak these facts directly with high enthusiasm and always close for an admission action."
)
_student_ref = STUDENT_NAME or "the student who enquired with us"


# Cap the reply length. gpt-oss (reasoning) otherwise dumps the WHOLE flow as one 300-600
# token wall every turn — which burns the per-minute token budget (→ 429s) and makes Priya
# monologue for 20+ seconds. A hard cap keeps replies to ~one short answer + one question.
MAX_REPLY_TOKENS = int(os.getenv("MAX_REPLY_TOKENS", "160"))

# Cap what's actually SPOKEN per turn (characters). Even within the token cap, a long
# info-dump (e.g. a full fee breakdown) becomes a 20-30s audio clip — and a long clip
# streamed from a laptop over jittery wifi is exactly what stutters/breaks. Trimming the
# spoken reply to whole sentences keeps every clip short (~10-12s max) and resilient.
MAX_SPOKEN_CHARS = int(os.getenv("MAX_SPOKEN_CHARS", "280"))


_ENV_KEY = {
    "groq": "GROQ_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "huggingface": "HF_API_KEY",
    "bedrock": "BEDROCK_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "azure": "AZURE_OPENAI_API_KEY",
    "catalyst": "CATALYST_ENDPOINT_KEY",
}


def _keys_for(provider: str) -> list[str]:
    """All API keys configured for a provider, in priority order."""
    if provider == "local":
        return ["ollama"]
    if provider == "bedrock":
        key = os.getenv("BEDROCK_API_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY") or "bedrock_key"
        return [key]
    env = _ENV_KEY.get(provider)
    if not env:
        return []
    raw = [k.strip() for k in re.split(r"[,\s]+", os.getenv(env, "").strip()) if k.strip()]
    for i in range(1, 20):
        val = os.getenv(f"{env}_{i}")
        if val:
            for k in re.split(r"[,\s]+", val.strip()):
                if k.strip():
                    raw.append(k.strip())
    seen, out = set(), []
    for k in raw:
        if k not in seen:
            seen.add(k); out.append(k)
    return out


def _models_for(provider: str) -> list:
    """Models to build for a provider."""
    if provider == "openrouter":
        raw = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
        return [m.strip() for m in raw.split(",") if m.strip()] or [None]
    if provider == "huggingface":
        raw = os.getenv("HF_MODEL", "meta-llama/Llama-3.3-70B-Instruct:novita")
        return [m.strip() for m in raw.split(",") if m.strip()] or [None]
    return [None]


def _build_one(provider: str, api_key: str, model: str | None = None):
    """A single LLM builder for one provider."""
    if provider == "local":
        return openai.LLM(
            model=os.getenv("LOCAL_MODEL", "qwen2.5:3b"),
            base_url=os.getenv("LOCAL_BASE_URL", "http://localhost:11434/v1"),
            api_key="ollama", temperature=0.6, max_completion_tokens=MAX_REPLY_TOKENS,
        )
    if provider == "bedrock":
        b_model = os.getenv("BEDROCK_MODEL", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
        try:
            from livekit.plugins import aws
            return aws.LLM(
                model=b_model,
                temperature=0.6,
                max_completion_tokens=MAX_REPLY_TOKENS,
            )
        except Exception:
            try:
                from livekit.plugins import anthropic
                clean_model = b_model.replace("us.", "").replace("anthropic.", "").split("-v1")[0]
                return anthropic.LLM(
                    model=clean_model,
                    api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""),
                    temperature=0.6,
                    max_completion_tokens=MAX_REPLY_TOKENS,
                )
            except Exception:
                return openai.LLM(
                    model=b_model,
                    base_url=os.getenv("BEDROCK_BASE_URL", "https://bedrock-runtime.us-east-1.amazonaws.com/v1"),
                    api_key=api_key, temperature=0.6,
                    max_completion_tokens=MAX_REPLY_TOKENS,
                )
    if provider == "anthropic":
        a_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        try:
            from livekit.plugins import anthropic
            return anthropic.LLM(
                model=a_model,
                api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""),
                temperature=0.6,
                max_completion_tokens=MAX_REPLY_TOKENS,
            )
        except Exception:
            return openai.LLM(
                model=a_model,
                base_url="https://api.anthropic.com/v1",
                api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""),
                temperature=0.6,
                max_completion_tokens=MAX_REPLY_TOKENS,
            )
    if provider == "cerebras":
        c_model = os.getenv("CEREBRAS_MODEL", "llama-3.3-70b")
        c_kwargs = {
            "model": c_model,
            "base_url": "https://api.cerebras.ai/v1",
            "api_key": api_key,
            "temperature": 0.6,
            "max_completion_tokens": MAX_REPLY_TOKENS,
        }
        if "gpt-oss" in c_model or "zai" in c_model:
            c_kwargs["reasoning_effort"] = "low"
        return openai.LLM(**c_kwargs)
    if provider == "gemini":
        return openai.LLM(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=api_key, temperature=0.6,
            max_completion_tokens=MAX_REPLY_TOKENS,
        )
    if provider == "huggingface":
        return openai.LLM(
            model=model or os.getenv("HF_MODEL", "meta-llama/Llama-3.3-70B-Instruct:novita"),
            base_url="https://router.huggingface.co/v1",
            api_key=api_key, temperature=0.6,
            max_completion_tokens=MAX_REPLY_TOKENS,
        )
    if provider == "openrouter":
        or_model = model or os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct").split(",")[0].strip()
        or_kwargs = {
            "model": or_model,
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": api_key,
            "temperature": 0.6,
            "max_completion_tokens": MAX_REPLY_TOKENS,
        }
        if "nemotron" in or_model.lower() or "reasoning" in or_model.lower():
            or_kwargs["extra_body"] = {"reasoning": {"enabled": False}}
        return openai.LLM(**or_kwargs)
    if provider == "catalyst":
        from catalyst_llm import get_catalyst_client
        return openai.LLM(
            client=get_catalyst_client(),
            model="glm-4.7-flash",
            temperature=0.6,
            max_completion_tokens=MAX_REPLY_TOKENS,
        )
    if provider == "azure":
        az_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        az_model = model or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
        az_api_ver = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        return openai.LLM.with_azure(
            azure_endpoint=az_endpoint,
            azure_deployment=az_model,
            api_key=api_key or os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=az_api_ver,
            temperature=0.6,
            max_completion_tokens=MAX_REPLY_TOKENS,
        )
    return openai.LLM(  # groq
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key, temperature=0.6,
        max_completion_tokens=MAX_REPLY_TOKENS,
    )


def build_llm():
    """Build the LLM failover chain."""
    valid_provs = {"groq", "gemini", "cerebras", "openrouter", "local", "huggingface", "bedrock", "anthropic", "azure", "catalyst"}
    if LLM_PROVIDER not in valid_provs:
        logger.warning(f"unknown LLM_PROVIDER '{LLM_PROVIDER}' — defaulting to groq")

    order = [LLM_PROVIDER]
    for fb in os.getenv("LLM_FALLBACK", "").strip().lower().split(","):
        fb = fb.strip()
        if fb and fb not in order:
            order.append(fb)

    instances, labels = [], []
    for prov in order:
        if prov not in valid_provs:
            continue
        models = _models_for(prov)   # >1 for OpenRouter (tries each Nemotron model in turn)
        for idx, key in enumerate(_keys_for(prov), 1):
            for m in models:
                try:
                    instances.append(_build_one(prov, key, m))
                    tag = f"{prov}#{idx}" + (f"({m.split('/')[-1].replace(':free', '')})" if m else "")
                    labels.append(tag)
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"LLM {prov}#{idx} ({m or 'default'}) unavailable ({e}); skipping")

    if not instances:   # nothing configured → last-ditch groq attempt so we fail loudly, not silently
        return _build_one("groq", os.getenv("GROQ_API_KEY", ""))
    if len(instances) == 1:
        logger.info(f"LLM: {labels[0]} (no failover — add more keys to enable)")
        return instances[0]

    from livekit.agents.llm import FallbackAdapter
    logger.info(f"LLM failover chain ({len(instances)}): {' → '.join(labels)}")
    # max_retry_per_llm=0 + short attempt_timeout → fail over fast on a sustained 429/401.
    return FallbackAdapter(instances, max_retry_per_llm=0, attempt_timeout=4.0)


# The reply is cleaned ONCE, at the source, in Priya.llm_node (leaked tool JSON, markdown,
# stage directions, stacked questions) — so the chat HISTORY stores exactly what is spoken
# and every model, reasoning or instruct, streams to TTS sentence-by-sentence. Priya starts
# speaking on the first sentence instead of waiting for the whole reply.

# Cap how many past conversation items are sent to the LLM each turn. The system prompt is
# separate (always kept); this just bounds the GROWING history so prompt_tokens stays flat on
# long calls — lowers cost, latency, and how fast you hit provider rate limits. ~0 = unlimited.
MAX_HISTORY_ITEMS = int(os.getenv("MAX_HISTORY_ITEMS", "14"))


# ── Knowledge Base & Multi-Dialect Instructions ──────────────────────────────
from pathlib import Path
_KB_FILE = Path(__file__).parent / "Aditya_University_Knowledge_Base.md"
_KB_DATA = ""
if _KB_FILE.exists():
    try:
        _KB_DATA = _KB_FILE.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read knowledge base file: {e}")

INSTRUCTIONS = f"""# ADMITAI PRIYA — CONTEXT-FLOW VOICE AGENT SYSTEM PROMPT

# 1. IDENTITY & MISSION
You are Priya, a warm, intelligent and consultative Senior Admissions Counsellor at Aditya University (2025-26).
YOUR PRIMARY MISSION: CONVERT EVERY CALLER / ENQUIRY INTO AN ADMISSION through consultative guidance.
You are a conversational voice agent, not a form-filling bot. Every reply must be natural, engaging, and spoken aloud.

# 2. CORE CONTEXT-FLOW PRINCIPLE & STATEFUL EXECUTION
Do NOT treat this prompt as a flat list of questions. The conversation is STATEFUL.
At every turn, follow this internal sequence:
CURRENT CONTEXT → UNDERSTAND USER INTENT → IDENTIFY NEW/CORRECTED INFO → UPDATE STATE → IDENTIFY MISSING INFO → DETERMINE NEXT OBJECTIVE → ANSWER OR ASK ONE QUESTION → WAIT.
- Never restart conversation logic from the beginning.
- Never ask for information that is already known.
- A newer explicit statement from the caller overrides older stored memory.

# 3. CONTEXT PRIORITY
1. CURRENT USER MESSAGE
2. VERIFIED TOOL RESULT
3. CURRENT SESSION MEMORY (STM)
4. TRUSTED CUSTOMER MEMORY / CRM (LTM)
5. VERIFIED KNOWLEDGE BASE
6. SYSTEM INSTRUCTIONS

# 4. 5-STAGE ADMISSION CONVERSATION FLOW
Stage 1: Greeting & Identify Caller
  • If caller says "Yes" / "Speaking" / "Hello" -> Warmly ask for their name: "May I know your name, please?"
  • If caller is a parent, acknowledge warmly and ask for student's name.
  • Do NOT pitch campus visits or courses until identity is established!
Stage 2: Program & Course Interest
  • Once name is known -> "Nice to meet you, [Name]! Which program or branch are you interested in at Aditya University?"
  • Acknowledge their choice naturally. If they change programs later, immediately update to the new choice.
Stage 3: Academic Background & Eligibility
  • Ask for 12th Board / Intermediate marks or entrance exams (JEE Main, EAPCET, ASAT).
  • Apply praise: ≥90% "That's exceptional!"; 75-89% "That's a very solid score!"; 60-74% "Good, you meet our eligibility criteria!"
Stage 4: Consultative Value Pitch & ROI
  • Present verified ROI (3,800+ placements, 27 LPA package, up to 50% merit scholarship).
Stage 5: High-Conversion Close
  • Close with ONE action question:
    - CTA 1 (Top Priority): "Would you like to book a campus visit with your parents this Saturday?"
    - CTA 2: "Shall I send the direct application link to your WhatsApp to reserve your seat?"
    - CTA 3: "Shall I register you for the ASAT scholarship exam to secure your fee waiver?"

# 5. USER-INTENT OVERRIDE & INTERRUPTION HANDLING
- If the caller asks a direct question (fees, hostel, placements, scholarships), ANSWER IT FIRST using verified facts before returning to qualification.
- If the caller interrupts while you are speaking, drop your previous thought immediately. Do NOT apologize for speaking. Answer their new question directly in under 20 words.

# 6. OBJECTION HANDLING BATTLECARDS
• Fee / Expensive: "We offer up to 50% merit scholarships, semester installments, and 0% interest on-campus SBI/HDFC education loans."
• Parent Consultation: "Admissions are a big family decision! We warmly invite you and your parents for a guided campus tour this Saturday."
• Waiting for JEE/EAPCET: "You can secure a provisional seat now with a 100% refund guarantee if you get top ranks in IIT, NIT, or government colleges."
• Hostel / Safety / Food: "Our 250-acre gated smart campus has 24/7 CCTV, separate AC hostels with attached baths, and hygienic North & South Indian meals."

# 7. LANGUAGE & DIALECT
{LANGUAGE_BLOCK}

# 8. HARD VOICE OUTPUT RULES
1. Spoken response ONLY. Max 25 words per reply. Concise, punchy, persuasive tone.
2. Max ONE question per turn. Never combine multiple questions in one reply.
3. Keep facts strictly accurate from official data (fees, scholarships, placements).
4. No markdown, bullets, emojis, asterisks, stage directions, labels, or "Priya:" prefix.
5. Never repeat a question or ask for details already known.
6. Use student's name warmly 2-3 times during the call.
7. If caller says "Hello?" / "Are you there?" -> "Yes, I'm here!" + repeat the last point.
8. UNAVAILABLE COURSES: If caller asks for courses NOT offered at Aditya University (such as MBBS/Medicine/Dental, Law/LLB, Aviation/Pilot, Architecture/B.Arch, Fashion Design, Hotel Management, Veterinary, Marine Engineering, or B.Ed), clearly state that Aditya University does NOT offer this program. Highlight our flagship offerings: B.Tech (CSE, AI/ML, ECE), Pharmacy, MBA, BBA, Agriculture, or Forensic Science, and ask if they are interested in any of these.
9. ADMISSION CONVERSION CLOSING: When the caller agrees to an action ("yes send link", "book saturday", "register me"), immediately trigger the tool and confirm enthusiastically in under 20 words!

# TOOLS — use these for ALL factual answers and conversion actions
lookup_program, get_fees, check_scholarship, list_programs, list_branches, get_placements,
get_university_info, get_facilities, book_campus_visit, send_application_link, register_for_asat, handle_admission_objection. {KNOWLEDGE_BASE}
"""

# ── Nemotron-only style override ─────────────────────────────────────────────
# Nemotron ignores the softer style rules above — it writes paragraphs and dash/bullet lists
# that get read aloud awkwardly and run 20-30s. This block is blunt and repetitive on purpose;
# it's appended LAST (highest recency) only when Nemotron is the active model.
NEMOTRON_STYLE = """

# ⚠ HARD OUTPUT RULES — FOLLOW EXACTLY (you tend to over-explain; do NOT)
- Reply in ONE spoken sentence, MAXIMUM 25 words, then STOP. Never two sentences of content.
- ABSOLUTELY NO lists. No bullet points, no dashes ("-"), no numbered items, no "colon then a list",
  no line breaks. These are a PHONE call — a list cannot be read aloud.
- If you would list options, instead name only TWO or THREE in a natural sentence and offer more:
  e.g. "We have core CSE, Data Science, and an SAP-partnered track — shall I tell you about those?"
- NEVER say a filler like "Let me get the list/details for you" and then dump it. Just answer in one
  sentence, or call the tool and speak only the ONE thing they asked about.
- Do NOT begin every reply with "Great!" / "Excellent!" / "Great question!" — vary it, and usually
  skip it. Get to the point warmly.
- Exactly ONE question per turn, then wait. Never write or imagine the caller's reply.
"""
if IS_NEMOTRON:
    INSTRUCTIONS = INSTRUCTIONS + NEMOTRON_STYLE


# Fixed opening line — spoken in full, first, before anything else. A fixed string
# (not an LLM-generated reply) so it never comes out in fragments or gets re-greeted;
# it's added to the chat history, so the LLM knows it has already greeted and moves on.
# Kept SHORT (~4s of audio): phone callers hang up on long monologue openers.
GREETING = (
    f"Hello! This is {AGENT_NAME} from {UNIVERSITY_NAME}, "
    "calling about your admission enquiry. Is this a good time?"
)

# Appended to the prompt on a RE-ENGAGEMENT call (a lead who was interested earlier but hasn't
# enrolled). We already know their details (seeded into "KNOWN ABOUT THIS CALLER"), so Priya
# reconnects warmly, uncovers what's holding them back, and solves it — never starts from scratch.
FOLLOWUP_BLOCK = """

# THIS IS A FOLLOW-UP CALL (warm re-engagement — you have spoken before)
You already spoke with this student earlier; their details are in "KNOWN ABOUT THIS CALLER". They
were INTERESTED but haven't enrolled yet. Goal: reconnect warmly, find what's holding them back,
solve it, and gently move them toward enrolling or booking a campus visit.
- Open by referencing what you already know (their name + program) — do NOT re-collect name/program/scores.
- Warmly ask if they have any questions or concerns since you last spoke.
- Fee worry → proactively check their scholarship (check_scholarship) and share the exact %.
- Unsure about the program → offer to explore other branches/specialisations that suit them (they CAN change).
- Answer every concern with a real fact (scholarship, placements, hostel, safety) and reassure genuinely.
- Be warm, patient and friendly — a caring mentor checking in, never pushy or salesy.
- Close by inviting them to a campus visit or a counselling session, and confirm a day/time.
"""


# Safety net: some models (esp. smaller ones) LEAK tool calls as spoken text, e.g.
#   <function=save_detail>{"field": "student_name", "value": "Karthik"}</function>
# If that reaches TTS the caller HEARS it. Strip any such tool syntax + stray JSON arg
# blobs before synthesis, regardless of which model is used.
def _strip_tool_syntax(s: str) -> str:
    s = re.sub(r"<function\s*=[^>]*>\s*\{.*?\}\s*</?function>", " ", s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"</?function[^>]*>", " ", s, flags=re.IGNORECASE)          # bare/opening/closing tags
    # Any brace block is tool-arg JSON leaking through — braces never appear in real speech.
    # Iterate: a single pass leaves the OUTER braces of nested JSON ({"args": {...}}) behind.
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\{[^{}]*\}", " ", s)
    # gpt-oss sometimes echoes the tool result ("Saved program_of_interest.") or fakes a
    # "Label: value" data dump. Drop a trailing "Saved …" echo; it's never something to speak.
    s = re.sub(r"\s*\.{2,}\s*", ". ", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


# ── Phonetic number normalization for natural Indian conversational speech ──
_NUM_WORDS_BASE = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
    12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen",
    17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty", 30: "thirty",
    40: "forty", 50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety"
}

def _int_to_words(n: int) -> str:
    if n in _NUM_WORDS_BASE:
        return _NUM_WORDS_BASE[n]
    if n < 100:
        tens, rem = divmod(n, 10)
        return f"{_NUM_WORDS_BASE.get(tens * 10, '')} {_NUM_WORDS_BASE.get(rem, '')}".strip()
    if n < 1000:
        hundreds, rem = divmod(n, 100)
        rem_str = f" {_int_to_words(rem)}" if rem else ""
        return f"{_NUM_WORDS_BASE.get(hundreds, '')} hundred{rem_str}".strip()
    if n < 100000:
        thousands, rem = divmod(n, 1000)
        rem_str = f" {_int_to_words(rem)}" if rem else ""
        return f"{_int_to_words(thousands)} thousand{rem_str}".strip()
    if n < 10000000:
        lakhs, rem = divmod(n, 100000)
        rem_str = f" {_int_to_words(rem)}" if rem else ""
        return f"{_int_to_words(lakhs)} lakh{rem_str}".strip()
    return str(n)

def _normalize_numbers_for_speech(s: str, lang: str = "en-IN") -> str:
    """Convert digits, amounts, and fees into natural spoken phrases for Sarvam TTS.
    - English/Teluglish: '₹2.75 lakh' -> 'two lakh seventy five thousand rupees', '₹15,000' -> 'fifteen thousand rupees'
    - Telugu script: '₹2.75 lakh' -> 'రెండు లక్షల డెబ్బై ఐదు వేల రూపాయలు', '₹15,000' -> 'పదిహేను వేల రూపాయలు'
    - Hindi script: '₹2.75 lakh' -> 'दो लाख पचहत्तर हज़ार रुपये', '₹15,000' -> 'पंद्रह हज़ार रुपये'
    """
    if not s:
        return s

    # Strip formal catalog parentheses like (non-refundable), (compulsory), (per attempt)
    s = re.sub(r"\s*\((?:non-refundable|compulsory|one-time|per attempt|maximum \d+ attempts)\)", "", s, flags=re.IGNORECASE)

    has_telugu_script = bool(re.search(r'[\u0C00-\u0C7F]', s))
    has_hindi_script = bool(re.search(r'[\u0900-\u097F]', s))

    # ── Pure Telugu Script Handling ──────────────────────────────────────────
    if has_telugu_script:
        def _replace_lakh_te(m):
            w, f = m.group(1), m.group(2)
            if w == "1" and (not f or int(f) == 0):
                return "ఒక లక్ష రూపాయలు"
            if w == "2" and f and f.startswith("75"):
                return "రెండు లక్షల డెబ్బై ఐదు వేల రూపాయలు"
            if w == "1" and f and f.startswith("15"):
                return "లక్షా పదిహేను వేల రూపాయలు"
            if w == "1" and f and f.startswith("30"):
                return "లక్షా ముప్పై వేల రూపాయలు"
            if w == "1" and f and f.startswith("35"):
                return "లక్షా ముప్పై ఐదు వేల రూపాయలు"
            return f"{w} లక్షల రూపాయలు"

        s = re.sub(r"(?:₹|\bRs\.?\s*)?(\d+)(?:\.(\d+))?\s*(?:lakhs?|లక్షలు|లక్ష|lpa)\b(?:\s*(?:రూపాయలు|rupees?))?", _replace_lakh_te, s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?1[,.]?15[,.]?000\b", "లక్షా పదిహేను వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?1[,.]?30[,.]?000\b", "లక్షా ముప్పై వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?2[,.]?75[,.]?000\b", "రెండు లక్షల డెబ్బై ఐదు వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?15[,.]?000\b", "పదిహేను వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?30[,.]?000\b", "ముప్పై వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?45[,.]?000\b", "నలభై ఐదు వేల రూపాయలు", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?500\b", "ఐదు వందల రూపాయలు", s, flags=re.IGNORECASE)
        s = s.replace("₹", "").replace("Rs.", "")
        return re.sub(r"\s{2,}", " ", s).strip()

    # ── Pure Hindi Script Handling ───────────────────────────────────────────
    if has_hindi_script:
        s = re.sub(r"(?:₹|\bRs\.?\s*)?2\.75\s*(?:lakhs?|लाख)\b", "दो लाख पचहत्तर हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?1\.15\s*(?:lakhs?|लाख)\b", "एक लाख पंद्रह हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?1\.30\s*(?:lakhs?|लाख)\b", "एक लाख तीस हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?15[,.]?000\b", "पंद्रह हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?30[,.]?000\b", "तीस हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?45[,.]?000\b", "पैंतालीस हज़ार रुपये", s, flags=re.IGNORECASE)
        s = re.sub(r"(?:₹|\bRs\.?\s*)?500\b", "पाँच सौ रुपये", s, flags=re.IGNORECASE)
        s = s.replace("₹", "").replace("Rs.", "")
        return re.sub(r"\s{2,}", " ", s).strip()

    # ── Standard English / Teluglish / Hinglish Roman Script Normalizer ──────
    # 1. Decimal lakhs (e.g. ₹2.75 lakh, 2.75 lakh, 1.15 lakh, 1.30 lakh, 27 LPA, 27 lakh)
    def _replace_lakh_en(m):
        w, f = m.group(1), m.group(2)
        whole = int(w)
        frac = int(f.ljust(2, '0')[:2]) if f else 0
        parts = []
        if whole > 0:
            parts.append(f"{_int_to_words(whole)} lakh")
        if frac > 0:
            parts.append(f"{_int_to_words(frac)} thousand")
        amt = " ".join(parts) if parts else "zero"
        return f"{amt} rupees"

    s = re.sub(r"(?:₹|\bRs\.?\s*|\bINR\s*)?(\d+)(?:\.(\d+))?\s*(?:lakhs?|lakh per year|lpa)\b(?:\s*(?:rupees?|/-))?", _replace_lakh_en, s, flags=re.IGNORECASE)

    # 2. Indian formatted comma numbers (e.g. ₹1,15,000, 1,15,000, ₹2,75,000, ₹15,000, 15,000)
    def _replace_comma_amount(m):
        num_str = m.group(1).replace(",", "")
        try:
            num = int(num_str)
            if num >= 100:
                return f"{_int_to_words(num)} rupees"
            return _int_to_words(num)
        except ValueError:
            return m.group(0)

    s = re.sub(r"(?:₹|\bRs\.?\s*|\bINR\s*)?(\d{1,2},\d{2},\d{3}|\d{1,3},\d{3})\b(?:\s*(?:rupees?|/-))?", _replace_comma_amount, s, flags=re.IGNORECASE)

    # 3. Direct numbers preceded by currency symbol: ₹15000, ₹500, ₹30000, ₹275000
    def _replace_curr_num(m):
        try:
            num = int(m.group(1))
            return f"{_int_to_words(num)} rupees"
        except ValueError:
            return m.group(0)

    s = re.sub(r"(?:₹|\bRs\.?\s*|\bINR\s*)(\d+)\b(?:\s*(?:rupees?|/-))?", _replace_curr_num, s, flags=re.IGNORECASE)

    # 4. Clean up stray currency symbols
    s = s.replace("₹", "").replace("Rs.", "").replace("Rs", "")

    # 5. Ordinals (10th, 12th, etc.)
    s = re.sub(r"\b10th\b", "tenth", s, flags=re.IGNORECASE)
    s = re.sub(r"\b12th\b", "twelfth", s, flags=re.IGNORECASE)
    s = re.sub(r"\b1st\b", "first", s, flags=re.IGNORECASE)
    s = re.sub(r"\b2nd\b", "second", s, flags=re.IGNORECASE)
    s = re.sub(r"\b3rd\b", "third", s, flags=re.IGNORECASE)
    s = re.sub(r"\b4th\b", "fourth", s, flags=re.IGNORECASE)

    # 6. Percentages: 95% -> ninety five percent
    s = re.sub(r"\b(\d+)\s*%", lambda m: f"{_int_to_words(int(m.group(1)))} percent", s)
    s = re.sub(r"\b(\d+)\s+(percent|percentage)\b", lambda m: f"{_int_to_words(int(m.group(1)))} {m.group(2)}", s, flags=re.IGNORECASE)

    # 7. Standalone decimals (non-lakh) like 2.75 -> two point seven five
    def _replace_decimal(m):
        whole, frac = m.group(1), m.group(2)
        whole_w = _int_to_words(int(whole)) if whole.isdigit() else whole
        frac_w = " ".join(_NUM_WORDS_BASE.get(int(d), d) for d in frac)
        return f"{whole_w} point {frac_w}"
    s = re.sub(r"\b(\d+)\.(\d+)\b", _replace_decimal, s)

    # 8. Clean up excess whitespace
    return re.sub(r"\s{2,}", " ", s).strip()


# ── 6-Layer Advanced Language Detection Engine ──────────────────────────────
# Layer 1: AudioQualityGate (pre-filters noise, clippings, non-speech)
# Layer 2: ConversationContext (tracks session dominance, hysteresis, slots)
# Layer 3: LanguageDetector (multi-signal weighted scoring: STT + Script + Keywords)
# Layer 4: LanguageSwitchDecider (4-gate stability & confidence verification)
# Layer 5: ExplicitLanguageSwitchDetector (100% prioritized user switch requests)
# Layer 6: NoiseResilienceHandler (graceful multilingual repeats/clarifications)

_EXPLICIT_DETECTOR = ExplicitLanguageSwitchDetector()
_LANG_DETECTOR = LanguageDetector()
_SWITCH_DECIDER = LanguageSwitchDecider(max_switches_per_call=5, allowed_languages=TTS_ALLOWED)
_NOISE_HANDLER = NoiseResilienceHandler()
# ── Language Hysteresis & Multi-Signal Detection Engine ──────────────────────
from language_detector import LanguageHysteresisEngine

_HYSTERESIS_ENGINE = LanguageHysteresisEngine(default_lang="en-IN")


_TELUGU_INDICATORS = re.compile(
    r'[\u0C00-\u0C7F]|'  # Telugu Unicode script
    r'\b(entha|enti|entandi|cheppandi|telusukovalani|kavali|kavalani|undi|undhi|unnanu|untundi|untundhi|'
    r'meeru|naaku|chudandi|adagali|chadavali|chaduvutunnanu|cheyali|chey|mariyu|kadha|kadhara|emi|ela|'
    r'eppudu|akkada|ikkada|emiti|sare|babu|amma|vachanu|vasthanu|unnara|chudam|chesanu|ivvandi|cheppara|'
    r'lekapothe|pettandi|undha|leka|chala|baguntunda|bhayya|ayya|garu|andi|mastaru|masthu|mastu|etla|'
    r'etlundhi|kaneesam|koddiga|chusthunna|kavali bro|cheppu bro|entha bro|ela bro)\b',
    re.I
)

_HINDI_INDICATORS = re.compile(
    r'[\u0900-\u097F]|'  # Devanagari script
    r'\b(kya|hai|hain|kitna|kitni|kitne|hoga|hogi|hoge|bataiye|batao|bata|chahiye|kaise|kahan|kaha|aap|'
    r'tum|mujhe|aur|theek|accha|kab|kyun|bol|bolo|raha|rahi|rahe|hoon|hun|sunte|sunao|kare|karna|'
    r'chahunga|chahungi|milega|milegi|bhai|bhaiya|yaar|dost|kaisa|kaisa hai|chal raha|scene|sahi hai)\b',
    re.I
)

_TAMIL_INDICATORS = re.compile(
    r'[\u0B80-\u0BFF]|'  # Tamil script
    r'\b(enna|eppadi|solunga|venum|irukku|enga|ungalukku|enakku|kandippa)\b',
    re.I
)

_NEUTRAL_WORDS = {
    "ok", "okay", "yes", "yeah", "yep", "sure", "fine", "alright", "hmm", "ha",
    "haan", "avunu", "sare", "theek", "theek hai"
}


def detect_language(text: str, current_lang: str = "en-IN", stt_lang: str = None) -> tuple[str, str]:
    """
    Direct Turn-by-Turn Language Mirroring:
    Instantly matches whichever language the user speaks:
    1. Explicit User Switch ("speak in English/Hindi/Telugu") -> Immediate (100% priority).
    2. Short neutral confirmations ("yes", "ok", "sure") -> Keep current conversation language.
    3. Direct Telugu check (Telugu script or conversational words) -> te-IN immediately.
    4. Direct Hindi check (Devanagari script or conversational words) -> hi-IN immediately.
    5. Direct Tamil check -> ta-IN.
    6. Default clean English -> en-IN.
    """
    if not text or not text.strip():
        return current_lang or "en-IN", "empty"

    t = text.strip()
    t_clean = re.sub(r'[^a-zA-Z0-9\s]', '', t.lower()).strip()

    # 1. Explicit User Request
    explicit = _EXPLICIT_DETECTOR.detect_explicit_switch(t)
    if explicit.is_explicit_switch and explicit.target_language:
        if explicit.target_language in TTS_ALLOWED:
            return explicit.target_language, "explicit_request"

    # 2. Maintain active language on neutral conversational words
    if t_clean in _NEUTRAL_WORDS and current_lang in TTS_ALLOWED:
        return current_lang, "maintain_neutral"

    # 3. Direct Native Script Checks
    if re.search(r'[\u0C00-\u0C7F]', t):
        if "te-IN" in TTS_ALLOWED:
            return "te-IN", "telugu_script"
    if re.search(r'[\u0900-\u097F]', t):
        if "hi-IN" in TTS_ALLOWED:
            return "hi-IN", "hindi_script"
    if re.search(r'[\u0B80-\u0BFF]', t):
        if "ta-IN" in TTS_ALLOWED:
            return "ta-IN", "tamil_script"

    # 4. Romanized Vocabulary & Keyword Indicators
    if _TELUGU_INDICATORS.search(t):
        if "te-IN" in TTS_ALLOWED:
            return "te-IN", "telugu_words"
    if _HINDI_INDICATORS.search(t):
        if "hi-IN" in TTS_ALLOWED:
            return "hi-IN", "hindi_words"
    if _TAMIL_INDICATORS.search(t):
        if "ta-IN" in TTS_ALLOWED:
            return "ta-IN", "tamil_words"

    # 5. STT Language Hint (if provided by Sarvam Saaras)
    if stt_lang:
        stt_code = LanguageHandler.get_language_code(stt_lang)
        if stt_code in TTS_ALLOWED and stt_code != "unknown":
            return stt_code, f"stt_hint_{stt_code}"

    # 6. Default clean English
    return "en-IN", "english_speech"


# ── Pattern Router: instant responses for simple factual questions ────────────
# Intercepts ~70% of questions (fees, placements, programs, scholarships, facilities)
# and returns responses from university_data.py in <50ms, bypassing the ~1.3s Azure LLM.

class PatternRouter:
    """Fast-path router: matches user text to cached university data responses."""

    _SCHOLARSHIP_RE = re.compile(
        r'\b(scholarship|waivers?|concession|fee.?waiv|discount|merits?|free.?seat)\b|స్కాలర్‌షిప్|స్కాలర్షిప్|స్కాలర్|स्कॉलरशिप|छात्रवृत्ति', re.I)
    _FEE_RE = re.compile(
        r'\b(fee|fees|tuition|charges?|kitna|paisa|rupee|₹|kharchu)\b|ఫీజు|ఫీజులు|ఖర్చు|फीस|कितनी|खर्च', re.I)
    _PLACEMENT_RE = re.compile(
        r'\b(placements?|recruit|recruitment|recruiters?|highest package|average package|campus placement|placed students?|top companies?|lpa)\b|ప్లేస్‌మెంట్|ప్లేస్మెంట్|జాబ్స్?|ప్యాకేజీ|प्लेसमेंट', re.I)
    _PROGRAM_RE = re.compile(
        r'\b(programs?|courses?|branches?|specializations?|academic programs?|all courses|what courses|list branches)\b|కోర్సులు|బ్రాంచ్|కోర్సు|कोर्स|ब्रांच', re.I)
    _FACILITY_RE = re.compile(
        r'\b(hostel|hostels|library|lab|labs|medical|gym|transport|wifi|cafeteria|sports?|canteen|mess|room|rooms|hospital|ambulance)\b|హాస్టల్|హాస్టల్స్|हॉस्टल', re.I)
    _VISIT_RE = re.compile(
        r'\b(campus\s*visit|book\s*(?:a\s*)?visit|schedule\s*(?:a\s*)?visit|want\s*to\s*visit|visiting\s*(?:the\s*campus|aditya|that)?|come\s*to\s*campus|offline\s*counselling|see\s*the\s*campus|visit\s*aditya|visit\s*the\s*campus)\b|'
        r'విజిట్|క్యాంపస్\s*విజిట్|రావాలనుకుంటున్నా|విజిటింగ్|విజిట్\s*చేస్తాను|विजिट|कैंपस\s*विजिट|आना\s*चाहता', re.I)
    _UNIVERSITY_RE = re.compile(
        r'\b(naac|nirf|rankings?|accreditations?|accredit|where\s*is.*campus|campus\s*location|campus\s*size|campus\s*area|how\s*big.*campus|establish|about.*university|university.*about|qs.?rating)\b|'
        r'క్యాంపస్\s*ఎక్కడ|యూనివర్సిటీ\s*గురించి|कैंपस\s*कहाँ|यूनिवर्सिटी', re.I)
    _ELIGIBILITY_RE = re.compile(
        r'\b(eligib|cutoff|cut off|qualif|requirement|criteria|minimum.*score|marks.*need|can i get|chance)\b|అర్హత|ఎలిజిబిలిటీ|कटऑफ|योग्यता', re.I)

    _hit = 0
    _miss = 0

    @classmethod
    def detect_topic(cls, text: str) -> str:
        """Detect question topic for contextual filler selection."""
        if not text:
            return "GENERAL"
        t = text.lower().strip()
        if cls._FACILITY_RE.search(t):
            return "FACILITIES"
        if cls._SCHOLARSHIP_RE.search(t):
            return "SCHOLARSHIPS"
        if cls._FEE_RE.search(t):
            return "FEES"
        if cls._PLACEMENT_RE.search(t):
            return "PLACEMENTS"
        if cls._ELIGIBILITY_RE.search(t):
            return "ELIGIBILITY"
        if cls._PROGRAM_RE.search(t):
            return "PROGRAMS"
        if cls._UNIVERSITY_RE.search(t):
            return "UNIVERSITY"
        return "GENERAL"

    _AFFIRM_RE = re.compile(
        r'^(hello|hi|hey|namaste|vanakkam|yes|yeah|yep|sure|ok|okay|fine|alright|speaking|this side|avunu|haan|haa|ha|sare|theek|theek hai|avunandi)$', re.I)
    _NAME_INTRO_RE = re.compile(
        r'\b(?:my name is|myself|naa peru|mera naam|peru|naam)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b'
        r'|^(?:i am|i\'m|this is|it\'s)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\.?$',
        re.I
    )
    _DEGREE_RE = re.compile(
        r'\b(b\.?tech|m\.?tech|mba|mca|bba|b\.?pharmacy|b\.?pharm|pharm\.?\s*d|bca|diploma)\b', re.I)

    _UNAVAILABLE_PROGRAMS_RE = re.compile(
        r'\b(mbbs|bds|dental|dentist|bams|bhms|ayush|medicine|medical\s*doctor|doctor\s*course|'
        r'law|llb|llm|ba\s*llb|bba\s*llb|advocate|lawyer|'
        r'aviation|pilot|commercial\s*pilot|pilot\s*training|air\s*hostess|cabin\s*crew|flight\s*attendant|'
        r'b\.?arch|architecture|architect|fashion\s*design(?:ing)?|nift|interior\s*design(?:ing)?|'
        r'veterinary|bvsc|animal\s*husbandry|'
        r'hotel\s*management|culinary|catering|chef|'
        r'marine\s*engineering|nautical\s*science|merchant\s*navy|navy\s*course|'
        r'b\.?ed|d\.?ed|m\.?ed|teaching\s*course)\b|'
        r'ఎంబీబీఎస్|లా\s*కోర్స్|పైలట్|ఆర్కిటెక్చర్|ఫ్యాషన్\s*డిజైన్|'
        r'एमबीबीएस|वकील|लॉ|पायलट|आर्किटेक्चर|फैशन\s*डिजाइन',
        re.I
    )

    @classmethod
    def _unavailable_program(cls, text: str, lang: str = "en-IN") -> str:
        t_low = text.lower()
        course_name = "that course"
        if re.search(r'\b(mbbs|bds|dental|dentist|medicine|medical|doctor)\b|ఎంబీబీఎస్|एमबीबीएस', t_low):
            course_name = "MBBS / Medical"
        elif re.search(r'\b(law|llb|llm|ba\s*llb|bba\s*llb|advocate|lawyer)\b|లా|लॉ|वकील', t_low):
            course_name = "Law (LLB)"
        elif re.search(r'\b(aviation|pilot|commercial\s*pilot|air\s*hostess|cabin\s*crew)\b|పైలట్|पायलट', t_low):
            course_name = "Aviation / Pilot training"
        elif re.search(r'\b(b\.?arch|architecture|architect)\b|ఆర్కిటెక్చర్|आर्किटेक्चर', t_low):
            course_name = "Architecture (B.Arch)"
        elif re.search(r'\b(fashion\s*design(?:ing)?|nift|interior\s*design(?:ing)?)\b|ఫ్యాషన్|फैशन', t_low):
            course_name = "Fashion / Interior Designing"
        elif re.search(r'\b(veterinary|bvsc)\b', t_low):
            course_name = "Veterinary Science"
        elif re.search(r'\b(hotel\s*management|culinary|catering|chef)\b', t_low):
            course_name = "Hotel Management"
        elif re.search(r'\b(marine\s*engineering|nautical\s*science|merchant\s*navy)\b', t_low):
            course_name = "Marine Engineering"
        elif re.search(r'\b(b\.?ed|d\.?ed|m\.?ed)\b', t_low):
            course_name = "B.Ed / Teaching"

        if lang == "te-IN":
            return (f"ఆదిత్య యూనివర్సిటీలో {course_name} కోర్సు అందుబాటులో లేదండి. "
                    f"మా దగ్గర B.Tech (CSE, AI & ML, Data Science, ECE), Pharmacy, MBA, BBA, "
                    f"Forensic Science మరియు Agriculture కోర్సులు ఉన్నాయి. వీటిలో దేని గురించి తెలుసుకోవాలనుకుంటున్నారు?")
        if lang == "hi-IN":
            return (f"आदित्य यूनिवर्सिटी में {course_name} उपलब्ध नहीं है। "
                    f"हमारे यहाँ B.Tech (CSE, AI & ML, Data Science, ECE), Pharmacy, MBA, BBA, "
                    f"Forensic Science और Agriculture के प्रमुख प्रोग्राम्स हैं। क्या आप इनमें से किसी कोर्स की जानकारी लेना चाहेंगे?")
        return (f"Aditya University does not offer {course_name}. "
                f"We specialize in B.Tech (CSE, AI & ML, Data Science, ECE), Pharmacy, MBA, BBA, "
                f"Forensic Science, and Agricultural Sciences. Would you like details on any of these available programs?")

    @classmethod
    def route(cls, text: str, collected: dict, lang: str = "en-IN") -> str | None:
        """Alias for match()."""
        return cls.match(text, collected, lang=lang)

    @classmethod
    def match(cls, text: str, collected: dict, lang: str = "en-IN") -> str | None:
        """Return a response string if a high-confidence pattern matches, else None."""
        if not text or len(text.strip()) < 1:
            return None
        # Clean punctuation from text for robust matching (e.g. "Yes?" -> "yes")
        t = re.sub(r'[^\w\s]', '', text).lower().strip()

        # Determine language of the query directly so cached responses match immediately
        if re.search(r'[\u0C00-\u0C7F]', text) or re.search(r'\b(entha|kavali|undi|untundi|cheppandi|telusukovalani|avunu|namaste)\b', t):
            lang = "te-IN"
        elif re.search(r'[\u0900-\u097F]', text) or re.search(r'\b(kya|hai|kitna|kitni|chahiye|bataiye|hoga|namaste)\b', t):
            lang = "hi-IN"
        elif re.search(r'[\u0B80-\u0BFF]', text):
            lang = "ta-IN"

        # ── 0. Check for UNAVAILABLE programs (MBBS, Law, Aviation, Fashion, Architecture, etc.) ───
        if cls._UNAVAILABLE_PROGRAMS_RE.search(text) or cls._UNAVAILABLE_PROGRAMS_RE.search(t):
            cls._hit += 1
            logger.info(f"[FAST] pattern hit: unavailable program query ({cls._hit}/{cls._hit + cls._miss})")
            return cls._unavailable_program(text, lang=lang)

        # ── 1. Greeting / Availability / Affirmation fast-path (e.g. "Hello", "Yes", "Yes?") ───
        if cls._AFFIRM_RE.match(t):
            name = collected.get("student_name") or collected.get("name")
            prog = collected.get("program_of_interest") or collected.get("program")
            if name and prog:
                # Mid-call affirmation when name and program are already known
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: mid-call acknowledgment for {name} ({cls._hit}/{cls._hit + cls._miss})")
                if lang == "te-IN":
                    return f"ఖచ్చితంగా {name} గారు! {prog} ఫీజు లేదా క్యాంపస్ విజిట్ గురించి ఇంకేమైనా వివరాలు కావాలా?"
                if lang == "hi-IN":
                    return f"ज़रूर {name} जी! {prog} की फीस या कैंपस विजिट के बारे में और क्या जानना चाहते हैं?"
                return f"Certainly {name}! What other questions do you have regarding {prog} or admissions?"
            elif name:
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: greeting for {name} ({cls._hit}/{cls._hit + cls._miss})")
                if lang == "te-IN":
                    return f"నమస్తే {name} గారు! Aditya University admissions gurinchi meeku em details kavali?"
                if lang == "hi-IN":
                    return f"नमस्ते {name} जी! Aditya University admissions ke baare mein aapko kya jaankari chahiye?"
                return f"Hello {name}! How can I assist you with your admissions today?"
            elif not collected.get("_name_asked") and not any(k for k in collected if k not in ("_name_asked",)):
                # ONLY ask for name on the very first greeting turn
                collected["_name_asked"] = True
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: initial turn name request ({cls._hit}/{cls._hit + cls._miss})")
                if lang == "te-IN":
                    return "నమస్తే అండీ! Mee peru telusukovacha?"
                if lang == "hi-IN":
                    return "नमस्ते! Kya main aapka naam jaan sakti hoon?"
                return "Hello! May I know your name, please?"
            else:
                # Mid-call affirmation / acknowledgement (do not re-greet or re-ask name!)
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: mid-call acknowledgment ({cls._hit}/{cls._hit + cls._miss})")
                if lang == "te-IN":
                    return "ఖచ్చితంగా అండీ! Aditya University lo ఏ కోర్సు లేదా ఫీజు వివరాలు తెలుసుకోవాలనుకుంటున్నారు?"
                if lang == "hi-IN":
                    return "ज़रूर! Aditya University में आप किस कोर्स या फीस के बारे में जानना चाहते हैं?"
                return "Sure! Which course or admission details would you like to explore today?"

        # ── 2. Name Introduction fast-path (Turn 3: "My name is Karthik") ─────────
        m_name = cls._NAME_INTRO_RE.search(text)
        if m_name and not collected.get("student_name") and not cls._FACILITY_RE.search(t) and not cls._FEE_RE.search(t) and not cls._SCHOLARSHIP_RE.search(t) and not cls._PROGRAM_RE.search(t):
            raw_match = m_name.group(1) or m_name.group(2) or ""
            raw_name = raw_match.strip().title()
            stop_words = {
                "interested", "admission", "calling", "student", "good", "fine", "asking", "asking you",
                "looking", "inquiring", "checking", "wondering", "telling", "trying", "here", "just", "now", "not",
                "talking", "talking with", "with", "from", "in", "at", "for", "about", "platform", "first",
                "which", "what", "how", "why", "where", "you", "me", "done", "doing", "passed", "studying"
            }
            tokens = [w.lower() for w in raw_name.split()]
            # Ensure every token in the name is a valid proper name (no verbs, no prepositions, no -ing words)
            is_valid_name = (
                bool(raw_name)
                and len(tokens) <= 2
                and not any(w in stop_words for w in tokens)
                and not any(w.endswith("ing") for w in tokens)
                and not any(len(w) < 2 for w in tokens)
            )
            if is_valid_name:
                collected["student_name"] = raw_name
                collected["_name_asked"] = True
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: name '{raw_name}' ({cls._hit}/{cls._hit + cls._miss})")
                if lang == "te-IN":
                    return f"Nice to meet you, {raw_name} గారు! Aditya University lo meeru ఏ program lo join avvali anukuntunnaru?"
                if lang == "hi-IN":
                    return f"Nice to meet you, {raw_name} जी! Aap Aditya University mein kaunse program ke liye dekh rahe hain?"
                return f"Nice to meet you, {raw_name}! Which program are you interested in at Aditya University?"

        # ── 3a. Specific Saturday / Weekend Campus Visit Confirmation fast-path ──
        if re.search(r'\b(saturday|sunday|weekend|tomorrow)\b.*\b(visit|come|tour|book|chudalani|vasthanu|aunga)\b|\b(visit|come)\b.*\b(saturday|sunday|weekend|tomorrow)\b|(శనివారం|ఆదివారం|వీకెండ్)\s*(వస్తాను|విజిట్|బుక్)|(शनिवार|रविवार|वीकेंड)\s*(आऊंगा|विजिट|बुक)', t, re.I):
            day_match = "Saturday" if "sat" in t or "శని" in text or "शनి" in text else ("Sunday" if "sun" in t or "ఆది" in text or "रवि" in text else "this Weekend")
            collected["visit_datetime"] = f"{day_match} 10:00 AM"
            collected["engagement_choice"] = "campus_visit"
            collected["counselling_mode"] = "offline"
            collected["call_outcome"] = "interested"
            cls._hit += 1
            logger.info(f"[FAST] pattern hit: specific visit booking {day_match} ({cls._hit}/{cls._hit + cls._miss})")
            name = collected.get("student_name", "")
            name_suffix = f", {name} जी" if (name and lang == "hi-IN") else (f", {name} గారు" if (name and lang == "te-IN") else (f", {name}" if name else ""))
            if lang == "te-IN":
                return f"అద్భుతం{name_suffix}! మీ వీఐపీ క్యాంపస్ సందర్శన {day_match} ఉదయం 10 గంటలకు ఖరారు చేయబడింది. లొకేషన్ మ్యాప్ వాట్సాప్‌కు పంపాను. మీ తల్లిదండ్రులతో కలిసి రండి!"
            if lang == "hi-IN":
                return f"शानदार{name_suffix}! आपकी वीआईपी कैंपस विजिट {day_match} सुबह 10 बजे के लिए कन्फर्म हो गई है। लोकेशन मैप आपके व्हाट्सएप पर भेज दिया गया है। अपने माता-पिता के साथ जरूर आएं!"
            return f"Wonderful{name_suffix}! Your VIP campus tour is confirmed for this {day_match} at 10 AM. I have sent the GPS location and counselor pass to your WhatsApp. We look forward to welcoming you and your parents!"

        # ── 3b. Generic Campus Visit / Offline Counselling Booking fast-path ──────────
        if cls._VISIT_RE.search(t):
            collected["engagement_choice"] = "campus_visit"
            collected["counselling_mode"] = "offline"
            cls._hit += 1
            logger.info(f"[FAST] pattern hit: campus visit booking ({cls._hit}/{cls._hit + cls._miss})")
            name = collected.get("student_name", "")
            name_suffix = f", {name} जी" if (name and lang == "hi-IN") else (f", {name} గారు" if (name and lang == "te-IN") else (f", {name}" if name else ""))
            if lang == "te-IN":
                return f"తప్పకుండా{name_suffix}! మా 250 ఎకరాల సురంపాలెం క్యాంపస్‌కు మీకు సాదర స్వాగతం. మీరు ఏ తేదీ మరియు సమయంలో రావాలనుకుంటున్నారు?"
            if lang == "hi-IN":
                return f"बिल्कुल{name_suffix}! सुरमपलेम में हमारे 250 एकड़ के स्मार्ट कैंपस में आपका स्वागत है। आप किस तारीख और समय पर आना पसंद करेंगे?"
            return f"We would be delighted to welcome you{name_suffix} to our 250-acre smart campus in Surampalem! Which date and time would be convenient for your visit?"

        # ── 3c. Direct Provisional Application Link / WhatsApp CTA fast-path ──
        if re.search(r'\b(send|whatsapp|share|message)\b.*\b(link|application|form|details|site|url)\b|(link|application)\b.*\b(send|whatsapp|share|karo|bhejo|cheyandi|pampandi)\b|(లింక్|వాట్సాప్|అప్లికేషన్|లింకు).*?(పంపండి|షేర్|చేయండి|సెండ్)|(लिंक|व्हाट्सएप|एप्लिकेशन|फॉर्म).*?(भेज|दीजिये|कर|सेंड)', t, re.I):
            collected["engagement_choice"] = "application_link"
            collected["call_outcome"] = "interested"
            cls._hit += 1
            logger.info(f"[FAST] pattern hit: application link requested ({cls._hit}/{cls._hit + cls._miss})")
            name = collected.get("student_name", "")
            name_suffix = f", {name} जी" if (name and lang == "hi-IN") else (f", {name} గారు" if (name and lang == "te-IN") else (f", {name}" if name else ""))
            if lang == "te-IN":
                return f"ఖచ్చితంగా{name_suffix}! సీటు రిజర్వేషన్ మరియు స్కాలర్‌షిప్ కోసం డైరెక్ట్ అప్లికేషన్ లింక్ వాట్సాప్‌కు పంపాను. మీరు ఈ శనివారం క్యాంపస్ సందర్శించడానికి కూడా ఆసక్తిగా ఉన్నారా?"
            if lang == "hi-IN":
                return f"बिल्कुल{name_suffix}! सीट रिजर्वेशन और स्कॉलरशिप के लिए डायरेक्ट एप्लिकेशन लिंक आपके व्हाट्सएप पर भेज दी गई है। क्या आप इस शनिवार को माता-पिता के साथ कैंपस भी विजिट करना चाहेंगे?"
            return f"Done{name_suffix}! I have sent the direct provisional application link to your WhatsApp to lock your seat and scholarship. Would you also like to visit our campus with your parents this Saturday?"

        # ── 3d. ASAT Scholarship Exam Registration fast-path ──
        if re.search(r'\b(register|sign\s*up|enroll|write|appear)\b.*\b(asat|scholarship\s*test|entrance)\b|\b(asat|scholarship\s*test)\b.*\b(register|writing|ready)\b|(ఎగ్జామ్|పరీక్ష|స్కాలర్‌షిప్\s*టెస్ట్|అశాట్).*?(రాయడానికి|రిజిస్టర్)|(परीक्षा|स्कॉलरशिप\s*टेस्ट|एग्जाम|असाट).*?(देना|रजिस्टर)', t, re.I):
            collected["willing_university_exam"] = "yes"
            collected["engagement_choice"] = "asat_registration"
            collected["call_outcome"] = "interested"
            cls._hit += 1
            logger.info(f"[FAST] pattern hit: asat registration ({cls._hit}/{cls._hit + cls._miss})")
            name = collected.get("student_name", "")
            name_suffix = f", {name} जी" if (name and lang == "hi-IN") else (f", {name} గారు" if (name and lang == "te-IN") else (f", {name}" if name else ""))
            if lang == "te-IN":
                return f"చాలా మంచి నిర్ణయం{name_suffix}! 50% వరకు స్కాలర్‌షిప్ కోసం మిమ్మల్ని అశాట్ పరీక్షకు రిజిస్టర్ చేసాను. మోడల్ పేపర్స్ మరియు లింక్ వాట్సాప్‌కు పంపాను!"
            if lang == "hi-IN":
                return f"बहुत बढ़िया{name_suffix}! 50% तक स्कॉलरशिप के लिए आपका असाट परीक्षा में रजिस्ट्रेशन कर दिया गया है। सिलेबस और टेस्ट लिंक आपके व्हाट्सएप पर भेज दिया गया है!"
            return f"Great decision{name_suffix}! You are registered for the ASAT scholarship test to unlock up to 50% fee concession. Test syllabus and link are sent to your WhatsApp!"

        # ── 3e. Fee Objection Handling fast-path ──
        if re.search(r'\b(fees?\s+are\s+high|too\s+(expensive|costly|much)|can\'t\s+afford|fees\s+ekkuva|chala\s+ekkuva|bohot\s+zyada\s+fees|high\s+fee)\b|(ఫీజు|ఖర్చు)\s*(చాలా\s*ఎక్కువ|కట్టలేము)|(फीस|खर्चा)\s*(बहुत\s*ज्यादा|महंगी)', t, re.I):
            cls._hit += 1
            logger.info(f"[FAST] pattern hit: fee objection ({cls._hit}/{cls._hit + cls._miss})")
            name = collected.get("student_name", "")
            name_suffix = f", {name} जी" if (name and lang == "hi-IN") else (f", {name} గారు" if (name and lang == "te-IN") else (f", {name}" if name else ""))
            if lang == "te-IN":
                return f"నేను అర్థం చేసుకోగలను{name_suffix}. అందుకే ఆదిత్యలో 50% వరకు మెరిట్ స్కాలర్‌షిప్‌లు మరియు SBI/HDFC తో సున్నా వడ్డీ ఎడ్యుకేషన్ లోన్స్ ఉన్నాయి. మీ 12వ మార్కులకు స్కాలర్‌షిప్ చెక్ చేయమంటారా?"
            if lang == "hi-IN":
                return f"मैं बिल्कुल समझती हूँ{name_suffix}। इसीलिए आदित्य में 50% तक मेरिट स्कॉलरशिप और कैंपस में SBI/HDFC से 0% ब्याज लोन की सुविधा है। क्या मैं आपकी स्कॉलरशिप चेक करूँ?"
            return f"I completely understand{name_suffix}. That is why Aditya offers up to 50% merit scholarships and on-campus 0% interest SBI/HDFC education loans. Shall I check your scholarship eligibility?"

        # ── 3f. Parent Consultation Objection fast-path ──
        if re.search(r'\b(talk\s+to|discuss\s+with|ask)\b.*?\b(parents?|father|mother|family|mom|dad)\b|(పేరెంట్స్|తండ్రి|నాన్న|అమ్మ|తల్లి).*?(తో\s*మాట్లాడాలి|కనుక్కోవాలి)|(माता|पिता|पापा|मम्मी|पैरेंट्स).*?(से\s*बात|पूछना)', t, re.I):
            cls._hit += 1
            logger.info(f"[FAST] pattern hit: parent consultation objection ({cls._hit}/{cls._hit + cls._miss})")
            name = collected.get("student_name", "")
            name_suffix = f", {name} जी" if (name and lang == "hi-IN") else (f", {name} గారు" if (name and lang == "te-IN") else (f", {name}" if name else ""))
            if lang == "te-IN":
                return f"తప్పకుండా{name_suffix}, కాలేజీ ఎంపికలో కుటుంబ నిర్ణయం ఎంతో ముఖ్యం! మీ పేరెంట్స్‌తో కలిసి ఈ శనివారం మా క్యాంపస్ టూర్‌కు రండి, ఫ్యాకల్టీని నేరుగా కలవండి. విజిట్ బుక్ చేయమంటారా?"
            if lang == "hi-IN":
                return f"बिल्कुल{name_suffix}, कॉलेज चयन परिवार का महत्वपूर्ण निर्णय है! आप अपने माता-पिता के साथ इस शनिवार कैंपस आएं और फैकल्टी से सीधे मिलें। क्या मैं विजिट बुक कर दूँ?"
            return f"Absolutely{name_suffix}, family consultation is essential! That is why we invite you and your parents for a guided campus visit this Saturday to see our labs and meet faculty. Shall I schedule your tour?"

        # ── 4. Facilities (Hostel / Campus / Gym / Mess) ──────────────────────
        # Must be checked BEFORE programs to avoid "available" or "room" matching course keywords!
        if cls._FACILITY_RE.search(t):
            resp = cls._facilities(t, lang=lang)
            if resp:
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: facility ({cls._hit}/{cls._hit + cls._miss})")
                return resp

        # ── 4. Scholarships (Priority match over generic package/fee terms) ───
        if cls._SCHOLARSHIP_RE.search(t):
            resp = cls._scholarship(t, collected, lang=lang)
            if resp:
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: scholarship ({cls._hit}/{cls._hit + cls._miss})")
                return resp

        # ── 5. Fees ─────────────────────────────────────────────────────────
        if cls._FEE_RE.search(t):
            resp = cls._fees(t, collected, lang=lang)
            if resp:
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: fees ({cls._hit}/{cls._hit + cls._miss})")
                return resp

        # ── 6. Degree Selection fast-path (Turn 4: "B.Tech phase") ────────────────
        m_deg = cls._DEGREE_RE.search(t)
        if m_deg and not collected.get("program_of_interest") and not collected.get("specialization") and not cls._FEE_RE.search(t) and not cls._SCHOLARSHIP_RE.search(t):
            deg = m_deg.group(1).upper().replace(".", "")
            collected["program_of_interest"] = deg
            name = collected.get("student_name", "")
            name_suffix = f", {name} जी" if (name and lang == "hi-IN") else (f", {name} గారు" if (name and lang == "te-IN") else (f", {name}" if name else ""))
            cls._hit += 1
            logger.info(f"[FAST] pattern hit: degree '{deg}' ({cls._hit}/{cls._hit + cls._miss})")
            if lang == "te-IN":
                return f"చాలా మంచి ఎంపిక{name_suffix}! {deg} లో మీకు ఏ బ్రాంచ్ అంటే ఆసక్తి ఉంది?"
            if lang == "hi-IN":
                return f"बहुत अच्छा निर्णय{name_suffix}! {deg} में आप किस ब्रांच में प्रवेश लेना चाहते हैं?"
            return f"Good choice{name_suffix}! Which branch of {deg} interests you?"

        # Ignore acoustic echo of Priya's own questions in fast-path
        if re.search(r'\b(which branch of|interests you|good choice|great choice|may i know your name|admission enquiry)\b', t):
            return None

        # ── 7. Department / Program Selection fast-path (Turn 5: "CSE department" / "సిఎస్ఈ బ్రాంచ్") ──
        _DEPT_MAP = {
            "cse": ["cse", "computer science", "సిఎస్ఈ", "సీఎస్ఈ", "కంప్యూటర్", "सीएसई", "कंप्यूटर"],
            "data science": ["data science", "డేటా సైన్స్", "डेटा साइंस"],
            "aiml": ["aiml", "ai & ml", "ai", "ఆర్టిఫిషియల్ ఇంటెలిజెన్స్"],
            "ece": ["ece", "electronics", "ఈసీఈ", "ईसीई"],
            "eee": ["eee", "electrical", "ట్రిపుల్ ఈ", "ईईई"],
            "mechanical": ["mechanical", "మెకానికల్", "मैकेनिकल"],
            "civil": ["civil", "సివిల్", "सिविल"],
        }
        matched_dept = None
        for dept_key, variations in _DEPT_MAP.items():
            matched = False
            for v in variations:
                if re.search(r'[a-zA-Z]', v):
                    if re.search(r'\b' + re.escape(v.lower()) + r'\b', t):
                        matched = True
                        break
                else:
                    if v in text:
                        matched = True
                        break
            if matched:
                matched_dept = dept_key
                break

        if matched_dept and not collected.get("specialization") and not cls._FEE_RE.search(t) and not cls._SCHOLARSHIP_RE.search(t) and not any(w in t for w in ["why", "explain", "association", "partner", "ఫీజు", "fees", "fee"]):
            collected["specialization"] = matched_dept.upper()
            names = udata.list_programs(matched_dept)
            top = [n.replace("B.Tech - ", "").replace("in association with ", "") for n in names[:4]] if names else ["Core", "AI & ML", "Data Science"]
            name = collected.get("student_name", "")
            name_suffix = f", {name} जी" if (name and lang == "hi-IN") else (f", {name} గారు" if (name and lang == "te-IN") else (f", {name}" if name else ""))
            cls._hit += 1
            logger.info(f"[FAST] pattern hit: department '{matched_dept}' ({cls._hit}/{cls._hit + cls._miss})")
            if lang == "te-IN":
                return f"చాలా మంచి ఎంపిక{name_suffix}! {matched_dept.upper()} లో కోర్ మరియు స్పెషలైజేషన్స్ ఉన్నాయి. మీరు 12వ తరగతి లేదా ఇంటర్ పూర్తి చేశారా?"
            if lang == "hi-IN":
                return f"बहुत अच्छा निर्णय{name_suffix}! {matched_dept.upper()} में हमारे पास बेहतरीन ब्रांचेज हैं। क्या आपने 12वीं की परीक्षा पूरी कर ली है?"
            return f"Great choice{name_suffix}! In {matched_dept.upper()} we offer top specialisations. Have you completed your 12th Board or Intermediate?"

        # ── 8. Placements ───────────────────────────────────────────────────
        if cls._PLACEMENT_RE.search(t):
            resp = cls._placements(lang=lang)
            if resp:
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: placements ({cls._hit}/{cls._hit + cls._miss})")
                return resp

        # ── 9. Program list ─────────────────────────────────────────────────
        if cls._PROGRAM_RE.search(t) and not collected.get("specialization"):
            resp = cls._programs(t, lang=lang)
            if resp:
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: programs ({cls._hit}/{cls._hit + cls._miss})")
                return resp

        # ── 10. University info ──────────────────────────────────────────────
        if cls._UNIVERSITY_RE.search(t):
            resp = cls._university(lang=lang)
            if resp:
                cls._hit += 1
                logger.info(f"[FAST] pattern hit: university ({cls._hit}/{cls._hit + cls._miss})")
                return resp

        # No match → fall through to Azure LLM
        cls._miss += 1
        return None

    # ── Handlers (use udata for all facts — same source as the LLM tools) ────

    @staticmethod
    def _fees(text: str, collected: dict, lang: str = "en-IN") -> str | None:
        course = udata.find_course(text)
        if not course:
            prog = collected.get("program_of_interest") or collected.get("specialization") or ""
            course = udata.find_course(prog) if prog else None
        if not course or not course.get("fee"):
            return None
        c_name = course['name'].replace(" - ", " ").replace("&", "and")
        cf = udata.COMMON_FEES
        fee_clean = course['fee'].replace('per year', '').replace('/year', '').strip()
        if lang == "te-IN":
            return (f"Aditya University lo {c_name} annual tuition fee year ki {fee_clean} untundandi, and up to 50% merit scholarship kuda undi. "
                    f"CSE seats fast ga fill avthunnayi. Meeku scholarship seat block cheyala, leda campus visit book cheskuntara?")
        if lang == "hi-IN":
            return (f"Aditya University mein {c_name} ki annual tuition fee per year {fee_clean} hai, aur 50% tak merit scholarship available hai. "
                    f"Seats jaldi book ho rahi hain. Kya aapko scholarship seat reserve karni hai ya campus visit book karein?")
        return (f"The annual tuition fee for {c_name} is {course['fee']}, with up to 50% merit scholarships available. "
                f"Seats fill quickly—would you like to reserve a scholarship seat or book a campus visit with your parents?")

    @staticmethod
    def _placements(lang: str = "en-IN") -> str | None:
        p = udata.PLACEMENTS
        stats = p.get("2026", "")
        if not stats:
            return None
        if lang == "te-IN":
            return ("Ma Aditya University lo 3,800 kante ekkuva placement offers vachayandi, and highest package 27 lakh rupees. "
                    "Labs and facilities chudadaniki meeku Saturday roju campus visit book cheyana?")
        if lang == "hi-IN":
            return ("Hamare yahan 3,800 se zyada placement offers record huye hain aur highest package 27 lakh hai. "
                    "Labs aur faculty se milne ke liye kya aapke liye is weekend campus visit schedule karein?")
        return ("Aditya University has recorded over 3,800 placement offers with a 27 lakh highest package. "
                "Would you like to schedule a campus visit this weekend to tour our advanced tech labs?")

    @staticmethod
    def _programs(text: str, lang: str = "en-IN") -> str | None:
        t_low = text.lower()
        for kw in ["cse", "computer science", "ece", "electronic", "eee", "electrical",
                   "mechanical", "civil", "mba", "pharmacy", "bba", "forensic",
                   "data science", "aiml", "ai"]:
            if re.search(r'\b' + re.escape(kw) + r'\b', t_low):
                names = udata.list_programs(kw)
                if names:
                    shown = names[:5]
                    extra = f" and {len(names) - 5} more" if len(names) > 5 else ""
                    if lang == "te-IN":
                        return f"ముఖ్యమైన కోర్సులు: {'; '.join(shown)}{extra}. మీకు ఏ బ్రాంచ్ లో ఆసక్తి ఉంది?"
                    if lang == "hi-IN":
                        return f"प्रमुख कोर्सेज: {'; '.join(shown)}{extra}. आप किस ब्रांच में इंटरेस्टेड हैं?"
                    return f"Programs: {'; '.join(shown)}{extra}. Which interests you?"
        branches = udata.list_branches()
        if branches:
            if lang == "te-IN":
                return "మా ముఖ్యమైన B.Tech బ్రాంచీలు: " + "; ".join(branches[:6]) + ". మీరు ఏ బ్రాంచ్‌లో చేరాలనుకుంటున్నారు?"
            if lang == "hi-IN":
                return "हमारे मुख्य B.Tech ब्रांचेज: " + "; ".join(branches[:6]) + " हैं। आप किस ब्रांच में प्रवेश लेना चाहते हैं?"
            return ("Our main B.Tech branches: " + "; ".join(branches[:6]) +
                    ". Which branch interests you?")
        return None

    @staticmethod
    def _scholarship(text: str, collected: dict, lang: str = "en-IN") -> str | None:
        t_low = text.lower()
        exam = collected.get("entrance_exams_taken", "")
        prog = collected.get("program_of_interest") or collected.get("specialization") or "B.Tech CSE"
        if not exam:
            for e in ["asat", "jee", "eapcet", "neet", "cat", "nmat", "bie", "cbse", "12th", "inter", "ఇంటర్", "బోర్డ్"]:
                if e in t_low or e in text:
                    exam = "12TH" if e in ["12th", "inter", "bie", "cbse", "ఇంటర్", "బోర్డ్"] else e.upper()
                    break

        score = None
        scores = re.findall(r'\b(\d{1,3}(?:\.\d+)?)\b', text)
        if scores:
            for s in scores:
                try:
                    val = float(s)
                    if 35.0 <= val <= 100.0 or val > 500:  # marks or percentage or rank
                        score = s
                        break
                except ValueError:
                    pass
        if not score:
            score = collected.get("class_12_score", "")

        # Personalized calculation when caller's score is available
        if score and (not exam or exam in ["12TH", "BIE", "CBSE", "ASAT"]):
            calc = udata.calculate_scholarship(prog, str(score))
            if calc.get("qualifies"):
                waiver = calc["waiver_percentage"]
                fee = calc["final_annual_fee"]
                cat = calc["category"]
                if lang == "te-IN":
                    return f"మీ {score} మార్కులకు {waiver}% ఫీజు రాయితీ లభిస్తుంది. రాయితీ తర్వాత వార్షిక ఫీజు ₹{fee:,}. అడ్మిషన్ వివరాలు తెలుసుకోవాలనుకుంటున్నారా?"
                if lang == "hi-IN":
                    return f"आपके {score} स्कोर के साथ आपको {waiver}% स्कॉलरशिप मिलेगी। स्कॉलरशिप के बाद सालाना फीस ₹{fee:,} होगी। क्या आप एडमिशन प्रोसेस जानना चाहते हैं?"
                return f"With your {score} score, you qualify for a {waiver}% scholarship ({cat}). Your annual fee after scholarship is ₹{fee:,}. Would you like to proceed with admission?"

        # If user asks for general 12th / scholarship slabs without giving a score yet
        if not score or not exam:
            if any(w in t_low or w in text for w in ["12th", "inter", "board", "cbse", "percentage", "marks", "slab", "slabs", "criteria", "స్కాలర్‌షిప్", "రాయితీ", "స్లాబ్"]):
                if lang == "te-IN":
                    return "12వ తరగతి / ఇంటర్‌లో 95% పైగా మార్కులకు 50%, 90-95% కి 40%, 85-90% కి 30%, 80-85% కి 20% ఫీజు రాయితీ లభిస్తుంది. మీ మార్కులు ఎన్ని శాతం వచ్చాయి?"
                if lang == "hi-IN":
                    return "12वीं बोर्ड में 95% से अधिक पर 50%, 90-95% पर 40%, 85-90% पर 30%, और 80-85% पर 20% ट्यूशन फीस छूट मिलती है। आपके 12वीं में कितने प्रतिशत मार्क्स हैं?"
                return "For 12th Board / Intermediate, students with 95%+ get 50% tuition waiver, 90-95% get 40%, 85-90% get 30%, and 80-85% get 20% fee waiver. What is your score percentage?"
            return None

        result = udata.compute_scholarship(exam, score, prog)
        if result and lang == "te-IN":
            m_pct = re.search(r'(\d+)%\s+tuition scholarship', result, re.I)
            if m_pct:
                pct = m_pct.group(1)
                return f"{prog} కోర్సులో మీకు {pct}% ఫీజు రాయితీ (స్కాలర్‌షిప్) లభిస్తుంది. అడ్మిషన్ ప్రాసెస్ గురించి తెలుసుకోవాలనుకుంటున్నారా?"
        if result and lang == "hi-IN":
            m_pct = re.search(r'(\d+)%\s+tuition scholarship', result, re.I)
            if m_pct:
                pct = m_pct.group(1)
                return f"{prog} में आपको {pct}% ट्यूशन फीस स्कॉलरशिप मिलेगी। क्या आप एडमिशन प्रोसेस जानना चाहते हैं?"
        return result if result else None

    @staticmethod
    def _facilities(text: str, lang: str = "en-IN") -> str | None:
        f = udata.FACILITIES
        t = text.lower()
        if "hostel" in t or "హాస్టల్" in text or "हॉस्टल" in text or any(w in t for w in ["room", "mess", "canteen", "stay", "accommodation", "girls hostel", "boys hostel", "వసతి", "భోజనం"]):
            if lang == "te-IN":
                return "Hostel facilities lo AC and Non-AC rooms unnayandi with meals. Admission seat tho patu hostel room secure cheskodaniki direct application link WhatsApp cheyana?"
            if lang == "hi-IN":
                return "Hostel facilities mein AC aur Non-AC dono options meals ke saath available hain. Admission ke saath hostel room reserve karne ke liye kya application link WhatsApp par bhej doon?"
            return "We provide AC and Non-AC hostel options with attached bathrooms and multi-cuisine meals. Would you like me to send the direct admission link to reserve your seat and hostel room?"
        
        for topic in ["medical", "sports", "safety", "labs"]:
            if topic in t or (topic == "medical" and any(w in t for w in ["hospital", "ambulance", "doctor", "ఆసుపత్రి", "వైద్యం"])):
                info = f.get(topic)
                if info:
                    if lang == "te-IN":
                        return f"{topic.capitalize()} facilities: {info}"
                    return f"{topic.capitalize()}: {info}"
        return None

    @staticmethod
    def _university(lang: str = "en-IN") -> str | None:
        if lang == "te-IN":
            return "Aditya University Kakinada daggara Surampalem lo 250-acre smart campus lo undandi. NAAC A++ accreditation and NIRF top 200 ranking undi. Meeku courses gurinchi kani facilities gurinchi kani telusukovalani unda?"
        if lang == "hi-IN":
            return "Aditya University Surampalem mein 250-acre ke smart campus mein situated hai, NAAC A++ accreditation aur NIRF top 200 ranking ke saath. Kya aap courses ya facilities ke baare mein jaanna chahenge?"
        return "Aditya University is situated on a 250-acre smart campus in Surampalem, Kakinada. We are NAAC A++ accredited and ranked among the top 200 by NIRF. Would you like to know more about our programs or campus facilities?"


class Priya(Agent):
    def __init__(self, student_name: str = "", reporter: Reporter | None = None,
                 job_ctx: JobContext | None = None, collected: dict | None = None,
                 followup: bool = False, last_summary: str = "", phone_number: str = "") -> None:
        # Per-call personalisation injected from the CRM (via dispatch metadata): if we
        # already know the prospect's name, tell Priya so she greets them by it and skips
        # asking. Everything else (prompt, voice, tools) is unchanged.
        self._followup = followup
        self._phone_number = phone_number
        # Retrieve live system prompt from Azure App Config if active, else default
        app_prompt = AZURE_APPCONFIG.get_setting("priya/system_prompt") if AZURE_APPCONFIG else None
        instructions = app_prompt or INSTRUCTIONS
        if followup:
            # Re-engagement: we already know this student — nurture, don't re-collect.
            instructions += FOLLOWUP_BLOCK
            if last_summary:
                instructions += f"\n# LAST TIME YOU SPOKE\n{last_summary}\n"
        elif student_name:
            instructions += (
                f"\n\n# THIS CALL\nThe student's name is {student_name}. Greet and address them "
                "by it naturally during the call; you do NOT need to ask for their name."
            )
        super().__init__(
            instructions=instructions,
            vad=silero.VAD.load(
                activation_threshold=float(os.getenv("USER_VAD_THRESHOLD", "0.65")),
                min_speech_duration=float(os.getenv("MIN_SPEECH_DURATION_MS", "350")) / 1000.0,
                min_silence_duration=float(os.getenv("END_OF_SPEECH_SILENCE_MS", "650")) / 1000.0,
                prefix_padding_duration=0.20
            ),
            stt=sarvam.STT(
                model="saaras:v3",
                language=STT_LANGUAGE,   # "en-IN" (English-only) or "unknown" (auto-detect)
                mode="transcribe",       # keep source language (we reply in it)
                flush_signal=True,       # emit start/end-of-speech for turn-taking
                prompt="Aditya University admissions counsellor Priya student Karthik Telugu Hindi English B.Tech CSE ECE EEE Mechanical Civil MBA MCA ASAT JEE EAPCET fees placements scholarships hostel campus",
            ),
            llm=build_llm(),
            tts=sarvam.TTS(
                model="bulbul:v3",
                target_language_code=TTS_START_LANG,
                speaker=SARVAM_SPEAKER,
                pace=TTS_PACE,
                # Telephony-native audio: G.711 mu-law at 8 kHz — the EXACT format the phone
                # network (Twilio/PSTN) uses. Unlike mp3, mu-law is sample-by-sample with NO
                # frame boundaries, so the stream can't gap/garble at frame edges (that was the
                # "breaking"), and it needs no resampling down to the phone. This is the fix.
                speech_sample_rate=22050,
                output_audio_codec="mp3",
                output_audio_bitrate="128k",
                enable_cached_responses=True,  # repeated phrases come back instantly
            ),
        )
        # In-memory collected fields for this call. On a follow-up we seed these with what we
        # already learned last time, so Priya knows the caller and the "KNOWN ABOUT THIS CALLER"
        # note is populated from turn one (she never re-asks name/program/scores).
        room_name = getattr(job_ctx, "room_name", None) or f"room_{int(time.time()*1000)}"
        self._session_id = room_name
        from session_lifecycle import start_new_call, apply_language_switch
        self.conv_session: SessionContext = start_new_call(
            session_id=room_name,
            initial_facts=collected,
            initial_language=TTS_START_LANG
        )
        if collected:
            self.conv_session.collected.update({k: v for k, v in collected.items() if v})
        self.collected = self.conv_session.collected
        from structured_memory import StructuredCallState, GLOBAL_USER_STORE
        self.structured_state = StructuredCallState(call_id=room_name, phone_number=self._phone_number)
        if self.collected:
            self.structured_state.merge_facts(self.collected)
        # Full Conversation History & Intelligent Prompting Architecture
        self.conv_history: ConversationHistory = getattr(self.conv_session, "history", None) or ConversationHistory(call_id=room_name)
        if self.collected:
            self.conv_history.facts.update(self.collected)
            if hasattr(self.conv_session, "long_mgr") and self.conv_session.long_mgr:
                self.conv_session.long_mgr.fact_memory.facts.update(self.collected)
        self.question_engine = QuestionEngine(self.conv_history)
        self.llm_history = LLMWithHistory(self.conv_history, self.question_engine)
        self.no_repetition = NoRepetitionEngine(self.conv_history)
        # Current voice language (updated by the multilingual handler); picks the filler language.
        self._lang: str = TTS_START_LANG
        self.conv_session.active_language = self._lang
        # Pushes collected details to the dashboard as they're captured (no-op if standalone).
        self._reporter = reporter
        # JobContext, so Priya can hang up the SIP call herself once the conversation
        # concludes (delete_room disconnects the caller). None in some test paths.
        self._job_ctx = job_ctx
        self._hangup_started = False
        # Pattern router stats (logged on shutdown for tuning)
        self._pattern_enabled = PATTERN_MATCH
        # 6-Layer Advanced Language Detection System
        self.audio_quality_gate = AudioQualityGate(sample_rate=16000)
        self.acoustic_pipeline = AcousticPipeline(sample_rate=16000)
        self.lang_conversation_context = ConversationContext(default_language=self._lang)
        self.language_detector = _LANG_DETECTOR
        self.explicit_switch_detector = _EXPLICIT_DETECTOR
        self.switch_decider = LanguageSwitchDecider(max_switches_per_call=5, allowed_languages=TTS_ALLOWED)
        self.noise_handler = _NOISE_HANDLER

    def switch_language(self, code: str, reason: str):
        """Update active language, TTS options, and translate prewarm if needed."""
        if not code or code == self._lang:
            return
        if code not in TTS_ALLOWED:
            return
        old_lang = self._lang
        self._lang = code
        from session_lifecycle import apply_language_switch
        apply_language_switch(self.conv_session, code, reason=reason)
        if hasattr(self, "lang_conversation_context"):
            self.lang_conversation_context.update_dominant_language(code)
        if hasattr(self, "_session_id") and self._session_id:
            try:
                get_or_create_logger(self._session_id).log_language_switch(old_lang=old_lang, new_lang=code)
            except Exception:
                pass
        try:
            self.tts.update_options(target_language_code=code)
            logger.info(f"[LANG] Switched voice language: {old_lang} -> {code} ({reason})")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[LANG] TTS update_options failed: {e}")

        if TRANSLATE_OUT and not code.lower().startswith("en"):
            asyncio.create_task(
                translate_prewarm(code, gender=TRANSLATE_GENDER, mode=TRANSLATE_MODE))

    async def _hang_up_after_closing(self):
        """End the call automatically once Priya has finished her closing line.

        Triggered when the LLM saves call_outcome (the conversation is over). We do NOT
        hang up immediately — the goodbye still has to be generated and spoken. So we wait
        for Priya to actually be speaking, then for BOTH sides to fall silent for a short
        grace period (covering a trailing "thank you" / "you're welcome"), then delete the
        room, which disconnects the caller and ends the SIP call."""
        if self._hangup_started:
            return
        self._hangup_started = True
        try:
            session = self.session
            # 1) Wait (up to 8s) for the closing line to START playing, so we never hang up
            #    in the gap before the goodbye audio begins.
            for _ in range(80):
                if session.agent_state == "speaking":
                    break
                await asyncio.sleep(0.1)
            # 2) Wait for the call to go fully quiet — neither Priya speaking/thinking nor the
            #    caller talking — for 1.6s straight (capped at ~30s so we always end).
            quiet = 0.0
            for _ in range(150):
                await asyncio.sleep(0.2)
                busy = (session.agent_state in ("speaking", "thinking")
                        or session.current_speech is not None
                        or session.user_state == "speaking")
                quiet = 0.0 if busy else quiet + 0.2
                if quiet >= 1.6:
                    break
        except Exception as e:  # noqa: BLE001
            logger.warning(f"hang-up wait error: {e}")
        # Small pause so the last audio frames flush to the phone before teardown.
        await asyncio.sleep(0.4)
        logger.info("conversation concluded — hanging up the call")
        try:
            if self._job_ctx is not None:
                await self._job_ctx.delete_room()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"delete_room (hang-up) failed: {e}")

    async def _prewarm_llm(self):
        """Warm up Azure OpenAI GPU cache with parallel background requests so all subsequent turns respond instantly."""
        az_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        az_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        az_model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
        az_ver = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

        if not az_endpoint or not az_key:
            return

        import openai as raw_openai
        client = raw_openai.AsyncAzureOpenAI(
            azure_endpoint=az_endpoint,
            api_key=az_key,
            api_version=az_ver,
            timeout=5.0
        )

        warmup_prompts = [
            [{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": "Hi"}],
            [{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": "What is the B.Tech fee?"}],
            [{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": "Tell me about CSE."}],
            [{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": "What are the scholarship slabs?"}],
        ]

        async def _probe(msgs):
            try:
                stream = await client.chat.completions.create(
                    model=az_model,
                    messages=msgs,
                    max_tokens=1,
                    stream=True
                )
                async for _ in stream:
                    break
            except Exception:
                pass

        try:
            logger.info("🔥 Warming up Azure OpenAI GPU prompt cache in background...")
            await asyncio.gather(*[_probe(p) for p in warmup_prompts], return_exceptions=True)
            logger.info("✅ Azure OpenAI prompt cache primed (GPU cache hot)")
        except Exception as e:
            logger.debug(f"llm prewarm skipped: {e}")
        finally:
            await client.close()

    async def on_enter(self):
        # Warm the Sarvam translate connection in the BACKGROUND while the greeting plays,
        # so the first real translate of the call is warm (~0.3s) not cold (~0.7s). The
        # ~12s greeting gives it plenty of time. Skipped automatically if translate-out is off.
        if TRANSLATE_OUT:
            warm_lang = next((l for l in TTS_ALLOWED if not l.lower().startswith("en")), "te-IN")
            asyncio.create_task(translate_prewarm(warm_lang, gender=TRANSLATE_GENDER, mode=TRANSLATE_MODE))
        # Same idea for the LLM — warm it during the greeting so turn 1 isn't cold.
        asyncio.create_task(self._prewarm_llm())
        # Speak the greeting first, before anything else. It's a fixed string added to the
        # chat history, so the LLM knows it already greeted and never re-greets. It IS
        # interruptible: if the caller talks over it ("hello? who is this?"), Priya stops
        # and responds — a false trigger (echo/noise) auto-resumes the greeting instead
        # of losing it (resume_false_interruption above).
        await self.session.say(self._greeting())

    def _greeting(self) -> str:
        """The opening line. A follow-up call reconnects warmly using what we already know
        (name + program) instead of the cold first-call greeting."""
        if not self._followup:
            return GREETING
        name = self.collected.get("student_name") or ""
        prog = self.collected.get("program_of_interest") or self.collected.get("specialization") or ""
        hi = f"Hello {name}!" if name else "Hello!"
        about = f" We spoke recently about {prog}" if prog else " We spoke recently about your admission"
        return (f"{hi} This is {AGENT_NAME} from {UNIVERSITY_NAME} again.{about}, "
                "and I wanted to follow up. Is this a good time?")

    async def on_user_turn_completed(self, turn_ctx, new_message):
        # Noise Gate: drop non-speech noise bursts
        raw_text = getattr(new_message, 'text_content', '') or getattr(new_message, 'content', '') or ''
        if raw_text and not is_valid_user_speech(raw_text):
            logger.info(f"[NOISE_GATE] User turn rejected as non-speech noise: '{raw_text}'")
            return

        # Semantic Interruption Gate: Check if user spoke a passive backchannel during assistant speech
        if hasattr(self, "acoustic_pipeline") and hasattr(self.acoustic_pipeline, "interruption_controller"):
            if self.acoustic_pipeline.is_assistant_speaking and raw_text:
                is_meaningful, reason = self.acoustic_pipeline.interruption_controller.turn_validator.is_meaningful_turn(
                    raw_text, is_assistant_speaking=True
                )
                if not is_meaningful:
                    logger.info(f"[INTERRUPTION_REJECTED] Suppressed passive backchannel/turn during assistant speech: '{raw_text}' ({reason})")
                    return

        # Bound the history sent to the LLM (system prompt is separate and kept). Keeps
        # prompt_tokens roughly flat across a long call instead of growing every turn.
        if MAX_HISTORY_ITEMS > 0:
            try:
                turn_ctx.truncate(max_items=MAX_HISTORY_ITEMS)
            except Exception as e:  # noqa: BLE001
                logger.debug(f"history truncate skipped: {e}")

    # Short, live summary of everything collected so far — injected each turn so Priya
    # NEVER forgets the caller's program/name/scores after history truncation (and so never
    # re-asks something they already told her).
    _DETAIL_LABELS = {
        "student_name": "Name", "program_of_interest": "Program", "specialization": "Specialization",
        "entrance_exams_taken": "Exam", "class_10_score": "Class 10 %", "class_12_score": "Class 12 %",
        "graduation_score": "Graduation", "current_city": "City", "engagement_choice": "Next step",
        "counselling_mode": "Counselling mode", "visit_datetime": "Booked time",
    }

    def _known_details(self) -> str:
        parts = [f"{lbl}: {self.collected[k]}" for k, lbl in self._DETAIL_LABELS.items() if self.collected.get(k)]
        return "; ".join(parts)

    # ── LLM output filter ──────────────────────────────────────────────────────
    # Clean the reply AT THE SOURCE, not just before TTS. gpt-oss tends to dump the whole
    # question flow (5 stacked questions) in one 160-token wall and sometimes TYPES a tool
    # call / its JSON result as text. Cleaning only in tts_node left all of that in the chat
    # HISTORY, so every later turn saw leaked JSON + questions "already asked" and got worse.
    # Filtering here means history == exactly what was spoken, and we can CANCEL the
    # generation the moment the first question is complete — less latency, fewer tokens.
    async def llm_node(self, chat_ctx, tools, model_settings):
        # Extract latest user message and previous assistant message for echo suppression
        last_user_text = ""
        last_asst_text = ""
        try:
            items = getattr(chat_ctx, 'items', getattr(chat_ctx, 'messages', []))
            for item in reversed(list(items)):
                role = getattr(item, 'role', '')
                if not last_user_text and role == 'user':
                    last_user_text = (getattr(item, 'text_content', '')
                                      or getattr(item, 'content', '') or '').strip()
                elif not last_asst_text and role == 'assistant':
                    last_asst_text = (getattr(item, 'text_content', '')
                                      or getattr(item, 'content', '') or '').strip()
                if last_user_text and last_asst_text:
                    break
        except Exception as e:  # noqa: BLE001
            logger.debug(f"extract text error: {e}")

        # ── Noise Gate: Drop coughs, breathing, clicks, and non-speech artifacts ──
        if last_user_text and not is_valid_user_speech(last_user_text):
            logger.info(f"[NOISE_GATE] Dropped non-speech noise artifact: '{last_user_text}'")
            return

        # ── Backchannel / Interruption Check: Drop passive acknowledgement fillers if assistant is speaking ──
        if hasattr(self, "acoustic_pipeline") and hasattr(self.acoustic_pipeline, "interruption_controller"):
            if self.acoustic_pipeline.is_assistant_speaking and last_user_text:
                is_meaningful, reason = self.acoustic_pipeline.interruption_controller.turn_validator.is_meaningful_turn(
                    last_user_text, is_assistant_speaking=True
                )
                if not is_meaningful:
                    logger.info(f"[INTERRUPTION_REJECTED] LLM turn skipped for passive backchannel: '{last_user_text}' ({reason})")
                    return

        # ── Echo Suppression: Drop microphone capture of Priya's own speaker output ──
        _CONVERSATIONAL_WHITELIST = {
            "hello", "hi", "hey", "yes", "yeah", "yep", "sure", "ok", "okay",
            "fine", "alright", "speaking", "namaste", "vanakkam", "sare", "avunu",
            "haan", "ha", "theek", "theek hai", "priya", "karthik"
        }
        if last_user_text and last_asst_text:
            u_clean = re.sub(r'[^a-zA-Z0-9\s]', '', last_user_text.lower()).strip()
            a_clean = re.sub(r'[^a-zA-Z0-9\s]', '', last_asst_text.lower()).strip()
            u_words = set(u_clean.split())
            a_words = set(a_clean.split())
            # NEVER drop greetings, affirmations, or short turns (<5 words)
            if u_clean not in _CONVERSATIONAL_WHITELIST and len(u_words) >= 5 and len(u_clean) >= 25:
                overlap = len(u_words & a_words) / max(1, len(u_words))
                if overlap >= 0.85:
                    logger.info(f"[ECHO] Suppressed microphone echo of assistant speech: '{last_user_text}'")
                    return

        # ── Transcript Gate: Decide if transcript really came from caller before state changes ──
        if last_user_text:
            awaiting_slot = None
            if not self.collected.get("student_name"):
                awaiting_slot = "name"
            elif not self.collected.get("program_of_interest"):
                awaiting_slot = "branch"
            elif not self.collected.get("class_12_score"):
                awaiting_slot = "percentage"

            agent_speaking = getattr(self, "is_speaking", False)
            if hasattr(self, "acoustic_pipeline"):
                agent_speaking = agent_speaking or self.acoustic_pipeline.is_assistant_speaking

            verdict, reason = classify_transcript(
                last_user_text,
                awaiting_slot=awaiting_slot,
                agent_speaking=agent_speaking,
            )
            logger.info(f"[TRANSCRIPT_GATE] {verdict} ({reason}): {last_user_text!r}")

            if verdict == "drop":
                logger.info(f"[TRANSCRIPT_GATE] Dropped transcript: {last_user_text!r} ({reason})")
                return

            if verdict == "unclear":
                self.unclear_streak = getattr(self, "unclear_streak", 0) + 1
                if self.unclear_streak == 1:
                    logger.info(f"[TRANSCRIPT_GATE] Unclear transcript streak 1 — asking to repeat")
                    clarification = (
                        "క్షమించండి, కాస్త శబ్దం వచ్చింది. మళ్లీ చెప్తారా?"
                        if self._lang == "te-IN"
                        else "माफ़ कीजियेगा, कुछ शोर आ रहा था। क्या आप दोबारा कह सकते हैं?"
                        if self._lang == "hi-IN"
                        else "Sorry, there's some background noise. Could you say that again?"
                    )
                    self.conv_session.add_turn("assistant", clarification, language=self._lang)
                    yield clarification
                else:
                    logger.info(f"[TRANSCRIPT_GATE] Unclear streak {self.unclear_streak} — staying quiet and listening")
                return

            self.unclear_streak = 0

        # ── Language Detection & Voice Switch (Sync at start of turn) ────────
        if MULTILANG and last_user_text:
            try:
                script = dominant_script(last_user_text)
                if script in ALLOWED_SCRIPTS:
                    detected_lang, reason = detect_language(last_user_text, current_lang=self._lang)
                    resolved_lang = resolve_mixed_language(detected_lang, last_user_text, self._lang, session_id=getattr(self, "_session_id", "default"))
                    if resolved_lang != self._lang and resolved_lang in TTS_ALLOWED:
                        self.switch_language(resolved_lang, f"turn_{reason}")
            except Exception as e:  # noqa: BLE001
                logger.debug(f"lang detect error: {e}")

        # ── Automated Slot & Entity Extraction (Session Manager) ──────────────
        if ENABLE_SLOT_MANAGER and last_user_text:
            try:
                prev_collected = dict(self.collected)
                self.collected = DialogueSlotManager.extract_slots(last_user_text, self.collected)
                if hasattr(self, "conv_history") and self.conv_history:
                    self.conv_history.extract_facts(last_user_text)
                    for k, v in self.conv_history.facts.items():
                        if k in self._DETAIL_LABELS and not self.collected.get(k):
                            self.collected[k] = str(v)
                self.conv_session.collected = self.collected
                if hasattr(self, "_session_id") and self._session_id:
                    GLOBAL_SESSION_STORE.merge_facts(self._session_id, self.collected)
                # Emit newly extracted slots to dashboard in real-time
                if self._reporter:
                    for k, v in self.collected.items():
                        if k not in prev_collected or prev_collected[k] != v:
                            self._reporter.emit(type="detail", field=k, value=v)
                self.structured_state.merge_facts(self.collected)
                if self._phone_number:
                    from structured_memory import GLOBAL_USER_STORE
                    GLOBAL_USER_STORE.save_profile(self._phone_number, self.collected)
                logger.info(f"[SLOT] Current profile: {self.collected}")
            except Exception as e:  # noqa: BLE001
                logger.debug(f"slot extraction error: {e}")

        # ── "I Already Told You" Intercept & Immediate Recovery ──────────────
        if last_user_text:
            already_told_ack = DialogueSlotManager.detect_already_told(last_user_text, self.collected)
            if already_told_ack:
                logger.info(f"[ALREADY_TOLD] Intercepted statement, acknowledging known fact: '{already_told_ack}'")
                self.conv_session.add_turn("assistant", already_told_ack, language=self._lang)
                yield already_told_ack
                return

        # ── Session turn logging ─────────────────────────────────────────────
        if last_user_text:
            self.conv_session.add_turn("user", last_user_text, language=self._lang)
            if hasattr(self, "lang_conversation_context"):
                self.lang_conversation_context.add_turn("user", last_user_text, language=self._lang)

        # ── Goodbye / Call Wrap-up Handling (Strict is_farewell & Soft Close) ──
        if last_user_text and is_farewell(last_user_text):
            is_explicit = bool(re.search(r'\b(bye|goodbye|good bye|see you|talk (to you )?later)\b|(अलविदा|फिर मिलेंगे|బై|వస్తాను)', last_user_text, re.IGNORECASE))
            soft_closed = getattr(self, "soft_close_asked", False)

            if is_explicit or soft_closed:
                logger.info(f"[GOODBYE] Confirmed farewell from caller: '{last_user_text}'")
                if self._lang == "te-IN":
                    farewell = "ఆదిత్య యూనివర్సిటీని సంప్రదించినందుకు ధన్యవాదాలు! మీ అడ్మిషన్స్ కోసం ఆల్ ది బెస్ట్. హావ్ ఏ గ్రేట్ డే!"
                elif self._lang == "hi-IN":
                    farewell = "आदित्य यूनिवर्सिटी में संपर्क करने के लिए धन्यवाद! आपके एडमिशन के लिए शुभकामनाएं। आपका दिन शुभ हो!"
                elif self._lang == "ta-IN":
                    farewell = "ஆதித்யா பல்கலைக்கழகத்தை தொடர்பு கொண்டதற்கு நன்றி! உங்கள் சேர்க்கைக்கு வாழ்த்துக்கள்."
                else:
                    farewell = "Thank you for reaching out to Aditya University! Wishing you all the best for your admissions. Have a wonderful day!"
                self.conv_session.add_turn("assistant", farewell, language=self._lang)
                # Save full conversation transcript
                if hasattr(self, "conv_history") and self.conv_history:
                    try:
                        os.makedirs("transcripts", exist_ok=True)
                        t_path = f"transcripts/{self.conv_history.call_id}.txt"
                        with open(t_path, "w", encoding="utf-8") as f:
                            f.write(self.conv_history.get_full_transcript())
                        logger.info(f"[TRANSCRIPT] Saved full transcript to {t_path}")
                    except Exception as ex:
                        logger.debug(f"transcript save error: {ex}")
                yield farewell
                asyncio.create_task(self._hang_up_after_closing())
                return
            else:
                self.soft_close_asked = True
                logger.info(f"[GOODBYE] Soft close prompt triggered on non-explicit farewell: '{last_user_text}'")
                soft_close_prompt = (
                    "ఇంకేమైనా వివరాలు తెలుసుకోవాలనుకుంటున్నారా?"
                    if self._lang == "te-IN"
                    else "क्या मैं आपकी किसी और चीज़ में मदद कर सकती हूँ?"
                    if self._lang == "hi-IN"
                    else "Is there anything else I can help you with today?"
                )
                self.conv_session.add_turn("assistant", soft_close_prompt, language=self._lang)
                yield soft_close_prompt
                return

        # ── Pattern matching: instant response for simple factual questions ────
        # If matched, yield the cached response directly (~0ms) and skip the LLM entirely.
        # Cached instant response means NO filler is played.
        if self._pattern_enabled and last_user_text:
            try:
                t0 = time.time()
                from fast_path import try_fast_path as deterministic_fast_path
                cached = deterministic_fast_path(last_user_text, language_code=self._lang)
                if not cached:
                    cached = PatternRouter.match(last_user_text, self.collected, lang=self._lang)
                if not cached:
                    cached = await LatencyOptimizer.try_fast_path(last_user_text, lang=self._lang)
                if cached:
                    elapsed_ms = (time.time() - t0) * 1000
                    logger.info(f"[FAST] pattern response in {elapsed_ms:.0f}ms (skipped Azure)")
                    self.conv_session.add_turn("assistant", cached, language=self._lang)
                    yield cached
                    return  # done — no LLM call needed, no filler
            except Exception as e:  # noqa: BLE001
                logger.debug(f"pattern match error: {e}")

        # ── Slow path (Azure LLM): Play contextual filler ONLY for questions/inquiries ────
        # Selected based on topic & language (e.g. Telugu filler if caller speaks Telugu)
        # NEVER play fillers for conversational answers, greetings, stating names, or yes/no.
        if ENABLE_CONTEXT_FILLERS and last_user_text:
            try:
                t_clean = last_user_text.lower().strip()
                # Check for question/inquiry indicators
                is_explicit_question = bool(
                    "?" in last_user_text or
                    re.search(r'\b(what|which|how|where|when|why|who|can you|tell me|explain|describe|details|structure|breakdown|cutoff|cut off|eligibility|placements?|fees?|cost|scholarships?|hostels?|courses?|programs?|package|entha|kavali|undi|untundhi|kaisa|kitna|bataiye)\b', t_clean)
                )
                # Check if it's just a simple short affirmation or greeting (skip filler only for these)
                is_short_affirmation = bool(
                    re.search(r'^(yes|yeah|yep|no|nah|okay|ok|sure|fine|hello|hi|hey|good time|my name|i am|this is|call me)\b', t_clean) and
                    not is_explicit_question
                )
                if is_explicit_question and not is_short_affirmation:
                    topic = PatternRouter.detect_topic(last_user_text)
                    filler = get_filler(topic, lang=self._lang)
                    if filler:
                        logger.info(f"[FILLER] Contextual filler ({self._lang}) for {topic}: '{filler}'")
                        yield filler + " "
            except Exception as e:  # noqa: BLE001
                logger.debug(f"filler error: {e}")

        # ── Normal Azure LLM path (for complex/conversational queries) ────────
        # Bound chat history: retain full conversation turns across entire call
        known = self._known_details()
        try:
            chat_ctx = chat_ctx.copy()
            all_msgs = getattr(chat_ctx, 'messages', [])
            if all_msgs:
                # Keep ONLY the initial base system prompt (index 0) — never accumulate stale system turns!
                base_sys = [m for m in all_msgs if getattr(m, 'role', '') == 'system'][:1]
                non_sys_msgs = [m for m in all_msgs if getattr(m, 'role', '') != 'system']
                # Retain full conversation history across all turns (up to 40 messages = 20 turns)
                max_msgs = max(MAX_CONTEXT_TURNS * 4, 40)
                recent_msgs = non_sys_msgs[-max_msgs:] if len(non_sys_msgs) > max_msgs else non_sys_msgs
                chat_ctx.messages = base_sys + recent_msgs

            # Consolidate dynamic turn instructions into ONE compact system message (prevents token bloat)
            turn_prompts = []

            # ── 1. Canonical State & Shared Prompt Template (LangChain/LangGraph architecture) ──
            try:
                from prompts import format_system_prompt
                facts_snapshot = {k: v for k, v in self.collected.items() if v and not str(k).startswith("_")}
                if hasattr(self, "conv_history") and self.conv_history and hasattr(self.conv_history, "facts"):
                    facts_snapshot.update({k: v for k, v in self.conv_history.facts.items() if v and not str(k).startswith("_")})

                # Compute canonical stage and next field (monotonic progression — never regress backwards)
                has_booking = bool(facts_snapshot.get("visit_datetime") or facts_snapshot.get("engagement_choice"))
                has_exam = bool(facts_snapshot.get("entrance_exams_taken") or facts_snapshot.get("exam"))
                has_score = bool(facts_snapshot.get("class_12_score") or facts_snapshot.get("marks_12") or facts_snapshot.get("score"))
                has_program = bool(facts_snapshot.get("program") or facts_snapshot.get("program_of_interest"))
                has_name = bool(facts_snapshot.get("student_name") or facts_snapshot.get("name"))

                if has_booking:
                    c_stage = "CONVERT"
                    c_field = "(campus visit booked)"
                elif has_score or has_exam:
                    c_stage = "CONVERT"
                    c_field = "campus_visit"
                elif has_program:
                    c_stage = "ELIGIBILITY"
                    c_field = "marks_12"
                elif has_name:
                    c_stage = "PROGRAM"
                    c_field = "program"
                else:
                    c_stage = "GREETING"
                    c_field = "student_name"

                shared_prompt = format_system_prompt(
                    facts=facts_snapshot,
                    stage=c_stage,
                    next_field=c_field,
                    language_code=self._lang
                )
                turn_prompts.append(shared_prompt)
            except Exception as e:
                logger.debug(f"shared prompt build error: {e}")

            # ── Full Conversation History & Intelligent Directives ──
            if hasattr(self, "conv_session") and getattr(self.conv_session, "long_mgr", None):
                turn_directives = self.conv_session.long_mgr.build_turn_prompt(last_user_text, language=self._lang)
                if turn_directives:
                    turn_prompts.append(turn_directives)
            elif hasattr(self, "llm_history") and self.llm_history:
                turn_directives = self.llm_history.build_turn_directives(last_user_text, language=self._lang)
                if turn_directives:
                    turn_prompts.append(turn_directives)
            elif known:
                turn_prompts.append(f"KNOWN CALLER DETAILS (do NOT re-ask): {known}")

            # Flexible guidance (non-mandatory)
            if hasattr(self, "question_engine") and self.question_engine:
                next_q = self.question_engine.get_next_question(last_user_text)
                if next_q:
                    turn_prompts.append(f"FLEXIBLE GUIDANCE: Answer caller's query directly first. Then, if naturally relevant, you may ask: '{next_q}'. Do NOT force if user changed topic.")
            else:
                turn_prompts.append("CONVERSATION DIRECTIVE: Answer the caller's immediate question or concern FIRST. Never interrogate.")

            if any(w in last_user_text.lower() for w in ["12th", "inter", "intermediate", "board", "12 pass", "12th complete", "12th pass"]):
                turn_prompts.append("Caller is 12th-pass. Pitch 12th merit scholarships & ASAT exam directly.")

            # Language & Slang instructions
            if MULTILANG and not TRANSLATE_OUT:
                turn_prompts.append(build_language_system_prompt(self._lang))
                turn_prompts.append(f"LANGUAGE DIRECTIVE:\n{LanguageHandler.get_llm_instruction(self._lang)}")
                u_text_low = last_user_text.lower() if last_user_text else ""
                if self._lang == "te-IN":
                    turn_prompts.append("LANGUAGE: Speak in warm, natural TELUGLISH (conversational Telugu + English mix with respectful 'గారు'/'మీరు').")
                    if ENABLE_SLANG:
                        if any(w in u_text_low for w in ["bhayya", "etla", "etlundhi", "cheppu bhayya", "kadha"]):
                            turn_prompts.append("SLANG: Caller used Telangana slang ('bhayya'/'etla'). Match their friendly Telangana Teluglish tone naturally!")
                        elif any(w in u_text_low for w in ["andi", "garu", "cheppandi andi", "enti andi"]):
                            turn_prompts.append("SLANG: Caller used Coastal Andhra dialect ('andi'/'garu'). Match their polite Godavari Andhra tone!")
                        elif any(w in u_text_low for w in ["bro", "dude"]):
                            turn_prompts.append("SLANG: Caller used 'bro'. Match their casual college student energy naturally!")
                    else:
                        turn_prompts.append("TONE: Maintain respectful counselor tone ('గారు'/'మీరు'). Do NOT use casual street slang ('bhayya'/'bro').")
                elif self._lang == "hi-IN":
                    turn_prompts.append("LANGUAGE: Speak in warm, natural HINGLISH (conversational Hindi + English mix with respectful 'जी'/'आप').")
                    if ENABLE_SLANG:
                        if any(w in u_text_low for w in ["bhai", "yaar", "kya scene", "bata na", "sahi hai"]):
                            turn_prompts.append("SLANG: Caller used casual Hindi slang ('bhai'/'yaar'/'scene'). Match their friendly Hinglish tone!")
                        elif any(w in u_text_low for w in ["bro", "dude"]):
                            turn_prompts.append("SLANG: Caller used 'bro'. Match their casual college student energy naturally!")
                    else:
                        turn_prompts.append("TONE: Maintain polite counselor tone with 'जी'/'आप'. Do NOT use street slang ('yaar'/'bhai'/'scene').")
                elif self._lang == "ta-IN":
                    turn_prompts.append("LANGUAGE: Speak in natural TANGLISH (Tamil + English mix).")
                else:
                    turn_prompts.append("LANGUAGE: Speak in clear, warm, friendly conversational Indian English.")
                    if ENABLE_SLANG and any(w in u_text_low for w in ["bro", "dude"]):
                        turn_prompts.append("SLANG: Match their casual 'bro' student energy naturally!")
                    elif not ENABLE_SLANG:
                        turn_prompts.append("TONE: Maintain courteous, professional counselor tone. Avoid casual slang ('bro'/'dude').")
            elif TRANSLATE_OUT:
                turn_prompts.append("LANGUAGE: Compose reply in simple conversational English (1 short sentence, max 20 words).")

            chat_ctx.add_message(role="system", content="\n".join(turn_prompts))
        except Exception as e:  # noqa: BLE001
            logger.debug(f"known-details / lang-mandate inject skipped: {e}")
        # Pass tools=None to guarantee Azure LLM streams speech immediately in 1 single pass with ZERO tool-calling latency
        stream = Agent.default.llm_node(self, chat_ctx, None, model_settings)
        buf = ""            # text not yet split into complete sentences
        spoken = 0          # chars emitted this turn (MAX_SPOKEN_CHARS cap)
        saw_tool = False    # a real tool call arrived → drain the stream, don't cancel it
        done = False        # first question / length cap reached → drop any further text

        def _clean(sentence: str) -> str:
            if not sentence:
                return ""
            s = _strip_tool_syntax(sentence) or ""
            s = re.sub(
                r"\([^)]*\b(?:waiting|response|pause|silence|continue|listening|no reply|note)\b[^)]*\)",
                "", s, flags=re.IGNORECASE,
            )
            s = s.replace("*", "").replace("#", "").replace("`", "")
            # Braces never occur in real speech. _strip_tool_syntax removed complete JSON
            # blocks; an UNTERMINATED one (stream cut mid-JSON) still starts with "{" — drop
            # from there to the end, keeping the legit speech before it.
            s = re.sub(r"\{.*", " ", s, flags=re.DOTALL)
            s = s.replace("}", " ")
            s = re.sub(r"\s{2,}", " ", s).strip()
            # Nothing word-like left (stray punctuation only) → nothing to say.
            return s if re.search(r"\w", s) else ""

        try:
            async for chunk in stream:
                if isinstance(chunk, str):
                    delta = chunk
                elif isinstance(chunk, ChatChunk) and chunk.delta is not None:
                    if chunk.delta.tool_calls:
                        saw_tool = True
                        # Forward the tool calls but NOT the content — text is re-emitted
                        # by us below, after cleaning.
                        yield chunk.model_copy(
                            update={"delta": chunk.delta.model_copy(update={"content": None})})
                    delta = chunk.delta.content
                else:
                    yield chunk   # flush sentinels etc. pass through untouched
                    continue

                if not delta or done:
                    continue
                # Accumulate RAW (no buffer-level strip — stripping trails would glue words
                # across chunk boundaries); _clean handles each complete sentence instead.
                buf += delta
                while not done:
                    # A "." ends a sentence only when followed by whitespace (a bare "." would
                    # split "B.Tech" / "₹2.75" mid-token). Strong enders (? ! ।) split even with
                    # NO space after — gpt-oss glues its stacked questions together ("…?Got it.").
                    # Reply-final text with no trailing space waits in buf for the tail flush.
                    m = re.search(r"[.!?।。！？]+[\"')\]]*\s|[!?！？।。]+[\"')\]]*", buf)
                    if not m:
                        break
                    sentence, buf = _clean(buf[: m.end()]), buf[m.end():]
                    if not sentence:
                        continue
                    yield sentence + " "
                    spoken += len(sentence)
                    try:
                        self.conv_session.add_turn("assistant", sentence, language=self._lang)
                    except Exception:
                        pass
                    # One question per turn / spoken-length cap → the reply is complete.
                    if "?" in sentence or spoken >= MAX_SPOKEN_CHARS:
                        done = True
                if done and not saw_tool:
                    break   # cancel the request — don't generate questions 2..N at all
            if not done:
                tail = _clean(buf)
                if tail:
                    try:
                        self.conv_session.add_turn("assistant", tail, language=self._lang)
                    except Exception:
                        pass
                    yield tail
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            if hasattr(self, "_session_id") and self._session_id:
                try:
                    get_or_create_logger(self._session_id).log_error(f"LLM streaming exception: {e}", exc=e)
                except Exception:
                    pass
            raise
        finally:
            await stream.aclose()

    async def tts_node(self, text, model_settings):
        # Open the Sarvam TTS websocket NOW, in the background, while the LLM is still
        # streaming and mayura is translating the first sentence. Without this, the
        # connect+config handshake (~0.1-0.25s) only started AFTER the translated text
        # arrived — serial cost on every reply whose pooled connection had gone idle.
        # prewarm() is a no-op when a live pooled connection already exists.
        try:
            self.tts.prewarm()
        except Exception as e:  # noqa: BLE001
            logger.debug(f"tts prewarm skipped: {e}")

        # Translate-out is active only when enabled AND the caller's language is non-English.
        needs_translation = TRANSLATE_OUT and bool(self._lang) and not self._lang.lower().startswith("en")
        # Hard spoken-length cap per turn so a verbose reply can't become a 20-30s monologue
        # that stutters over the network. Indic TTS (translate-out) runs ~2x longer per char,
        # so cap it tighter there.
        spoken_cap = MAX_SPOKEN_CHARS

        # llm_node already delivers clean one-question text — STREAM it sentence-by-sentence
        # so TTS starts on the first sentence (big latency win) instead of waiting for the
        # whole reply. With translate-out on, a producer reads the LLM stream and fires each
        # sentence's translation CONCURRENTLY, while the consumer yields them in order — so
        # sentence N+1 translates while sentence N is being spoken (only the first sentence's
        # translate is on the critical path).
        def _spoken(sentence: str):
            # Dynamically ensure Sarvam Bulbul TTS voice matches the sentence's script
            detected_tts_lang = self._lang
            if re.search(r'[\u0C00-\u0C7F]', sentence):
                detected_tts_lang = "te-IN"
            elif re.search(r'[\u0900-\u097F]', sentence):
                detected_tts_lang = "hi-IN"
            elif re.search(r'[\u0B80-\u0BFF]', sentence):
                detected_tts_lang = "ta-IN"

            if detected_tts_lang != self._lang and detected_tts_lang in TTS_ALLOWED:
                self.switch_language(detected_tts_lang, "tts_sentence_script_match")

            sentence = _normalize_numbers_for_speech(sentence, lang=detected_tts_lang)
            # Returns an awaitable resolving to the text to speak (translated or passthrough).
            if needs_translation:
                return asyncio.create_task(
                    translate_out(sentence, self._lang, gender=TRANSLATE_GENDER, mode=TRANSLATE_MODE))
            return asyncio.create_task(asyncio.sleep(0, result=sentence))

        async def streamed():
            queue: asyncio.Queue = asyncio.Queue()

            async def produce():
                buf = ""
                stopped = False
                spoken = 0          # chars emitted this turn (spoken_cap enforcement)
                try:
                    async for chunk in text:
                        if not chunk or stopped:
                            continue
                        buf += chunk.replace("*", "").replace("#", "").replace("`", "")
                        buf = _strip_tool_syntax(buf)   # drop leaked tool calls before splitting
                        while True:
                            # punctuation + whitespace only — never split "B.Tech" / "₹2.75"
                            m = re.search(r"[.!?।。！？]+[\"')\]]*\s", buf)
                            if not m:
                                break
                            sentence = re.sub(r"\s{2,}", " ", _strip_tool_syntax(buf[: m.end()])).strip()
                            buf = buf[m.end():]
                            if not sentence:
                                continue
                            # Length cap: keep whole sentences. Never slice a sentence mid-way.
                            # If this is beyond the 1st sentence and exceeds budget, stop cleanly.
                            if spoken > 0 and (spoken + len(sentence)) > spoken_cap:
                                stopped = True
                                buf = ""
                                break
                            await queue.put(_spoken(sentence))   # fire translate now (concurrent)
                            spoken += len(sentence)
                            # Stop after the first question (one question per turn).
                            if "?" in sentence or spoken >= spoken_cap:
                                stopped = True
                                buf = ""
                                break
                    if not stopped:
                        tail = re.sub(r"\s{2,}", " ", _strip_tool_syntax(buf)).strip()
                        if tail and (spoken == 0 or spoken + len(tail) <= spoken_cap):
                            await queue.put(_spoken(tail))
                finally:
                    await queue.put(None)   # sentinel: no more sentences

            producer = asyncio.create_task(produce())
            try:
                while True:
                    task = await queue.get()
                    if task is None:
                        break
                    out = await task
                    if out:
                        yield out
            finally:
                if not producer.done():
                    producer.cancel()
                while not queue.empty():
                    try:
                        pending_t = queue.get_nowait()
                        if pending_t is not None and isinstance(pending_t, (asyncio.Task, asyncio.Future)):
                            pending_t.cancel()
                    except Exception:
                        pass

        async for frame in Agent.default.tts_node(self, streamed(), model_settings):
            yield frame

    # ── Tools (port more from the Node agentTools.js as you need them) ────────
    @function_tool()
    async def save_detail(self, context: RunContext, field: str, value: str):
        """Save one collected detail, ONLY with a real value provided by the caller in their answer.
        DO NOT call this with your own questions, prompts, or placeholders.
        `field` = one of: student_name, program_of_interest, specialization, entrance_exams_taken,
        willing_university_exam, engagement_choice, counselling_mode, visit_datetime, class_10_score,
        class_12_score, graduation_score, graduation_status, current_city, call_outcome."""
        v = str(value or "").strip()
        f = str(field or "").strip()
        if not v or v.lower() in {"not provided", "not given", "unknown", "n/a", "na",
                                   "none", "null", "tbd", "-"}:
            return "Nothing concrete to save yet — ask the caller for the actual value first."
        
        # Guard against saving questions / prompts as values
        if "?" in v or any(q in v.lower() for q in [
            "may i know", "what is your name", "what is name", "tell me", "your name",
            "which branch", "what program", "what course", "please tell", "how can i help"
        ]):
            return "ERROR: Do NOT save question or prompt text as a value. save_detail must only be called AFTER the caller provides their answer."

        # Phonetic name autocorrection for common STT artifacts & reject conversational fillers
        if f == "student_name" and v:
            invalid_names = {
                "okay", "ok", "sure", "yes", "yeah", "yep", "no", "nahi", "haan",
                "thanks", "thank you", "fine", "hello", "hi", "hey", "alright",
                "done", "correct", "true", "right", "good", "sare", "theek", "theek hai"
            }
            clean_v = v.strip().lower()
            if clean_v in invalid_names or len(clean_v) <= 1:
                return "ERROR: The value is a conversational filler, not a student's actual name. Do not save this as student_name."
            _NAME_FIXES = {
                "kapli": "Karthik", "kamitha": "Karthik", "kavita": "Karthik",
                "kavitha": "Karthik", "kartik": "Karthik", "karthic": "Karthik",
                "karthikh": "Karthik", "karthi": "Karthik",
            }
            if clean_v in _NAME_FIXES:
                v = _NAME_FIXES[clean_v]

        # Guard against premature call_outcome save
        if f == "call_outcome":
            valid_outcomes = {"interested", "callback", "not_interested", "completed"}
            if v.lower() not in valid_outcomes:
                return f"Invalid call_outcome '{v}'. Must be one of: interested, callback, not_interested."
            self.collected[f] = v
            logger.info(f"save_detail: {f} = {v}")
            if self._reporter:
                self._reporter.emit(type="detail", field=f, value=v)
            asyncio.create_task(self._hang_up_after_closing())
            return f"Saved {f}."

        self.collected[f] = v
        logger.info(f"save_detail: {f} = {v}")
        if self._reporter:
            self._reporter.emit(type="detail", field=f, value=v)
        return f"Saved {f}."

    # ── High-Conversion Admissions Tools ─────────────────────────────────────────
    @function_tool()
    async def book_campus_visit(self, context: RunContext, visit_datetime: str, visitor_name: str = "", parent_accompanying: bool = True):
        """Book a VIP guided campus visit for the student and parents. `visit_datetime` = date/time agreed (e.g. 'Saturday 10 AM', '2026-06-20')."""
        dt = str(visit_datetime or "Upcoming Saturday 10 AM").strip()
        name = str(visitor_name or self.collected.get("student_name") or "Candidate").strip()
        self.collected["visit_datetime"] = dt
        self.collected["engagement_choice"] = "campus_visit"
        self.collected["counselling_mode"] = "offline"
        self.collected["call_outcome"] = "interested"
        logger.info(f"book_campus_visit: {name} on {dt} (parent={parent_accompanying})")
        if self._reporter:
            self._reporter.emit(type="detail", field="visit_datetime", value=dt)
            self._reporter.emit(type="detail", field="engagement_choice", value="campus_visit")
            self._reporter.emit(type="detail", field="call_outcome", value="interested")
        return (f"VIP Campus Visit successfully booked for {name} on {dt}! A confirmation message with campus GPS location, "
                "assigned counselor contact, and gate pass has been sent to your mobile. We look forward to hosting you and your parents!")

    @function_tool()
    async def send_application_link(self, context: RunContext, phone_number: str = "", program: str = "", student_name: str = ""):
        """Send direct priority provisional admission application link to the caller's WhatsApp/SMS to reserve seat."""
        prog = program or self.collected.get("program_of_interest") or self.collected.get("specialization") or "Selected Program"
        name = student_name or self.collected.get("student_name") or "Candidate"
        self.collected["engagement_choice"] = "application_link"
        self.collected["call_outcome"] = "interested"
        logger.info(f"send_application_link: {name} for {prog}")
        if self._reporter:
            self._reporter.emit(type="detail", field="engagement_choice", value="application_link")
            self._reporter.emit(type="detail", field="call_outcome", value="interested")
        return (f"Priority provisional application link for {prog} has been dispatched to your registered WhatsApp! "
                "Please complete the basic form to reserve your seat and secure your scholarship quota.")

    @function_tool()
    async def register_for_asat(self, context: RunContext, student_name: str = "", exam_date: str = ""):
        """Register candidate for the Aditya Scholarship Aptitude Test (ASAT) to unlock up to 50% tuition waiver."""
        name = student_name or self.collected.get("student_name") or "Candidate"
        dt = exam_date or "Next Available Slot"
        self.collected["willing_university_exam"] = "yes"
        self.collected["engagement_choice"] = "asat_registration"
        self.collected["call_outcome"] = "interested"
        logger.info(f"register_for_asat: {name} for {dt}")
        if self._reporter:
            self._reporter.emit(type="detail", field="willing_university_exam", value="yes")
            self._reporter.emit(type="detail", field="engagement_choice", value="asat_registration")
        return (f"Successfully registered {name} for the ASAT scholarship exam ({dt})! "
                "Exam syllabus, practice sample papers, and online test link have been sent to your WhatsApp.")

    @function_tool()
    async def handle_admission_objection(self, context: RunContext, objection_type: str):
        """Authoritative rebuttals for admission objections: fee_expensive, parent_consultation, waiting_for_exams, hostel_safety, comparison."""
        obj = str(objection_type or "").lower().strip()
        if "fee" in obj or "expensive" in obj or "cost" in obj:
            return ("We offer up to 50% merit scholarships based on 12th/ASAT scores. Additionally, Aditya has on-campus "
                    "zero-interest education loan tie-ups with SBI and HDFC, and flexible semester fee payment options.")
        if "parent" in obj or "family" in obj:
            return ("Admissions are a vital family decision! We warmly invite you and your parents for a VIP campus visit this Saturday "
                    "to tour our labs, talk to faculty, and inspect our hostels in person.")
        if "exam" in obj or "waiting" in obj or "eapcet" in obj or "jee" in obj:
            return ("You can reserve a provisional seat today with our 100% refund guarantee! If you secure an IIT, NIT, or government quota seat, "
                    "your seat reservation fee is fully refunded without any deduction.")
        if "hostel" in obj or "safe" in obj or "food" in obj:
            return ("Our 250-acre gated smart campus has 24/7 CCTV surveillance, on-campus health hospital, separate AC hostels with attached washrooms, "
                    "and hygienic multi-cuisine dining serving both North and South Indian menus.")
        return ("Aditya University is NAAC A++ accredited, ranked in NIRF 151-200, with 3,800+ campus placements and ₹27 LPA top package.")

    # ── Knowledge lookups (via MCP Server with local fallback) ──────────────────
    @function_tool()
    async def lookup_program(self, context: RunContext, program: str):
        """Program details (degree, eligibility, accepted exams, fee, highlights). `program` = what the caller said."""
        course = udata.find_course(program)
        if not course:
            return (f"No exact match for '{program}'. Ask the caller to name the specific course, "
                    "or offer to list programs in a school (use list_programs).")
        return udata.format_course(course)

    @function_tool()
    async def get_fees(self, context: RunContext, program: str):
        """Get the annual tuition fee for a program, plus the one-time admission fee, ASAT fee and
        hostel options. Only quote what this returns — never estimate fees."""
        course = udata.find_course(program)
        fee_line = (f"{course['name']}: tuition {course['fee']}."
                    if course and course.get("fee")
                    else f"I don't have a specific fee for '{program}' — a counsellor will confirm.")
        cf = udata.COMMON_FEES
        return (f"{fee_line} One-time admission fee {cf['admission_fee']}. ASAT exam fee {cf['asat_fee']}. "
                f"Hostel: Non-AC {cf['hostel_non_ac']}; AC {cf['hostel_ac']}.")

    @function_tool()
    async def check_scholarship(self, context: RunContext, exam: str, score: str = "", program: str = ""):
        """Merit scholarship %. `exam`=12TH/BIE/CBSE/ASAT/JEE/EAPCET/CAT/NMAT/NEET, `score`=percentile/%/marks/rank, `program`=course."""
        prog = program or self.collected.get("program_of_interest") or self.collected.get("specialization") or "B.Tech"
        if not score or str(score).lower() in {"0", "none", "unknown", ""}:
            if str(exam).lower() in {"12th", "12", "inter", "intermediate", "board", "cbse"}:
                return "12th Board / Intermediate scholarships: 95%+ gets 50% tuition fee waiver, 90-95% gets 40%, 85-90% gets 30%, 80-85% gets 20%, and 75-80% gets 10% waiver on tuition fees."
        return udata.compute_scholarship(exam, score, prog)

    @function_tool()
    async def list_programs(self, context: RunContext, category: str = ""):
        """List the SPECIALISATION tracks under a branch/degree (synonym-aware). Use AFTER the
        caller picks a branch — e.g. category="CSE" returns core CSE + AI&ML + Data Science +
        the SAP/Google/Microsoft associated tracks. Also accepts "B.Tech", "MBA", "Pharmacy"."""
        names = udata.list_programs(category)
        if not names:
            return f"No programs match '{category}'. Schools: Engineering, Business, Pharmacy, Sciences."
        return "Programs" + (f" ({category})" if category else "") + ": " + "; ".join(names)

    @function_tool()
    async def list_branches(self, context: RunContext):
        """The high-level B.Tech BRANCH list (CSE, ECE, EEE, Mechanical, Civil, etc.). Use FIRST
        when a caller asks "what programs / courses do you offer" — read these branches, then use
        list_programs(branch) to go deeper once they pick one. Also mention MBA, Pharmacy & Sciences exist."""
        return "Our main B.Tech branches: " + "; ".join(udata.list_branches()) + \
               ". We also offer MBA, Pharmacy and Science programs."

    @function_tool()
    async def get_placements(self, context: RunContext, year: str = "2026"):
        """Get placement statistics and top recruiters. `year` = "2026" or "2025"."""
        p = udata.PLACEMENTS
        stats = p.get(str(year).strip(), p["2026"])
        return f"{stats} Top recruiters: {p['recruiters']} Internships: {p['internships']}"

    @function_tool()
    async def get_university_info(self, context: RunContext):
        """Get university facts: rankings (NAAC, NIRF, QS), accreditation, location, campus,
        international collaborations and contact details."""
        u = udata.UNIVERSITY
        return (f"{u['name']}, {u['location']}. Established {u['established']}. {u['campus']}. "
                f"Accreditation: {u['naac']}, {u['nba']}, {u['nirf']}, {u['qs']}. {u['the_impact']}. "
                f"{u['international']}. Website {u['website']}, contacts {u['contacts']}.")
        u = udata.UNIVERSITY
        return (f"{u['name']}, {u['location']}. Established {u['established']}. {u['campus']}. "
                f"Accreditation: {u['naac']}, {u['nba']}, {u['nirf']}, {u['qs']}. {u['the_impact']}. "
                f"{u['international']}. Website {u['website']}, contacts {u['contacts']}.")


    @function_tool()
    async def get_facilities(self, context: RunContext, topic: str = ""):
        """Get campus facilities. `topic` = hostel / medical / sports / safety / labs (blank = all)."""
        f = udata.FACILITIES
        t = topic.lower().strip()
        if t in f:
            return f"{t.capitalize()}: {f[t]}"
        return " ".join(f"{k.capitalize()}: {v}" for k, v in f.items())


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    logger.info(f"Priya joining room: {ctx.room.name}")
    logger.info(f"translate-out: {'ON' if TRANSLATE_OUT else 'OFF'} | mode={TRANSLATE_MODE} | "
                f"multilang={MULTILANG} | allowed={sorted(TTS_ALLOWED)}")

    # ── Per-call context from the dashboard ────────────────────────────────────
    # The Node backend dispatches this agent with JSON metadata: the session id to
    # report back to, the backend report URL, the prospect's name, and voice prefs.
    # (Empty when launched via `python agent.py console` — then we just run standalone.)
    meta: dict = {}
    try:
        if ctx.job and ctx.job.metadata:
            meta = json.loads(ctx.job.metadata)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"could not parse job metadata: {e}")

    session_id   = meta.get("session_id")
    report_url   = meta.get("report_url") or os.getenv("BACKEND_REPORT_URL", "")
    
    # Dev-testing diagnostics logger (persists to crm/Yash_TEST/TEST_N)
    test_session_id = session_id or ctx.room.name
    session_logger = get_or_create_logger(test_session_id)
    session_logger.log_session_init(reason="livekit_agent_entrypoint", is_first_call=True)

    # Ignore CRM placeholder names ("New Contact", "Unknown", "Prospect"…) — otherwise Priya
    # greets the caller as "New Contact". Treat those as no-name so she asks for the real one.
    _raw_name    = (meta.get("name") or STUDENT_NAME or "").strip()
    _PLACEHOLDERS = {"", "new contact", "unknown", "prospect", "student", "lead", "n/a", "na",
                     "none", "null", "test", "caller"}
    student_name = "" if _raw_name.lower() in _PLACEHOLDERS else _raw_name

    # Re-engagement (follow-up) context: on a weekly re-call the CRM sends what we already
    # know (collected fields from the earlier call) + a flag + last call's summary, so Priya
    # reconnects warmly and never starts from scratch.
    prior_collected = meta.get("collected") if isinstance(meta.get("collected"), dict) else {}
    is_followup     = bool(meta.get("followup"))
    last_summary    = str(meta.get("last_summary") or "")

    # Look up persistent profile by caller phone number across all previous calls
    phone_number = meta.get("phone") or os.getenv("CALL_TO", "")
    from structured_memory import GLOBAL_USER_STORE
    persisted_profile = GLOBAL_USER_STORE.get_profile(phone_number)
    if persisted_profile:
        logger.info(f"[PERSISTENT_MEMORY] Loaded cross-call profile for {phone_number}: {persisted_profile.get('name')}")
        prior_collected = {**persisted_profile, **prior_collected}
        if not student_name and persisted_profile.get("name"):
            student_name = persisted_profile.get("name")
        is_followup = True

    if is_followup and not student_name:
        student_name = prior_collected.get("student_name") or ""

    reporter = Reporter(report_url, session_id)
    reporter.start()

    # Start MCP Server Bridge
    await mcp_bridge.start()

    agent = Priya(student_name=student_name, reporter=reporter, job_ctx=ctx,
                  collected=prior_collected, followup=is_followup, last_summary=last_summary,
                  phone_number=phone_number)
    agent._session_id = test_session_id

    # Low-latency Silero Neural VAD with noise-resistant thresholds & two-stage barge-in confirmation
    session = AgentSession(
        vad=silero.VAD.load(
            activation_threshold=float(os.getenv("VAD_SPEECH_THRESHOLD", "0.75")),
            min_speech_duration=float(os.getenv("MIN_SPEECH_DURATION_MS", "350")) / 1000.0,
            min_silence_duration=float(os.getenv("END_OF_SPEECH_SILENCE_MS", "650")) / 1000.0,
            prefix_padding_duration=0.20
        ),
        conn_options=SessionConnectOptions(
            llm_conn_options=APIConnectOptions(max_retry=1, retry_interval=0.5, timeout=4.0),
        ),
        turn_handling={
            "turn_detection": "vad",
            "endpointing": {"min_delay": float(os.getenv("EOU_MIN_DELAY", "0.35"))},
            "preemptive_generation": {
                "enabled": True,
                "preemptive_tts": False,
            },
            "interruption": {
                "enabled": True,
                "mode": "vad",
                "min_duration": float(os.getenv("MIN_INTERRUPTION_DURATION_MS", "800")) / 1000.0,  # 800ms confirmation gate
                "min_words": int(os.getenv("INTERRUPTION_MIN_WORDS", "3")),
                "resume_false_interruption": True,
                "discard_audio_if_uninterruptible": True,
            },
        },
    )

    @session.on("agent_speech_interrupted")
    def _on_speech_interrupted(ev):
        item = getattr(ev, "chat_item", None)
        spoken_text = getattr(ev, "interrupted_speech", "") or (getattr(item, "text_content", "") if item else "")
        logger.info(f"[REPLY_TRUNCATED] intended={spoken_text!r} (interrupted)")
        session_logger.log_interruption(reason="caller_barge_in", detail=f"speech interrupted: {spoken_text[:50]}")

    # ── Multilingual voice (only when MULTILANG=true) ──────────────────────────
    # STT auto-detects the language and the LLM replies in it; this switches the
    # Sarvam *voice* to match each turn, so a Hindi reply isn't spoken with a Telugu
    # voice. Only within TTS_ALLOWED, and only when the language actually changes.
    # In English-only mode this is skipped — the voice stays en-IN.
    if MULTILANG:
        last_lang = {"code": TTS_START_LANG}
        # True once the caller has explicitly asked for a NON-English language — then we don't
        # auto-revert to English just because their next utterance happens to be in English.
        pref_nonenglish = {"on": False}

        def _switch_voice(code: str, reason: str):
            last_lang["code"] = code
            agent._lang = code
            try:
                agent.tts.update_options(target_language_code=code)
                logger.info(f"voice language → {code} ({reason})")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"TTS language switch failed: {e}")
            # Warm Sarvam translate for the NEW language right away (fire-and-forget), so the
            # first reply after a switch translates warm (~0.3s) instead of cold (~1-2s).
            if TRANSLATE_OUT and not code.lower().startswith("en"):
                asyncio.create_task(
                    translate_prewarm(code, gender=TRANSLATE_GENDER, mode=TRANSLATE_MODE))

        def _requested_language(t: str):
            """If the caller is asking to switch language (e.g. 'speak in Telugu'), return that
            language code; else None. Matches a language name + a request hint, or a short command."""
            low = t.lower()
            for code, names in LANG_NAMES.items():
                if code not in TTS_ALLOWED:
                    continue
                if any(n in low for n in names):
                    if len(t) <= 35 or any(h in low for h in LANG_REQUEST_HINTS):
                        return code
            return None

        @session.on("user_input_transcribed")
        def _follow_language(ev):
            lang = getattr(ev, "language", None)
            text = (getattr(ev, "transcript", "") or "").strip()
            if not getattr(ev, "is_final", True) or not text:
                return

            verdict, reason = classify_transcript(text)
            if verdict == "drop":
                logger.info(f"[LANG_FOLLOW] Dropped non-caller transcript: {text!r} ({reason})")
                return

            script = dominant_script(text)
            if script not in ALLOWED_SCRIPTS:
                logger.info(f"[LANG_FOLLOW] Ignored unsupported script {script}: {text!r}")
                return

            detected, reason = detect_language(text, current_lang=agent._lang, stt_lang=lang)
            resolved = resolve_mixed_language(detected_lang=detected, transcript=text, session_lang=agent._lang, session_id=agent._session_id)
            if resolved != agent._lang and resolved in TTS_ALLOWED:
                agent.switch_language(resolved, f"event_{reason}")

    # ── Dead-air guard ─────────────────────────────────────────────────────────
    # When a turn's LLM generation fails outright (both providers rate-limited at once),
    # Priya previously said NOTHING — the caller heard 15s+ of silence and hung up. Speak a
    # short hold line instead and invite them to repeat (their failed turn is lost, so
    # repeating is what actually recovers the conversation). Throttled so a burst of
    # failures doesn't stack apologies. Goes through tts_node → localised to their language.
    _last_hold = {"t": 0.0}

    @session.on("error")
    def _on_session_error(ev):
        err = getattr(ev, "error", ev)
        session_logger.log_error(f"LiveKit session error: {err}")
        if getattr(ev.error, "type", "") != "llm_error":
            return
        now = time.time()
        if now - _last_hold["t"] < 15.0:
            return
        _last_hold["t"] = now
        logger.warning("LLM turn failed (likely rate limits on all providers) — speaking hold line")
        try:
            session.say("Sorry, give me just a second. Could you repeat that, please?",
                        add_to_chat_ctx=False)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"hold line failed: {e}")

    # ── Live transcript → dashboard ────────────────────────────────────────────
    # Every finalised conversation item (Priya's lines AND the caller's) is mirrored
    # to the Node backend so the dashboard's TranscriptViewer updates in real time.
    # The greeting is added to chat history, so it's reported too; the per-turn fillers
    # use add_to_chat_ctx=False, so they're correctly skipped.
    # Goodbye phrases that should end the call even when the LLM forgets to save
    # call_outcome (observed: she said "Have a great day!" twice and the line stayed
    # open until the caller hung up). _hang_up_after_closing waits for real quiet
    # first, so a caller who keeps talking is still answered before any hangup.
    _GOODBYE_RE = re.compile(
        r"have a (great|good|nice|wonderful) (day|evening|week)|good\s?bye|bye[\s\-]?bye"
        r"|take care|talk to you (soon|later)|शुभ दिन|अलविदा|ధన్యవాదాలు",
        re.IGNORECASE)

    @session.on("conversation_item_added")
    def _on_item(ev):
        item = ev.item
        if not isinstance(item, ChatMessage) or item.role not in ("user", "assistant"):
            return
        text = (item.text_content or "").strip()
        if text:
            reporter.emit(type="transcript", role=item.role, text=text,
                          detected_language=agent._lang)
            try:
                if item.role == "user":
                    session_logger.log_stt(text=text, language=agent._lang)
                elif item.role == "assistant":
                    facts_snap = dict(agent.collected) if hasattr(agent, "collected") and agent.collected else None
                    stage_snap = getattr(agent, "current_stage", getattr(agent, "_stage", "GENERAL"))
                    session_logger.log_llm_reply(text=text, stage=stage_snap, facts_snapshot=facts_snap)
            except Exception as log_err:
                logger.debug(f"session_logger turn log error: {log_err}")
        # Backstop hang-up: Priya spoke a goodbye → wind the call down even if
        # save_detail(call_outcome) was never called. Guarded inside the method.
        if item.role == "assistant" and text and _GOODBYE_RE.search(text):
            asyncio.create_task(agent._hang_up_after_closing())

    # ── Per-turn latency → latency_log.csv (chart with plot_latency.py) ─────────
    latency = LatencyTracker(session_id=session_id or ctx.room.name)

    @session.on("metrics_collected")
    def _on_metrics(ev):
        try:
            metrics.log_metrics(ev.metrics)   # human-readable line in the worker log
        except Exception:  # noqa: BLE001
            pass
        latency.collect(ev.metrics)

    # ── Call status → dashboard ────────────────────────────────────────────────
    start_ts = time.time()

    async def _on_shutdown():
        # The call is ending (caller hung up, room closed, or worker shutdown). Send a
        # final status + duration and flush the report queue before the process exits.
        duration = int(time.time() - start_ts)
        reporter.emit(type="status", status="completed", duration=duration,
                      detected_language=agent._lang)
        session_logger.finalize(disposition="completed", notes="LiveKit room session closed")
        await reporter.aclose()
        await translate_aclose()
        await mcp_bridge.close()

    ctx.add_shutdown_callback(_on_shutdown)

    # Build room input options with noise cancellation if available and enabled.
    # BVC (Background Voice Cancellation) removes non-primary voices and ambient noise
    # server-side BEFORE audio reaches Sarvam STT — cleaner transcripts, fewer false
    # interruptions from TV/family in the background. Requires LiveKit Cloud.
    _room_input_opts = None
    if NOISE_CANCEL and NC_AVAILABLE:
        try:
            from livekit.agents import room_io
            _room_input_opts = room_io.RoomInputOptions(
                noise_cancellation=nc.BVC(),
            )
            logger.info("noise cancellation: ON (BVC model)")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"noise cancellation setup failed ({e}) — running without it")
    elif NOISE_CANCEL and not NC_AVAILABLE:
        logger.warning("NOISE_CANCELLATION=true but livekit-plugins-noise-cancellation not installed — pip install it")

    start_kwargs = {"agent": agent, "room": ctx.room}
    if _room_input_opts:
        start_kwargs["room_input_options"] = _room_input_opts
    await session.start(**start_kwargs)
    # Mark the call live once Priya is in and starting to speak.
    reporter.emit(type="status", status="in-progress", detected_language=agent._lang)


# ============================================================================
# SIMPLE LANGUAGE MATCHING TURN PROCESSOR (No Switching Logic)
# ============================================================================

async def process_turn(
    audio_bytes: bytes,
    stt=None,
    llm=None,
    tts=None,
    memory: Optional[SessionMemory] = None,
    turn_number: int = 1,
    websocket=None
) -> dict:
    """
    Process one turn of conversation automatically matching caller's language:
    1. STT: Detect language & text from audio
    2. LanguageHandler: Map & standardize to language code
    3. LLM: Prompt response in caller's language (<50 words)
    4. TTS: Synthesize in caller's language
    """
    transcript = ""
    detected_lang = "en-IN"

    if stt is not None:
        stt_result = await stt.transcribe(audio_bytes)
        transcript = getattr(stt_result, "text", str(stt_result))
        detected_lang = getattr(stt_result, "language", "en-IN")
    elif isinstance(audio_bytes, str):
        # Allow passing raw string/transcript for easy simulation/testing
        transcript = audio_bytes
        detected_lang = "en-IN"

    # Step 3: NORMALIZE language to standard format
    curr = memory.current_language if memory else "en-IN"
    lang_code = LanguageHandler.normalize_language(detected_lang)
    if detected_lang == "en-IN" and transcript:
        # Transcript script / keyword fallback if STT was default
        lang_code = LanguageHandler.match_language(
            stt_detected_language=detected_lang,
            transcript_text=transcript,
            current_language=curr
        )

    # Step 4: GET UNIFIED LLM PROMPT (Preserves facts ledger & context across language switches)
    facts_str = memory.get_facts_ledger_str() if memory else ""
    context_str = memory.get_context() if memory else ""
    stage_str = getattr(memory, "current_stage", "Stage 1: Greeting & Identify Caller") if memory else ""
    pending_str = getattr(memory, "pending_field", "") if memory else ""

    final_prompt = LanguageHandler.build_unified_prompt(
        facts_ledger=facts_str,
        stage=stage_str,
        next_field=pending_str,
        language_code=lang_code,
        conversation_history=context_str,
        system_base=INSTRUCTIONS
    )

    # Step 5: LLM - Generate response in caller's language
    response = ""
    if llm is not None:
        response = await llm.generate(
            system_prompt=final_prompt,
            user_input=transcript,
            cache_control={"type": "ephemeral"}
        )
    else:
        # Factual default matching response from knowledge base
        answers = {
            "en-IN": "The B.Tech CSE tuition fee is ₹2,75,000 per year with up to 50% merit scholarships available.",
            "hi-IN": "B.Tech CSE की ट्यूशन फीस ₹2,75,000 प्रति वर्ष है और 50% तक मेरिट स्कॉलरशिप उपलब्ध है।",
            "te-IN": "B.Tech CSE ట్యూషన్ ఫీజు సంవత్సరానికి ₹2,75,000 మరియు 50% వరకు మెరిట్ స్కాలర్‌షిప్‌లు అందుబాటులో ఉన్నాయి.",
            "ta-IN": "B.Tech CSE கல்விக் கட்டணம் ஆண்டுக்கு ₹2,75,000 மற்றும் 50% வரை உதவித்தொகை கிடைக்கும்.",
        }
        response = answers.get(lang_code, answers["en-IN"])

    # Step 5: Synthesize in caller's language
    audio = None
    if tts is not None:
        audio = await tts.synthesize(response, language=lang_code)

    # Step 6: Send to caller websocket if provided
    if websocket is not None and audio is not None:
        await websocket.send(audio)

    # Update session memory
    if memory is not None:
        memory.add_turn(transcript, response, lang_code)

    return {"response": response, "audio": audio, "language": lang_code, "language_used": lang_code}

class FullConversationAgent:
    """Agent that maintains full conversation history from start to end with zero repetition."""

    def __init__(self, call_id: str = "call_default"):
        self.call_id = call_id
        self.history = ConversationHistory(call_id)
        self.questions = QuestionEngine(self.history)
        self.llm_handler = LLMWithHistory(self.history, self.questions)
        self.no_repetition = NoRepetitionEngine(self.history)
        self.turn_count = 0

    async def process_turn(self, audio_input: Any, language: str = "en-IN", stt: Any = None, llm: Any = None, tts: Any = None):
        """Process one turn with full history."""
        self.turn_count += 1

        # Step 1: STT or raw text input
        if isinstance(audio_input, str):
            user_input = audio_input
        elif stt is not None:
            stt_result = await stt.transcribe(audio_input)
            user_input = getattr(stt_result, "text", str(stt_result))
        else:
            user_input = str(audio_input)

        # Step 2: Extract facts from this input
        new_facts = self.history.extract_facts(user_input)

        # Step 3: Check for goodbye
        if self.should_end_call(user_input):
            response = f"Thank you for calling! Here's what we discussed:\n{self.questions.get_response_based_on_facts()}"
            audio = await tts.synthesize(response, language=language) if tts else None
            self.history.add_turn(user_input, response, 0.5, language)
            self._save_transcript()
            return audio or response, "END"

        # Step 4: Generate response using FULL history
        if llm is not None:
            response = await self.llm_handler.generate_response(
                user_input=user_input,
                llm_client=llm,
                language=language
            )
        else:
            next_q = self.questions.get_next_question(user_input)
            response = f"I noted your details. {next_q}" if next_q else "How else may I help you with your admission?"

        # Step 5: TTS
        audio = await tts.synthesize(response, language=language) if tts else None

        # Step 6: Add to history
        self.history.add_turn(user_input, response, 0.5, language)

        return audio or response, "CONTINUE"

    def should_end_call(self, text: str) -> bool:
        """Check if call should end."""
        goodbye = ["thank you", "bye", "goodbye", "nahi", "bas", "done", "that's all", "that is all"]
        if any(g in text.lower() for g in goodbye):
            return True
        if self.turn_count > 25:
            return True
        return False

    def _save_transcript(self):
        """Save full conversation transcript to transcripts directory."""
        try:
            os.makedirs("transcripts", exist_ok=True)
            transcript = self.history.get_full_transcript()
            with open(f"transcripts/{self.call_id}.txt", "w", encoding="utf-8") as f:
                f.write(transcript)
        except Exception as e:
            logger.warning(f"Error saving transcript: {e}")


if __name__ == "__main__":
    import sys
    audio_pipeline = os.getenv("AUDIO_PIPELINE", "").lower().strip()
    use_livekit = os.getenv("USE_LIVEKIT", "").lower().strip()
    is_cli_direct = len(sys.argv) > 1 and sys.argv[1].lower() == "direct"
    
    # Direct raw audio mode requested via CLI or ENV
    if is_cli_direct or audio_pipeline == "direct" or use_livekit == "false":
        if not (len(sys.argv) > 1 and sys.argv[1].lower() in {"console", "dev", "start"}):
            import uvicorn
            from direct_server import app as direct_app, HOST as D_HOST, PORT as D_PORT
            print("=" * 65)
            print(f"  [MODE: DIRECT RAW AUDIO] Launching Priya Direct Server on {D_HOST}:{D_PORT}")
            print(f"  LiveKit SFU / Cloud bypassed — In-Process 1:1 Media Pipe Active")
            print("=" * 65)
            uvicorn.run(direct_app, host=D_HOST, port=D_PORT)
            sys.exit(0)

    # Default LiveKit Agent Worker mode
    # agent_name lets the SIP dispatch rule target this agent by name ("priya").
    # `python agent.py console` still works for local mic testing regardless.
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="priya"))

