"""Pytest configuration and fixtures"""

import pytest
import tempfile
from pathlib import Path
from unified_ai.config import Config, ToolConfig
from unified_ai.context_manager import ContextManager
from unified_ai.cost import CostTracker


@pytest.fixture
def temp_db_path():
    """Temporary database path for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def test_config():
    """Test configuration"""
    config = Config()
    config.tools["claude"] = ToolConfig(
        api_key_env="ANTHROPIC_API_KEY",
        enabled=True,
        model="claude-3-5-sonnet-20241022",
    )
    return config


@pytest.fixture
def context_manager(temp_db_path):
    """Context manager fixture"""
    return ContextManager(temp_db_path)


@pytest.fixture
def cost_tracker(temp_db_path):
    """Cost tracker fixture"""
    return CostTracker(temp_db_path)
