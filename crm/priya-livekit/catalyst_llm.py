import os
import json
import time
import httpx
import logging
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("catalyst_llm")
logger.setLevel(logging.INFO)

class CatalystAuthTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.endpoint_url = os.getenv("CATALYST_ENDPOINT_URL")
        self.endpoint_key = os.getenv("CATALYST_ENDPOINT_KEY")
        self.client_id = os.getenv("CATALYST_CLIENT_ID")
        self.client_secret = os.getenv("CATALYST_CLIENT_SECRET")
        self.refresh_token = os.getenv("CATALYST_REFRESH_TOKEN")
        self.accounts_domain = os.getenv("CATALYST_ACCOUNTS_DOMAIN", "https://accounts.zoho.in").rstrip('/')
        
        self.access_token = None
        self.token_expiry = 0
        self.inner_transport = httpx.AsyncHTTPTransport()
        self._refresh_lock = asyncio.Lock()

    async def get_valid_token(self):
        if time.time() > self.token_expiry - 60:
            async with self._refresh_lock:
                # Double-check inside lock
                if time.time() > self.token_expiry - 60:
                    logger.info("[CATALYST] Refreshing access token...")
                    token_url = f"{self.accounts_domain}/oauth/v2/token"
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(token_url, data={
                            "refresh_token": self.refresh_token,
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                            "grant_type": "refresh_token"
                        })
                        if resp.status_code != 200:
                            logger.error(f"[CATALYST] Auth failed: {resp.text}")
                            resp.raise_for_status()
                        
                        data = resp.json()
                        self.access_token = data.get("access_token")
                        self.token_expiry = time.time() + data.get("expires_in", 3600)
                        logger.info("[CATALYST] Access token refreshed successfully.")
        return self.access_token

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Intercept OpenAI chat completions request
        if "/chat/completions" in request.url.path:
            token = await self.get_valid_token()
            
            body = json.loads(request.content)
            is_streaming = body.get("stream", False)
            
            # Convert to Catalyst QuickML generate format with prompt length budgeting
            # (Catalyst QuickML has a hard 10,000 character limit on the prompt)
            messages = body.get("messages", [])
            system_msg = ""
            chat_turns = []
            
            for m in messages:
                role = m.get("role", "user").upper()
                content = m.get("content", "")
                if role == "SYSTEM":
                    system_msg += f"{content}\n\n"
                else:
                    chat_turns.append(f"{role}: {content}\n\n")

            # Budget: keep system prompt, and keep as many recent dialogue turns as possible
            # Keep total length <= 8500 chars to leave ample safety margin
            MAX_CATALYST_CHARS = 8500
            
            # Trim system message if it alone is huge
            if len(system_msg) > 6000:
                system_msg = system_msg[:6000] + "\n[System prompt truncated]\n\n"

            available_for_chat = MAX_CATALYST_CHARS - len(system_msg) - 20
            selected_turns = []
            current_len = 0
            
            # Take turns from newest to oldest
            for turn in reversed(chat_turns):
                if current_len + len(turn) <= available_for_chat:
                    selected_turns.insert(0, turn)
                    current_len += len(turn)
                else:
                    break

            prompt_text = ""
            if system_msg:
                prompt_text += f"SYSTEM:\n{system_msg}\n"
            prompt_text += "".join(selected_turns)
            prompt_text += "ASSISTANT: "

            catalyst_payload = {
                "prompt": prompt_text
            }
            
            org_id = os.getenv("CATALYST_ORG")
            headers = {
                "Authorization": f"Zoho-oauthtoken {token}",
                "Content-Type": "application/json",
                "CATALYST-ORG": org_id,
                "zaid": org_id,
                "X-QUICKML-ENDPOINT-KEY": self.endpoint_key
            }
            # X-QUICKML-ENDPOINT-KEY is already added above
            t0 = time.time()
            async with httpx.AsyncClient() as client:
                cat_resp = await client.post(
                    self.endpoint_url,
                    json=catalyst_payload,
                    headers=headers,
                    timeout=30.0
                )
            
            if cat_resp.status_code != 200:
                logger.error(f"[CATALYST] Request failed: {cat_resp.text}")
                cat_resp.raise_for_status()
                
            cat_data = cat_resp.json()
            logger.info(f"[CATALYST] Response generated in {time.time() - t0:.2f}s")
            
            # Extract content (QuickML might return choices or direct content)
            content = ""
            if isinstance(cat_data, dict):
                if "data" in cat_data and isinstance(cat_data["data"], list) and len(cat_data["data"]) > 0:
                    content = cat_data["data"][0].get("data", "")
                elif "choices" in cat_data and len(cat_data["choices"]) > 0:
                    msg = cat_data["choices"][0].get("message", {})
                    content = msg.get("content", "")
                elif "response" in cat_data:
                    content = cat_data["response"]
                elif "output" in cat_data:
                    content = cat_data["output"]
                elif "message" in cat_data:
                    content = cat_data["message"]
            elif isinstance(cat_data, str):
                content = cat_data
                
            if is_streaming:
                # Mock a streaming response for LiveKit
                async def stream_generator():
                    # Yield role chunk
                    role_chunk = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "glm-4.7-flash",
                        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
                    }
                    yield b"data: " + json.dumps(role_chunk).encode("utf-8") + b"\n\n"
                    
                    # Yield content chunks
                    # Split into small chunks to simulate streaming
                    chunk_size = 4
                    for i in range(0, len(content), chunk_size):
                        delta = content[i:i+chunk_size]
                        content_chunk = {
                            "id": f"chatcmpl-{int(time.time())}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "glm-4.7-flash",
                            "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}]
                        }
                        yield b"data: " + json.dumps(content_chunk).encode("utf-8") + b"\n\n"
                        await asyncio.sleep(0.01)
                        
                    # Yield finish chunk
                    finish_chunk = {
                        "id": f"chatcmpl-{int(time.time())}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "glm-4.7-flash",
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                    }
                    yield b"data: " + json.dumps(finish_chunk).encode("utf-8") + b"\n\n"
                    yield b"data: [DONE]\n\n"
                    
                class AsyncStreamWrapper(httpx.AsyncByteStream):
                    def __init__(self, gen):
                        self.gen = gen
                    async def __aiter__(self):
                        async for chunk in self.gen():
                            yield chunk
                    async def aclose(self):
                        pass

                return httpx.Response(
                    status_code=200,
                    headers={"Content-Type": "text/event-stream"},
                    stream=AsyncStreamWrapper(stream_generator),
                    request=request
                )
            else:
                # Standard response
                openai_resp = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "glm-4.7-flash",
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                }
                return httpx.Response(
                    status_code=200,
                    json=openai_resp,
                    request=request
                )
                
        # Fallback to standard transport for non-chat requests
        return await self.inner_transport.handle_async_request(request)

def get_catalyst_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key="dummy-catalyst-key",
        base_url="https://api.openai.com/v1",  # dummy, intercepted by transport
        http_client=httpx.AsyncClient(transport=CatalystAuthTransport())
    )


from typing import Optional, List, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class ChatCatalyst(BaseChatModel):
    model_name: str = "glm-4.7-flash"
    temperature: float = 0.4
    max_tokens: int = 100

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        msgs = []
        for m in messages:
            if isinstance(m, HumanMessage):
                role = "user"
            elif isinstance(m, SystemMessage) or getattr(m, "type", "") == "system":
                role = "system"
            else:
                role = "assistant"
            msgs.append({"role": role, "content": str(m.content)})
        return msgs

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(
                lambda: asyncio.run(self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs))
            ).result()

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        client = get_catalyst_client()
        msgs = self._convert_messages(messages)
        resp = await client.chat.completions.create(
            model=self.model_name,
            messages=msgs,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        content = resp.choices[0].message.content or ""
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    @property
    def _llm_type(self) -> str:
        return "catalyst"
