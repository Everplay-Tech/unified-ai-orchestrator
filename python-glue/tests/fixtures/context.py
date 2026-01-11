"""Context fixtures for testing"""

import pytest
from unified_ai.context_manager import Context, Message
from datetime import datetime


class ContextBuilder:
    """Builder for creating test contexts"""
    
    def __init__(self):
        self.conversation_id = None
        self.project_id = None
        self.messages = []
        self.codebase_context = None
        self.tool_history = []
    
    def with_conversation_id(self, conversation_id: str):
        """Set conversation ID"""
        self.conversation_id = conversation_id
        return self
    
    def with_project_id(self, project_id: str):
        """Set project ID"""
        self.project_id = project_id
        return self
    
    def add_message(self, role: str, content: str, timestamp: int = None):
        """Add a message"""
        if timestamp is None:
            timestamp = int(datetime.now().timestamp())
        self.messages.append(Message(
            role=role,
            content=content,
            timestamp=timestamp
        ))
        return self
    
    def add_user_message(self, content: str):
        """Add a user message"""
        return self.add_message("user", content)
    
    def add_assistant_message(self, content: str):
        """Add an assistant message"""
        return self.add_message("assistant", content)
    
    def add_system_message(self, content: str):
        """Add a system message"""
        return self.add_message("system", content)
    
    def with_codebase_context(self, context: dict):
        """Set codebase context"""
        self.codebase_context = context
        return self
    
    def with_tool_history(self, history: list):
        """Set tool history"""
        self.tool_history = history
        return self
    
    def build(self) -> Context:
        """Build the context"""
        return Context(
            conversation_id=self.conversation_id,
            project_id=self.project_id,
            messages=self.messages,
            codebase_context=self.codebase_context,
            tool_history=self.tool_history,
        )


@pytest.fixture
def context_builder():
    """Context builder fixture"""
    return ContextBuilder


@pytest.fixture
def sample_context(context_builder):
    """Sample context for testing"""
    return context_builder\
        .with_conversation_id("test-conv-1")\
        .with_project_id("test-project")\
        .add_user_message("Hello")\
        .add_assistant_message("Hi there!")\
        .build()


@pytest.fixture
def empty_context(context_builder):
    """Empty context for testing"""
    return context_builder\
        .with_conversation_id("empty-conv")\
        .build()


@pytest.fixture
def long_context(context_builder):
    """Long context with many messages"""
    builder = context_builder.with_conversation_id("long-conv")
    for i in range(100):
        builder.add_user_message(f"Message {i}")
        builder.add_assistant_message(f"Response {i}")
    return builder.build()
