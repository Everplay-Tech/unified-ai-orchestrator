"""Integration tests for router"""

import pytest
from unified_ai.router import Router
from unified_ai.config import Config


@pytest.fixture
def router():
    """Create router instance"""
    routing_rules = {
        "code_editing": ["claude"],
        "research": ["perplexity"],
        "general_chat": ["claude", "gpt"],
    }
    return Router(routing_rules, default_tool="claude")


def test_router_code_editing(router):
    """Test router for code editing tasks"""
    decision = router.route(
        message="Refactor this function to be more efficient",
        conversation_id=None,
        project_id=None,
    )
    
    assert "selected_tools" in decision
    assert "claude" in decision["selected_tools"]
    assert "reasoning" in decision


def test_router_research(router):
    """Test router for research tasks"""
    decision = router.route(
        message="What is the latest research on quantum computing?",
        conversation_id=None,
        project_id=None,
    )
    
    assert "selected_tools" in decision
    # Should prefer perplexity for research
    assert "perplexity" in decision["selected_tools"] or "claude" in decision["selected_tools"]


def test_router_general_chat(router):
    """Test router for general chat"""
    decision = router.route(
        message="Hello, how are you?",
        conversation_id=None,
        project_id=None,
    )
    
    assert "selected_tools" in decision
    assert len(decision["selected_tools"]) > 0


def test_router_explicit_tool(router):
    """Test router with explicit tool"""
    decision = router.route(
        message="Hello",
        conversation_id=None,
        project_id=None,
        explicit_tool="gpt",
    )
    
    assert "selected_tools" in decision
    assert "gpt" in decision["selected_tools"]


def test_router_with_project_context(router):
    """Test router with project context"""
    decision = router.route(
        message="Explain this code",
        conversation_id=None,
        project_id="test-project",
    )
    
    assert "selected_tools" in decision
    # Should prefer tools that support code context
    assert len(decision["selected_tools"]) > 0
