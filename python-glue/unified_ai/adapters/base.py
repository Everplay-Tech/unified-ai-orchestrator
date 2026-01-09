"""Base adapter interface for AI tools"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional
from enum import Enum


class ToolCapability(Enum):
    """Capabilities that a tool may support"""
    CHAT = "chat"
    STREAMING = "streaming"
    CODE_CONTEXT = "code_context"
    WEB_SEARCH = "web_search"
    IMAGE_GENERATION = "image_generation"
    FUNCTION_CALLING = "function_calling"


@dataclass
class ToolCapabilities:
    """Describes what a tool can do"""
    supported_capabilities: List[ToolCapability]
    max_context_length: int
    supports_streaming: bool = False
    supports_code_context: bool = False


@dataclass
class Message:
    """A message in a conversation"""
    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class Response:
    """Response from an AI tool"""
    content: str
    tool: str
    metadata: Optional[dict] = None


@dataclass
class Context:
    """Context for a conversation"""
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    codebase_context: Optional[dict] = None


class ToolAdapter(ABC):
    """Base interface for all AI tool adapters"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ToolCapabilities:
        """What this tool can do"""
        pass

    @abstractmethod
    async def chat(
        self, messages: List[Message], context: Optional[Context] = None
    ) -> Response:
        """
        Send a chat request to the tool
        
        Args:
            messages: List of messages in the conversation
            context: Optional context (project, codebase, etc.)
            
        Returns:
            Response from the tool
        """
        pass

    @abstractmethod
    async def stream_chat(
        self, messages: List[Message], context: Optional[Context] = None
    ) -> AsyncIterator[str]:
        """
        Stream a chat response from the tool
        
        Args:
            messages: List of messages in the conversation
            context: Optional context
            
        Yields:
            Chunks of the response as they arrive
        """
        pass

    async def is_available(self) -> bool:
        """Check if the tool is available (API key configured, etc.)"""
        return True
