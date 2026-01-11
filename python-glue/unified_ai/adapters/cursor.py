"""Cursor IDE adapter"""

import json
import httpx
from typing import AsyncIterator, List, Optional
from .base import ToolAdapter, ToolCapabilities, ToolCapability, Message, Response, Context


class CursorAdapter(ToolAdapter):
    """Adapter for Cursor IDE integration"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        # Note: Cursor IDE does not currently have a public API
        # This adapter is prepared for future API availability
        # For now, it can be used with Cursor's local integration features
        # If you have access to Cursor's internal API, update this URL
        import os
        self.base_url = os.getenv("CURSOR_API_URL", "http://localhost:3000")  # Default to local Cursor instance
        self._client: Optional[httpx.AsyncClient] = None
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or keyring"""
        import os
        from ..utils.auth import get_secret
        
        # Cursor may use local authentication or API keys
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
        # Cursor doesn't have a public API yet, so availability depends on local setup
        # Check if Cursor is running locally or if API key is configured
        if self.api_key:
            return True
        
        # Try to connect to local Cursor instance
        try:
            client = await self._get_client()
            # Try a simple endpoint (may not exist)
            response = await client.get("/health", timeout=2.0)
            return response.status_code == 200
        except Exception as e:
            # If no API key and can't connect, assume unavailable
            import logging
            logging.getLogger(__name__).debug(f"Cursor adapter unavailable: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Perform health check on Cursor instance"""
        try:
            client = await self._get_client()
            # Try health endpoint
            response = await client.get("/health", timeout=2.0)
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
        
        try:
            response = await client.post("/v1/chat", json=payload, timeout=120.0)
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
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError("Cursor API endpoint not found. Cursor may not have a public API yet.")
            raise
        except httpx.TimeoutException:
            raise TimeoutError("Cursor API request timed out")
        except Exception as e:
            raise RuntimeError(f"Cursor API error: {str(e)}")
    
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
        
        try:
            async with client.stream("POST", "/v1/chat", json=payload, timeout=120.0) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "content" in data:
                                yield data["content"]
                        except json.JSONDecodeError:
                            # Skip invalid JSON lines
                            continue
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError("Cursor API endpoint not found. Cursor may not have a public API yet.")
            raise
        except httpx.TimeoutException:
            raise TimeoutError("Cursor API request timed out")
        except Exception as e:
            raise RuntimeError(f"Cursor API streaming error: {str(e)}")
    
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
        
        try:
            response = await client.post("/v1/edit", json=payload, timeout=120.0)
            response.raise_for_status()
            
            data = response.json()
            return data.get("edited_code", "")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError("Cursor edit endpoint not found. Cursor may not have a public API yet.")
            raise
        except httpx.TimeoutException:
            raise TimeoutError("Cursor edit request timed out")
        except Exception as e:
            raise RuntimeError(f"Cursor edit error: {str(e)}")
