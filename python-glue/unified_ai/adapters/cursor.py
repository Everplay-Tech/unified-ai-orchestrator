"""Cursor IDE adapter"""

import httpx
from typing import AsyncIterator, List, Optional
from .base import ToolAdapter, ToolCapabilities, ToolCapability, Message, Response, Context


class CursorAdapter(ToolAdapter):
    """Adapter for Cursor IDE integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://api.cursor.sh"  # Placeholder URL
        self._client: Optional[httpx.AsyncClient] = None
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or keyring"""
        import os
        from ..utils.auth import get_secret
        
        return os.getenv("CURSOR_API_KEY") or get_secret("cursor_api_key")
    
    @property
    def name(self) -> str:
        return "cursor"
    
    @property
    def capabilities(self) -> ToolCapabilities:
        return ToolCapabilities(
            supports_streaming=True,
            supports_code_context=True,
            supported_capabilities=[
                ToolCapability.CODE_EDITING,
                ToolCapability.FILE_OPERATIONS,
                ToolCapability.PROJECT_CONTEXT,
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
                timeout=60.0,
            )
        return self._client
    
    async def is_available(self) -> bool:
        """Check if Cursor API is available"""
        if not self.api_key:
            return False
        
        try:
            client = await self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def chat(
        self,
        messages: List[Message],
        context: Optional[Context] = None,
    ) -> Response:
        """Chat with Cursor IDE"""
        client = await self._get_client()
        
        # Prepare request
        payload = {
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
        }
        
        if context and context.codebase_context:
            payload["codebase_context"] = {
                "relevant_files": context.codebase_context.get("relevant_files", []),
                "semantic_matches": context.codebase_context.get("semantic_matches", []),
            }
        
        response = await client.post("/v1/chat", json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        return Response(
            content=data.get("content", ""),
            tool=self.name,
            metadata={
                "model": data.get("model", "cursor"),
                "usage": data.get("usage", {}),
            },
        )
    
    async def stream_chat(
        self,
        messages: List[Message],
        context: Optional[Context] = None,
    ) -> AsyncIterator[str]:
        """Stream chat response from Cursor"""
        client = await self._get_client()
        
        payload = {
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            "stream": True,
        }
        
        if context and context.codebase_context:
            payload["codebase_context"] = context.codebase_context
        
        async with client.stream("POST", "/v1/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "content" in data:
                        yield data["content"]
    
    async def edit_code(
        self,
        file_path: str,
        instructions: str,
        code_context: Optional[str] = None,
    ) -> str:
        """Edit code using Cursor"""
        client = await self._get_client()
        
        payload = {
            "file_path": file_path,
            "instructions": instructions,
        }
        
        if code_context:
            payload["code_context"] = code_context
        
        response = await client.post("/v1/edit", json=payload)
        response.raise_for_status()
        
        data = response.json()
        return data.get("edited_code", "")
