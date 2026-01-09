"""Perplexity AI adapter with web search"""

import os
from typing import AsyncIterator, List, Optional
import httpx

from .base import ToolAdapter, ToolCapabilities, ToolCapability, Message, Response, Context


class PerplexityAdapter(ToolAdapter):
    """Adapter for Perplexity AI API with web search"""

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-sonar-large-128k-online"):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.model = model
        self.base_url = "https://api.perplexity.ai"
        self._client = None

    @property
    def name(self) -> str:
        return "perplexity"

    @property
    def capabilities(self) -> ToolCapabilities:
        return ToolCapabilities(
            supported_capabilities=[
                ToolCapability.CHAT,
                ToolCapability.STREAMING,
                ToolCapability.WEB_SEARCH,
            ],
            max_context_length=128000,
            supports_streaming=True,
            supports_code_context=False,
        )

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            if not self.api_key:
                raise ValueError("PERPLEXITY_API_KEY not set")
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def is_available(self) -> bool:
        return self.api_key is not None

    def _prepare_messages(self, messages: List[Message]) -> List[dict]:
        """Convert our Message format to Perplexity's format"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def chat(
        self, messages: List[Message], context: Optional[Context] = None
    ) -> Response:
        client = self._get_client()
        
        perplexity_messages = self._prepare_messages(messages)
        
        try:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": perplexity_messages,
                    "temperature": 0.2,
                    "max_tokens": 4096,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            citations = data.get("citations", [])
            
            return Response(
                content=content,
                tool=self.name,
                metadata={
                    "model": self.model,
                    "citations": citations,
                    "usage": data.get("usage"),
                },
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"Perplexity API error: {e}") from e

    async def stream_chat(
        self, messages: List[Message], context: Optional[Context] = None
    ) -> AsyncIterator[str]:
        client = self._get_client()
        
        perplexity_messages = self._prepare_messages(messages)
        
        async with client.stream(
            "POST",
            "/chat/completions",
            json={
                "model": self.model,
                "messages": perplexity_messages,
                "temperature": 0.2,
                "max_tokens": 4096,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue
