"""Database fixtures for testing"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unified_ai.storage import create_storage_backend, DatabaseType, SQLiteStorage


@pytest.fixture
def temp_db_path():
    """Temporary database path"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
async def sqlite_storage(temp_db_path):
    """SQLite storage backend"""
    storage = create_storage_backend(DatabaseType.SQLITE, db_path=temp_db_path)
    await storage.initialize()
    yield storage
    await storage.close()


@pytest.fixture
def test_db_factory():
    """Factory for creating test databases"""
    def _create_db():
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)
    return _create_db


class DatabaseFixture:
    """Database fixture helper"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.storage = None
    
    async def setup(self):
        """Setup database"""
        self.storage = create_storage_backend(DatabaseType.SQLITE, db_path=self.db_path)
        await self.storage.initialize()
        return self.storage
    
    async def teardown(self):
        """Teardown database"""
        if self.storage:
            await self.storage.close()
        if self.db_path.exists():
            self.db_path.unlink()
    
    async def __aenter__(self):
        return await self.setup()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.teardown()


@pytest.fixture
def db_fixture(temp_db_path):
    """Database fixture context manager"""
    return DatabaseFixture(temp_db_path)
