"""Storage abstraction layer for database operations"""

from enum import Enum
from typing import Optional
from pathlib import Path

from .base import StorageBackend, StorageError
from .postgres import PostgreSQLStorage
from .sqlite import SQLiteStorage


class DatabaseType(str, Enum):
    """Supported database types"""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


def create_storage_backend(
    db_type: DatabaseType,
    connection_string: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> StorageBackend:
    """
    Create a storage backend instance
    
    Args:
        db_type: Type of database to use
        connection_string: PostgreSQL connection string (for PostgreSQL)
        db_path: Path to SQLite database file (for SQLite)
    
    Returns:
        StorageBackend instance
    
    Raises:
        StorageError: If backend creation fails
    """
    if db_type == DatabaseType.POSTGRESQL:
        if not connection_string:
            raise StorageError("PostgreSQL requires a connection string")
        return PostgreSQLStorage(connection_string)
    elif db_type == DatabaseType.SQLITE:
        if not db_path:
            raise StorageError("SQLite requires a database path")
        return SQLiteStorage(db_path)
    else:
        raise StorageError(f"Unsupported database type: {db_type}")


__all__ = [
    "StorageBackend",
    "StorageError",
    "DatabaseType",
    "PostgreSQLStorage",
    "SQLiteStorage",
    "create_storage_backend",
]
