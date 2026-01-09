"""Adapter utilities"""

from typing import Dict
from ..adapters import (
    ClaudeAdapter,
    GPTAdapter,
    PerplexityAdapter,
    GeminiAdapter,
    ToolAdapter,
)
from ..config import Config
from ..utils.auth import get_api_key


def get_adapters(config: Config) -> Dict[str, ToolAdapter]:
    """Get configured adapters"""
    adapters = {}
    
    # Claude adapter
    if "claude" in config.tools:
        tool_config = config.tools["claude"]
        if tool_config.enabled:
            api_key = tool_config.api_key or get_api_key("anthropic")
            if api_key:
                adapters["claude"] = ClaudeAdapter(
                    api_key=api_key,
                    model=tool_config.model or "claude-3-5-sonnet-20241022",
                )
    
    # GPT adapter
    if "gpt" in config.tools:
        tool_config = config.tools["gpt"]
        if tool_config.enabled:
            api_key = tool_config.api_key or get_api_key("openai")
            if api_key:
                adapters["gpt"] = GPTAdapter(
                    api_key=api_key,
                    model=tool_config.model or "gpt-4",
                )
    
    # Perplexity adapter
    if "perplexity" in config.tools:
        tool_config = config.tools["perplexity"]
        if tool_config.enabled:
            api_key = tool_config.api_key or get_api_key("perplexity")
            if api_key:
                adapters["perplexity"] = PerplexityAdapter(
                    api_key=api_key,
                    model=tool_config.model or "llama-3.1-sonar-large-128k-online",
                )
    
    # Gemini adapter
    if "gemini" in config.tools:
        tool_config = config.tools["gemini"]
        if tool_config.enabled:
            api_key = tool_config.api_key or get_api_key("gemini")
            if api_key:
                try:
                    adapters["gemini"] = GeminiAdapter(
                        api_key=api_key,
                        model=tool_config.model or "gemini-pro",
                    )
                except ImportError:
                    pass  # Gemini package not installed
    
    return adapters
