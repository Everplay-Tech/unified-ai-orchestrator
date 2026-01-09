"""Tests for router"""

import pytest
from unified_ai.router import Router


class TestRouter:
    """Test router"""
    
    def test_route_explicit_tool(self):
        """Test routing with explicit tool"""
        routing_rules = {
            "code_editing": ["claude"],
            "research": ["perplexity"],
            "general_chat": ["claude", "gpt"],
        }
        router = Router(routing_rules, "claude")
        
        decision = router.route(
            message="Hello",
            explicit_tool="gpt",
        )
        
        assert decision["selected_tools"] == ["gpt"]
        assert "explicit" in decision["reasoning"].lower()
    
    def test_route_code_editing(self):
        """Test routing code editing requests"""
        routing_rules = {
            "code_editing": ["claude"],
            "research": ["perplexity"],
            "general_chat": ["claude", "gpt"],
        }
        router = Router(routing_rules, "claude")
        
        decision = router.route(message="Refactor this function to be more efficient")
        
        assert "claude" in decision["selected_tools"]
        assert "code" in decision["reasoning"].lower() or "editing" in decision["reasoning"].lower()
    
    def test_route_research(self):
        """Test routing research requests"""
        routing_rules = {
            "code_editing": ["claude"],
            "research": ["perplexity"],
            "general_chat": ["claude", "gpt"],
        }
        router = Router(routing_rules, "claude")
        
        decision = router.route(message="What is the latest research on quantum computing?")
        
        assert "perplexity" in decision["selected_tools"] or "research" in decision["reasoning"].lower()
    
    def test_route_default(self):
        """Test default routing"""
        routing_rules = {
            "code_editing": ["claude"],
            "research": ["perplexity"],
            "general_chat": ["claude", "gpt"],
        }
        router = Router(routing_rules, "claude")
        
        decision = router.route(message="Hello, how are you?")
        
        assert len(decision["selected_tools"]) > 0
        assert decision["selected_tools"][0] in ["claude", "gpt"]
