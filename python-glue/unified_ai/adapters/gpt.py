"""GPT (OpenAI) adapter"""

import os
from typing import AsyncIterator, List, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from .base import ToolAdapter, ToolCapabilities, ToolCapability, Message, Response, Context


class GPTAdapter(ToolAdapter):
    """Adapter for OpenAI's GPT API"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._client = None

    @property
    def name(self) -> str:
        return "gpt"

    @property
    def capabilities(self) -> ToolCapabilities:
        return ToolCapabilities(
            supported_capabilities=[
                ToolCapability.CHAT,
                ToolCapability.STREAMING,
                ToolCapability.CODE_CONTEXT,
            ],
            max_context_length=128000,
            supports_streaming=True,
            supports_code_context=True,
        )

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def is_available(self) -> bool:
        return self.api_key is not None

    def _prepare_messages(self, messages: List[Message]) -> List[ChatCompletionMessageParam]:
        """Convert our Message format to OpenAI's format"""
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
        client = self._get_client()
        
        # Prepare messages
        openai_messages = self._prepare_messages(messages)
        
        # Add system message if we have codebase context
        if context and context.codebase_context:
            system_msg = self._build_system_message(context)
            openai_messages.insert(0, {
                "role": "system",
                "content": system_msg,
            })
        
        # Make API call
        response = await client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            max_tokens=4096,
        )

        content = response.choices[0].message.content or ""

        return Response(
            content=content,
            tool=self.name,
            metadata={
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
            },
        )

    async def stream_chat(
        self, messages: List[Message], context: Optional[Context] = None
    ) -> AsyncIterator[str]:
        client = self._get_client()
        
        openai_messages = self._prepare_messages(messages)
        if context and context.codebase_context:
            system_msg = self._build_system_message(context)
            openai_messages.insert(0, {
                "role": "system",
                "content": system_msg,
            })

        stream = await client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            max_tokens=4096,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _build_system_message(self, context: Context) -> str:
        """Build system message with codebase context"""
        parts = []
        if context.codebase_context:
            if "relevant_files" in context.codebase_context:
                parts.append("Relevant files:")
                for file in context.codebase_context["relevant_files"]:
                    parts.append(f"- {file}")
        return "\n".join(parts) if parts else ""
