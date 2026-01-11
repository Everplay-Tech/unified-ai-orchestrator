"""Local LLM adapter (Ollama, etc.)"""

import httpx
from typing import AsyncIterator, List, Optional
from .base import ToolAdapter, ToolCapabilities, ToolCapability, Message, Response, Context


class LocalLLMAdapter(ToolAdapter):
    """Adapter for local LLM servers (Ollama, etc.)"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def name(self) -> str:
        return "local"
    
    @property
    def capabilities(self) -> ToolCapabilities:
        return ToolCapabilities(
            supports_streaming=True,
            supports_code_context=False,
            supported_capabilities=[
                ToolCapability.GENERAL_CHAT,
            ],
        )
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=120.0,  # Longer timeout for local models
            )
        return self._client
    
    async def is_available(self) -> bool:
        """Check if local LLM server is available (pure check, no side effects)"""
        try:
            client = await self._get_client()
            # Try to list models (Ollama endpoint)
            response = await client.get("/api/tags", timeout=2.0)
            if response.status_code == 200:
                return True
            return False
        except Exception:
            return False
    
    async def auto_detect_model(self) -> bool:
        """Auto-detect and set model if current model is not available"""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                available_models = [m["name"] for m in data.get("models", [])]
                if available_models and self.model not in available_models:
                    # Use first available model
                    self.model = available_models[0]
                    return True
            return False
        except Exception:
            return False
    
    async def chat(
        self,
        messages: List[Message],
        context: Optional[Context] = None,
    ) -> Response:
        """Chat with local LLM"""
        client = await self._get_client()
        
        # Convert messages to Ollama format
        prompt = self._messages_to_prompt(messages)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        
        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        return Response(
            content=data.get("response", ""),
            tool=self.name,
            metadata={
                "model": self.model,
                "done": data.get("done", True),
            },
        )
    
    async def stream_chat(
        self,
        messages: List[Message],
        context: Optional[Context] = None,
    ) -> AsyncIterator[str]:
        """Stream chat response from local LLM"""
        client = await self._get_client()
        
        prompt = self._messages_to_prompt(messages)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }
        
        async with client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    import json
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                    except json.JSONDecodeError:
                        continue
    
    def _messages_to_prompt(self, messages: List[Message]) -> str:
        """Convert messages to a single prompt"""
        parts = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                parts.append(f"Assistant: {msg.content}")
        
        return "\n\n".join(parts) + "\n\nAssistant:"
    
    async def list_models(self) -> List[str]:
        """List available models"""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            # Log error but don't fail
            import logging
            logging.getLogger(__name__).warning(f"Failed to list models: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Perform health check on local LLM server"""
        try:
            client = await self._get_client()
            # Try ping endpoint if available, otherwise use tags
            try:
                response = await client.get("/api/version", timeout=2.0)
                return response.status_code == 200
            except Exception:
                # Fallback to tags endpoint
                response = await client.get("/api/tags", timeout=2.0)
                return response.status_code == 200
        except Exception:
            return False
