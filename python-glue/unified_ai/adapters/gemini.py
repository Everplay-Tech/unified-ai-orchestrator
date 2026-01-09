"""Google Gemini adapter"""

import os
from typing import AsyncIterator, List, Optional

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

from .base import ToolAdapter, ToolCapabilities, ToolCapability, Message, Response, Context


class GeminiAdapter(ToolAdapter):
    """Adapter for Google Gemini API"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro"):
        if not HAS_GEMINI:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        if self.api_key:
            genai.configure(api_key=self.api_key)

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def capabilities(self) -> ToolCapabilities:
        return ToolCapabilities(
            supported_capabilities=[
                ToolCapability.CHAT,
                ToolCapability.STREAMING,
                ToolCapability.CODE_CONTEXT,
            ],
            max_context_length=32000,
            supports_streaming=True,
            supports_code_context=True,
        )

    async def is_available(self) -> bool:
        return self.api_key is not None and HAS_GEMINI

    async def chat(
        self, messages: List[Message], context: Optional[Context] = None
    ) -> Response:
        model = genai.GenerativeModel(self.model)
        
        # Convert messages to Gemini format
        # Gemini uses a different message format
        chat_messages = []
        for msg in messages:
            if msg.role == "user":
                chat_messages.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                chat_messages.append({"role": "model", "parts": [msg.content]})
        
        # Start chat with history
        chat = model.start_chat(history=chat_messages[:-1] if len(chat_messages) > 1 else [])
        
        # Send last message
        last_message = chat_messages[-1]["parts"][0] if chat_messages else ""
        response = await chat.send_message_async(last_message)
        
        return Response(
            content=response.text,
            tool=self.name,
            metadata={
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                } if hasattr(response, "usage_metadata") else None,
            },
        )

    async def stream_chat(
        self, messages: List[Message], context: Optional[Context] = None
    ) -> AsyncIterator[str]:
        model = genai.GenerativeModel(self.model)
        
        # Convert messages
        chat_messages = []
        for msg in messages:
            if msg.role == "user":
                chat_messages.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                chat_messages.append({"role": "model", "parts": [msg.content]})
        
        chat = model.start_chat(history=chat_messages[:-1] if len(chat_messages) > 1 else [])
        last_message = chat_messages[-1]["parts"][0] if chat_messages else ""
        
        async for chunk in await chat.send_message_async(last_message, stream=True):
            if chunk.text:
                yield chunk.text
