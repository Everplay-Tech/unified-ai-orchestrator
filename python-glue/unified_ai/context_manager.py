"""Context manager for maintaining conversation history"""

import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from .storage import create_storage_backend, DatabaseType, StorageBackend
from .config import load_config

try:
    from unified_ai_orchestrator.pyo3_bridge import PyContextWindowManager, PyContextCompressor
    HAS_PYO3 = True
except ImportError:
    HAS_PYO3 = False


@dataclass
class Message:
    """A message in a conversation"""
    role: str
    content: str
    timestamp: int


@dataclass
class Context:
    """Context for a conversation"""
    conversation_id: str
    project_id: Optional[str]
    messages: List[Message]
    codebase_context: Optional[Dict[str, Any]]
    tool_history: List[Dict[str, Any]]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "conversation_id": self.conversation_id,
            "project_id": self.project_id,
            "messages": [asdict(msg) for msg in self.messages],
            "codebase_context": self.codebase_context,
            "tool_history": self.tool_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Context":
        """Create from dictionary"""
        messages = [
            Message(**msg) if isinstance(msg, dict) else msg
            for msg in data.get("messages", [])
        ]
        return cls(
            conversation_id=data["conversation_id"],
            project_id=data.get("project_id"),
            messages=messages,
            codebase_context=data.get("codebase_context"),
            tool_history=data.get("tool_history", []),
        )


