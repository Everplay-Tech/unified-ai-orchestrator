"""Claude (Anthropic) adapter"""

import os
from typing import AsyncIterator, List, Optional

from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import MessageParam

from .base import ToolAdapter, ToolCapabilities, ToolCapability, Message, Response, Context


class ClaudeAdapter(ToolAdapter):
    """Adapter for Anthropic's Claude API"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None
        self._async_client = None

    @property
    def name(self) -> str:
        return "claude"

    @property
    def capabilities(self) -> ToolCapabilities:
        return ToolCapabilities(
            supported_capabilities=[
                ToolCapability.CHAT,
                ToolCapability.STREAMING,
                ToolCapability.CODE_CONTEXT,
            ],
            max_context_length=200000,
            supports_streaming=True,
            supports_code_context=True,
        )

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def _get_async_client(self):
        if self._async_client is None:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self._async_client = AsyncAnthropic(api_key=self.api_key)
        return self._async_client

    async def is_available(self) -> bool:
        return self.api_key is not None

    def _prepare_messages(self, messages: List[Message]) -> List[MessageParam]:
        """Convert our Message format to Anthropic's format"""
        result = []
        for msg in messages:
            result.append({
                "role": msg.role,
                "content": msg.content,
            })
        return result

    async def chat(
        self, messages: List[Message], context: Optional[Context] = None
    ) -> Response:
        client = self._get_async_client()
        
        # Prepare messages
        anthropic_messages = self._prepare_messages(messages)
        
        # Add system message if we have codebase context
        system_message = None
        if context and context.codebase_context:
            system_message = self._build_system_message(context)
        
        # Make API call
        response = await client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=anthropic_messages,
            system=system_message,
        )

        # Extract content
        content = ""
        if response.content:
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

        return Response(
            content=content,
            tool=self.name,
            metadata={
                "model": self.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                } if hasattr(response, "usage") else None,
            },
        )

    async def stream_chat(
        self, messages: List[Message], context: Optional[Context] = None
    ) -> AsyncIterator[str]:
        client = self._get_async_client()
        
        anthropic_messages = self._prepare_messages(messages)
        system_message = None
        if context and context.codebase_context:
            system_message = self._build_system_message(context)

        async with client.messages.stream(
            model=self.model,
            max_tokens=4096,
            messages=anthropic_messages,
            system=system_message,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield event.delta.text

    def _build_system_message(self, context: Context) -> str:
        """Build system message with codebase context"""
        parts = []
        if context.codebase_context:
            if "relevant_files" in context.codebase_context:
                parts.append("Relevant files:")
                for file in context.codebase_context["relevant_files"]:
                    parts.append(f"- {file}")
        return "\n".join(parts) if parts else None
