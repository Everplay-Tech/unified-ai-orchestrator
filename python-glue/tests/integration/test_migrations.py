"""Integration tests for database migrations"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from unified_ai.storage import create_storage_backend, DatabaseType, SQLiteStorage, PostgreSQLStorage
from unified_ai.migrations.cli import (
    run_migrations,
    migration_status,
    rollback_migration,
    _run_migrations_async,
    _migration_status_async,
    _rollback_migration_async,
)
from unified_ai.migrations.migrations import MIGRATIONS
from unified_ai.migrations.sqlite import SQLiteMigrationRunner
from unified_ai.migrations.postgres import PostgreSQLMigrationRunner


@pytest.fixture
def temp_db_path():
    """Create a temporary database file"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sqlite_storage(temp_db_path):
    """Create SQLite storage backend"""
    storage = create_storage_backend(DatabaseType.SQLITE, db_path=temp_db_path)
    return storage


@pytest.mark.asyncio
async def test_migration_runner_initialization(sqlite_storage):
    """Test migration runner initialization"""
    await sqlite_storage.initialize()
    runner = SQLiteMigrationRunner(sqlite_storage)
    
    # Add migrations
    for migration in MIGRATIONS:
        runner.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
    
    assert len(runner.migrations) == len(MIGRATIONS)


@pytest.mark.asyncio
async def test_migration_up(sqlite_storage):
    """Test running migrations up"""
    await sqlite_storage.initialize()
    runner = SQLiteMigrationRunner(sqlite_storage)
    
    for migration in MIGRATIONS:
        runner.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
    
    # Run migrations
    await runner.migrate_up()
    
    # Check that migrations table exists
    current_version = await runner.get_current_version()
    assert current_version is not None
    assert current_version == len(MIGRATIONS)


@pytest.mark.asyncio
async def test_migration_status(sqlite_storage):
    """Test migration status"""
    await sqlite_storage.initialize()
    runner = SQLiteMigrationRunner(sqlite_storage)
    
    for migration in MIGRATIONS:
        runner.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
    
    # Run migrations
    await runner.migrate_up()
    
    # Check status
    status = await runner.status()
    assert len(status) == len(MIGRATIONS)
    
    # All migrations should be applied
    for version, name, applied in status:
        assert applied, f"Migration {version}:{name} should be applied"


@pytest.mark.asyncio
async def test_migration_rollback(sqlite_storage):
    """Test rolling back migrations"""
    await sqlite_storage.initialize()
    runner = SQLiteMigrationRunner(sqlite_storage)
    
    for migration in MIGRATIONS:
        runner.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
    
    # Run migrations up
    await runner.migrate_up()
    current_version = await runner.get_current_version()
    assert current_version == len(MIGRATIONS)
    
    # Rollback to version 2
    if len(MIGRATIONS) > 2:
        await runner.migrate_down(2)
        current_version = await runner.get_current_version()
        assert current_version == 2


@pytest.mark.asyncio
async def test_migration_target_version(sqlite_storage):
    """Test migrating to a specific target version"""
    await sqlite_storage.initialize()
    runner = SQLiteMigrationRunner(sqlite_storage)
    
    for migration in MIGRATIONS:
        runner.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
    
    # Migrate to version 2
    if len(MIGRATIONS) > 2:
        await runner.migrate_up(target_version=2)
        current_version = await runner.get_current_version()
        assert current_version == 2


@pytest.mark.asyncio
async def test_migration_dry_run(sqlite_storage):
    """Test migration dry run"""
    await sqlite_storage.initialize()
    runner = SQLiteMigrationRunner(sqlite_storage)
    
    for migration in MIGRATIONS:
        runner.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
    
    # Dry run should not apply migrations
    status_before = await runner.status()
    await runner.migrate_up(dry_run=True)
    status_after = await runner.status()
    
    # Status should be the same (no migrations applied)
    assert status_before == status_after