class ContextManager:
    """Manages conversation context and history"""

    def __init__(self, storage_backend: Optional[StorageBackend] = None, config=None):
        """
        Initialize context manager
        
        Args:
            storage_backend: Optional storage backend instance
            config: Optional config instance (will load if not provided)
        """
        if config is None:
            config = load_config()
        
        self.config = config
        
        # Initialize storage backend
        if storage_backend:
            self.storage = storage_backend
        else:
            # Create storage backend from config
            db_type = DatabaseType(config.storage.db_type.lower())
            if db_type == DatabaseType.POSTGRESQL:
                if not config.storage.connection_string:
                    raise ValueError("PostgreSQL requires connection_string in config")
                self.storage = create_storage_backend(
                    db_type,
                    connection_string=config.storage.connection_string
                )
            else:
                self.storage = create_storage_backend(
                    db_type,
                    db_path=Path(config.storage.db_path)
                )
        
        # Initialize Rust-based context management components if available
        if HAS_PYO3:
            self.window_manager = PyContextWindowManager()
            self.compressor = PyContextCompressor()
        else:
            self.window_manager = None
            self.compressor = None
    
    async def initialize(self) -> None:
        """Initialize the storage backend"""
        await self.storage.initialize()
    
    async def get_or_create_context(
        self,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Context:
        """Get existing context or create new one"""
        await self.initialize()
        
        if conversation_id:
            context = await self.get_context(conversation_id)
            if context:
                return context

        # Create new context
        conversation_id = conversation_id or str(uuid.uuid4())
        context = Context(
            conversation_id=conversation_id,
            project_id=project_id,
            messages=[],
            codebase_context=None,
            tool_history=[],
        )

        await self.save_context(context)
        return context

    async def get_context(self, conversation_id: str) -> Optional[Context]:
        """Get context by conversation ID"""
        await self.initialize()
        
        data_str = await self.storage.load_context(conversation_id)
        if data_str:
            data = json.loads(data_str)
            return Context.from_dict(data)

        return None

    async def save_context(self, context: Context) -> None:
        """Save context to database"""
        await self.initialize()
        
        data = json.dumps(context.to_dict())
        updated_at = int(datetime.now().timestamp())
        
        await self.storage.save_context(
            context.conversation_id,
            context.project_id,
            data,
            updated_at
        )

    async def add_message(self, context: Context, role: str, content: str) -> None:
        """Add a message to the context"""
        await self.initialize()
        
        timestamp = int(datetime.now().timestamp())
        message = Message(role=role, content=content, timestamp=timestamp)
        context.messages.append(message)
        
        # Also save to messages table
        await self.storage.add_message(
            context.conversation_id,
            role,
            content,
            timestamp
        )
        
        await self.save_context(context)

    async def add_tool_call(
        self, context: Context, tool: str, request: str, response: str
    ) -> None:
        """Add a tool call to the history"""
        timestamp = int(datetime.now().timestamp())
        tool_call = {
            "tool": tool,
            "timestamp": timestamp,
            "request": request,
            "response": response,
        }
        context.tool_history.append(tool_call)
        await self.save_context(context)
    
    def compress(self, context: Context) -> Context:
        """Compress context by removing redundancy"""
        if self.compressor:
            # Use Rust compressor
            context_dict = context.to_dict()
            compressed_dict = self.compressor.compress(context_dict)
            return Context.from_dict(compressed_dict)
        else:
            # Fallback: simple Python compression
            return self._compress_python(context)
    
    def manage_window(self, context: Context, model: str, reserved_tokens: Optional[int] = None) -> Context:
        """Manage context window for a specific model"""
        if self.window_manager:
            # Use Rust window manager
            context_dict = context.to_dict()
            if reserved_tokens:
                managed_dict = self.window_manager.manage_context_with_reserved(
                    context_dict,
                    model,
                    reserved_tokens
                )
            else:
                managed_dict = self.window_manager.manage_context(
                    context_dict,
                    model
                )
            return Context.from_dict(managed_dict)
        else:
            # Fallback: simple Python window management
            return self._manage_window_python(context, model, reserved_tokens or 1000)
    
    def _compress_python(self, context: Context) -> Context:
        """Simple Python-based compression fallback"""
        # Remove consecutive duplicate messages
        compressed_messages = []
        for i, msg in enumerate(context.messages):
            if i == 0 or msg.content != context.messages[i-1].content:
                # Compress long messages
                if len(msg.content) > 2000:
                    compressed = msg.content[:1000] + "... [truncated] ..." + msg.content[-1000:]
                    compressed_messages.append(Message(
                        role=msg.role,
                        content=compressed,
                        timestamp=msg.timestamp
                    ))
                else:
                    compressed_messages.append(msg)
        
        context.messages = compressed_messages
        return context
    
    def _manage_window_python(self, context: Context, model: str, reserved_tokens: int) -> Context:
        """Simple Python-based window management fallback"""
        # Model context windows (approximate)
        model_windows = {
            "gpt-4": 8192,
            "gpt-3.5-turbo": 4096,
            "claude-3-5-sonnet-20241022": 200000,
            "claude-3-opus": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-haiku": 200000,
        }
        
        window_size = model_windows.get(model, 4096)
        available_tokens = window_size - reserved_tokens
        
        # Simple token estimation (4 chars ≈ 1 token)
        total_chars = sum(len(msg.content) for msg in context.messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens <= available_tokens:
            return context
        
        # Keep system messages and recent messages
        kept_messages = []
        token_count = 0
        
        # Keep all system messages
        for msg in context.messages:
            if msg.role == "system":
                msg_tokens = len(msg.content) // 4
                if token_count + msg_tokens <= available_tokens:
                    kept_messages.append(msg)
                    token_count += msg_tokens
        
        # Keep recent messages (iterate in reverse to prioritize newest)
        for msg in reversed(context.messages):
            if msg.role == "system":
                continue
            msg_tokens = len(msg.content) // 4
            if token_count + msg_tokens <= available_tokens:
                kept_messages.insert(len([m for m in kept_messages if m.role == "system"]), msg)
                token_count += msg_tokens
            else:
                break
        
        # Reverse to get correct chronological order (matches Rust implementation)
        kept_messages.reverse()
        context.messages = kept_messages
        return context
    
    async def close(self) -> None:
        """Close the storage backend connection"""
        await self.storage.close()
