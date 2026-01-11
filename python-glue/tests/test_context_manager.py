"""Tests for context manager"""

import pytest
from unified_ai.context_manager import ContextManager, Context, Message


class TestContextManager:
    """Test context manager"""
    
    @pytest.mark.asyncio
    async def test_create_context(self, context_manager):
        """Test creating a new context"""
        context = await context_manager.get_or_create_context()
        
        assert context.conversation_id is not None
        assert len(context.messages) == 0
        assert context.project_id is None
    
    @pytest.mark.asyncio
    async def test_get_existing_context(self, context_manager):
        """Test retrieving existing context"""
        # Create context
        context1 = await context_manager.get_or_create_context()
        conv_id = context1.conversation_id
        
        # Retrieve it
        context2 = await context_manager.get_or_create_context(conversation_id=conv_id)
        
        assert context2.conversation_id == conv_id
    
    @pytest.mark.asyncio
    async def test_add_message(self, context_manager):
        """Test adding messages to context"""
        context = await context_manager.get_or_create_context()
        
        await context_manager.add_message(context, "user", "Hello")
        await context_manager.add_message(context, "assistant", "Hi there")
        
        assert len(context.messages) == 2
        assert context.messages[0].role == "user"
        assert context.messages[0].content == "Hello"
        assert context.messages[1].role == "assistant"
        assert context.messages[1].content == "Hi there"
    
    @pytest.mark.asyncio
    async def test_add_tool_call(self, context_manager):
        """Test adding tool call to history"""
        context = await context_manager.get_or_create_context()
        
        await context_manager.add_tool_call(
            context,
            "claude",
            "What is Python?",
            "Python is a programming language",
        )
        
        assert len(context.tool_history) == 1
        assert context.tool_history[0]["tool"] == "claude"
        assert context.tool_history[0]["request"] == "What is Python?"
    
    @pytest.mark.asyncio
    async def test_persistence(self, context_manager):
        """Test context persistence"""
        # Create and modify context
        context = await context_manager.get_or_create_context()
        await context_manager.add_message(context, "user", "Test message")
        conv_id = context.conversation_id
        
        # Save context
        await context_manager.save_context(context)
        
        # Create new manager instance (simulating restart)
        from pathlib import Path
        from unified_ai.storage import create_storage_backend, DatabaseType
        
        # Get the storage backend's db_path
        db_path = getattr(context_manager.storage, 'db_path', None)
        if db_path is None:
            # Try to get from config
            db_path = Path(context_manager.config.storage.db_path)
        
        new_storage = create_storage_backend(DatabaseType.SQLITE, db_path=db_path)
        await new_storage.initialize()
        new_manager = ContextManager(storage_backend=new_storage, config=context_manager.config)
        await new_manager.initialize()
        
        try:
            # Should retrieve persisted context
            retrieved = await new_manager.get_context(conv_id)
            assert retrieved is not None
            assert len(retrieved.messages) == 1
            assert retrieved.messages[0].content == "Test message"
        finally:
            await new_manager.close()