@pytest.mark.asyncio
async def test_migration_error_handling(sqlite_storage):
    """Test error handling for invalid migrations"""
    await sqlite_storage.initialize()
    runner = SQLiteMigrationRunner(sqlite_storage)
    
    # Add invalid migration
    runner.add_migration(
        999,
        "invalid_migration",
        "INVALID SQL SYNTAX!!!",
        "DROP TABLE IF EXISTS invalid_table",
    )
    
    # Should raise an error
    with pytest.raises(Exception):
        await runner.migrate_up()


@pytest.mark.asyncio
async def test_concurrent_migration_attempts(sqlite_storage):
    """Test that concurrent migration attempts are handled"""
    await sqlite_storage.initialize()
    
    # Create two runners
    runner1 = SQLiteMigrationRunner(sqlite_storage)
    runner2 = SQLiteMigrationRunner(sqlite_storage)
    
    for migration in MIGRATIONS:
        runner1.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
        runner2.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
    
    # Try to run migrations concurrently
    # One should succeed, the other should handle the conflict gracefully
    results = await asyncio.gather(
        runner1.migrate_up(),
        runner2.migrate_up(),
        return_exceptions=True,
    )
    
    # At least one should succeed
    assert any(not isinstance(r, Exception) for r in results)


def test_migration_cli_run(temp_db_path):
    """Test migration CLI run command"""
    with patch('unified_ai.migrations.cli.load_config') as mock_config:
        mock_config.return_value = MagicMock(
            storage=MagicMock(
                db_type='sqlite',
                db_path=str(temp_db_path),
            )
        )
        
        # Should not raise an error
        run_migrations(db_path=temp_db_path, db_type='sqlite')


def test_migration_cli_status(temp_db_path):
    """Test migration CLI status command"""
    with patch('unified_ai.migrations.cli.load_config') as mock_config:
        mock_config.return_value = MagicMock(
            storage=MagicMock(
                db_type='sqlite',
                db_path=str(temp_db_path),
            )
        )
        
        # Should not raise an error
        migration_status(db_path=temp_db_path, db_type='sqlite')


def test_migration_cli_rollback(temp_db_path):
    """Test migration CLI rollback command"""
    with patch('unified_ai.migrations.cli.load_config') as mock_config:
        mock_config.return_value = MagicMock(
            storage=MagicMock(
                db_type='sqlite',
                db_path=str(temp_db_path),
            )
        )
        
        # First run migrations
        run_migrations(db_path=temp_db_path, db_type='sqlite')
        
        # Then rollback
        if len(MIGRATIONS) > 1:
            rollback_migration(
                1,
                db_path=temp_db_path,
                db_type='sqlite',
            )


@pytest.mark.asyncio
async def test_migration_version_tracking(sqlite_storage):
    """Test that migration versions are tracked correctly"""
    await sqlite_storage.initialize()
    runner = SQLiteMigrationRunner(sqlite_storage)
    
    for migration in MIGRATIONS:
        runner.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
    
    # Run migrations one by one and check version
    for i, migration in enumerate(MIGRATIONS, start=1):
        await runner.migrate_up(target_version=i)
        current_version = await runner.get_current_version()
        assert current_version == i


@pytest.mark.asyncio
async def test_migration_applied_migrations(sqlite_storage):
    """Test getting applied migrations"""
    await sqlite_storage.initialize()
    runner = SQLiteMigrationRunner(sqlite_storage)
    
    for migration in MIGRATIONS:
        runner.add_migration(
            migration["version"],
            migration["name"],
            migration["up_sqlite"],
            migration["down_sqlite"],
        )
    
    # Run migrations
    await runner.migrate_up()
    
    # Get applied migrations
    applied = await runner.get_applied_migrations()
    assert len(applied) == len(MIGRATIONS)
    
    # Check that all migrations are in the list
    for migration in MIGRATIONS:
        assert migration["version"] in applied
        assert applied[migration["version"]] == migration["name"]
