"""Pytest configuration and fixtures"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unified_ai.config import Config, ToolConfig
from unified_ai.context_manager import ContextManager
from unified_ai.cost import CostTracker

# Configure pytest-asyncio to use auto mode
pytest_plugins = ("pytest_asyncio",)


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
@pytest.mark.asyncio
async def context_manager(temp_db_path):
    """Context manager fixture"""
    from unified_ai.storage import create_storage_backend, DatabaseType
    
    # Create storage backend from temp_db_path
    storage = create_storage_backend(DatabaseType.SQLITE, db_path=temp_db_path)
    await storage.initialize()
    
    # Create context manager with storage backend
    manager = ContextManager(storage_backend=storage)
    await manager.initialize()
    yield manager
    await manager.close()
    await storage.close()


@pytest.fixture
def cost_tracker(temp_db_path):
    """Cost tracker fixture"""
    return CostTracker(temp_db_path)
