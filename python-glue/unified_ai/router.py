"""Router integration - Python wrapper for Rust router"""

import json
from typing import Dict, List, Optional
from pathlib import Path

# For now, we'll use a Python implementation that matches the Rust logic
# In the future, this can be replaced with PyO3 bindings


class Router:
    """Router for selecting optimal AI tools"""

    def __init__(self, routing_rules: Dict[str, List[str]], default_tool: str):
        self.routing_rules = routing_rules
        self.default_tool = default_tool

    def route(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        explicit_tool: Optional[str] = None,
    ) -> Dict:
        """
        Route a request to the appropriate tool(s)
        
        Returns:
            Dict with 'selected_tools' and 'reasoning'
        """
        if explicit_tool:
            return {
                "selected_tools": [explicit_tool],
                "reasoning": f"Explicit tool selection: {explicit_tool}",
            }

        # Analyze request to determine task type
        task_type = self._analyze_request(message)

        # Select tools based on task type
        tools = self._select_tools(task_type)

        return {
            "selected_tools": tools,
            "reasoning": f"Task type: {task_type}, Selected tools: {tools}",
        }

    def _analyze_request(self, message: str) -> str:
        """Analyze request to determine task type"""
        lower = message.lower()

        # Simple keyword-based classification
        code_keywords = [
            "refactor", "edit", "fix", "bug", "function", "class", "import",
            "code", "file", "module", "package", "syntax", "error", "compile",
            "test", "debug", "implement", "rewrite", "optimize",
        ]
        if any(kw in lower for kw in code_keywords):
            return "code_editing"

        research_keywords = [
            "research", "find", "search", "what is", "explain", "how does",
            "information", "article", "paper", "source", "citation", "reference",
            "learn about", "tell me about", "investigate",
        ]
        if any(kw in lower for kw in research_keywords):
            return "research"

        terminal_keywords = [
            "run", "execute", "command", "terminal", "shell", "script",
            "automate", "workflow", "cli", "bash", "zsh",
        ]
        if any(kw in lower for kw in terminal_keywords):
            return "terminal_automation"

        generation_keywords = [
            "generate", "create", "write", "make", "build", "new",
            "scaffold", "boilerplate", "template",
        ]
        if any(kw in lower for kw in generation_keywords):
            return "code_editing"  # Use code_editing rules

        return "general_chat"

    def _select_tools(self, task_type: str) -> List[str]:
        """Select tools based on task type"""
        rule_key = {
            "code_editing": "code_editing",
            "research": "research",
            "terminal_automation": "general_chat",
            "general_chat": "general_chat",
        }.get(task_type, "general_chat")

        return self.routing_rules.get(rule_key, [self.default_tool])
