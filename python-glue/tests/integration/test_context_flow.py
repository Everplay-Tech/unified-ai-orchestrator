"""Integration tests for context flow"""

import pytest
from unified_ai.context_manager import ContextManager, Context


@pytest.fixture
def context_manager():
    """Create context manager"""
    return ContextManager()


def test_context_creation(context_manager):
    """Test context creation"""
    context = context_manager.create_context(project_id="test-project")
    assert context.conversation_id is not None
    assert context.project_id == "test-project"


def test_context_persistence(context_manager):
    """Test context persistence"""
    # Create context
    context = context_manager.create_context()
    conversation_id = context.conversation_id
    
    # Add message
    context.add_message("user", "Hello")
    context_manager.save_context(context)
    
    # Load context
    loaded = context_manager.load_context(conversation_id)
    assert loaded is not None
    assert len(loaded.messages) == 1
    assert loaded.messages[0].content == "Hello"
