"""Tests for context manager"""

import pytest
from unified_ai.context_manager import ContextManager, Context, Message


class TestContextManager:
    """Test context manager"""
    
    def test_create_context(self, context_manager):
        """Test creating a new context"""
        context = context_manager.get_or_create_context()
        
        assert context.conversation_id is not None
        assert len(context.messages) == 0
        assert context.project_id is None
    
    def test_get_existing_context(self, context_manager):
        """Test retrieving existing context"""
        # Create context
        context1 = context_manager.get_or_create_context()
        conv_id = context1.conversation_id
        
        # Retrieve it
        context2 = context_manager.get_or_create_context(conversation_id=conv_id)
        
        assert context2.conversation_id == conv_id
    
    def test_add_message(self, context_manager):
        """Test adding messages to context"""
        context = context_manager.get_or_create_context()
        
        context_manager.add_message(context, "user", "Hello")
        context_manager.add_message(context, "assistant", "Hi there")
        
        assert len(context.messages) == 2
        assert context.messages[0].role == "user"
        assert context.messages[0].content == "Hello"
        assert context.messages[1].role == "assistant"
        assert context.messages[1].content == "Hi there"
    
    def test_add_tool_call(self, context_manager):
        """Test adding tool call to history"""
        context = context_manager.get_or_create_context()
        
        context_manager.add_tool_call(
            context,
            "claude",
            "What is Python?",
            "Python is a programming language",
        )
        
        assert len(context.tool_history) == 1
        assert context.tool_history[0]["tool"] == "claude"
        assert context.tool_history[0]["request"] == "What is Python?"
    
    def test_persistence(self, context_manager):
        """Test context persistence"""
        # Create and modify context
        context = context_manager.get_or_create_context()
        context_manager.add_message(context, "user", "Test message")
        conv_id = context.conversation_id
        
        # Create new manager instance (simulating restart)
        from pathlib import Path
        new_manager = ContextManager(Path(context_manager.db_path))
        
        # Should retrieve persisted context
        retrieved = new_manager.get_context(conv_id)
        assert retrieved is not None
        assert len(retrieved.messages) == 1
        assert retrieved.messages[0].content == "Test message"
