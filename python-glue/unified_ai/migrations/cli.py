"""Migration CLI commands"""

import asyncio
from pathlib import Path
from typing import Optional

from ..storage import create_storage_backend, DatabaseType, PostgreSQLStorage, SQLiteStorage
from ..config import load_config
from .migrations import MIGRATIONS
from .postgres import PostgreSQLMigrationRunner
from .sqlite import SQLiteMigrationRunner


async def _run_migrations_async(
    storage_backend,
    target_version: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    """Run database migrations (async)"""
    await storage_backend.initialize()
    
    # Create appropriate migration runner
    if isinstance(storage_backend, PostgreSQLStorage):
        runner = PostgreSQLMigrationRunner(storage_backend)
        for migration in MIGRATIONS:
            runner.add_migration(
                migration["version"],
                migration["name"],
                migration["up_postgresql"],
                migration["down_postgresql"],
            )
    elif isinstance(storage_backend, SQLiteStorage):
        runner = SQLiteMigrationRunner(storage_backend)
        for migration in MIGRATIONS:
            runner.add_migration(
                migration["version"],
                migration["name"],
                migration["up_sqlite"],
                migration["down_sqlite"],
            )
    else:
        raise ValueError(f"Unsupported storage backend: {type(storage_backend)}")
    
    if dry_run:
        status = await runner.status()
        print("Migration status:")
        for version, name, applied in status:
            status_str = "✓" if applied else "✗"
            print(f"  {status_str} {version}: {name}")
        return
    
    await runner.migrate_up(target_version)
    print("Migrations applied successfully")


def run_migrations(
    db_path: Optional[Path] = None,
    connection_string: Optional[str] = None,
    db_type: Optional[str] = None,
    target_version: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    """Run database migrations"""
    config = load_config()
    
    # Determine database type
    if db_type:
        db_type_enum = DatabaseType(db_type.lower())
    else:
        db_type_enum = DatabaseType(config.storage.db_type.lower())
    
    # Create storage backend
    if db_type_enum == DatabaseType.POSTGRESQL:
        conn_str = connection_string or config.storage.connection_string
        if not conn_str:
            raise ValueError("PostgreSQL requires connection_string")
        storage = create_storage_backend(db_type_enum, connection_string=conn_str)
    else:
        db_path_val = db_path or Path(config.storage.db_path)
        storage = create_storage_backend(db_type_enum, db_path=db_path_val)
    
    # Run migrations
    asyncio.run(_run_migrations_async(storage, target_version, dry_run))


async def _migration_status_async(storage_backend) -> None:
    """Show migration status (async)"""
    await _run_migrations_async(storage_backend, dry_run=True)


def migration_status(
    db_path: Optional[Path] = None,
    connection_string: Optional[str] = None,
    db_type: Optional[str] = None,
) -> None:
    """Show migration status"""
    run_migrations(db_path=db_path, connection_string=connection_string, db_type=db_type, dry_run=True)


async def _rollback_migration_async(
    storage_backend,
    target_version: int,
) -> None:
    """Rollback migrations (async)"""
    await storage_backend.initialize()
    
    # Create appropriate migration runner
    if isinstance(storage_backend, PostgreSQLStorage):
        runner = PostgreSQLMigrationRunner(storage_backend)
        for migration in MIGRATIONS:
            runner.add_migration(
                migration["version"],
                migration["name"],
                migration["up_postgresql"],
                migration["down_postgresql"],
            )
    elif isinstance(storage_backend, SQLiteStorage):
        runner = SQLiteMigrationRunner(storage_backend)
        for migration in MIGRATIONS:
            runner.add_migration(
                migration["version"],
                migration["name"],
                migration["up_sqlite"],
                migration["down_sqlite"],
            )
    else:
        raise ValueError(f"Unsupported storage backend: {type(storage_backend)}")
    
    await runner.migrate_down(target_version)
    print(f"Rolled back to version {target_version}")


def rollback_migration(
    target_version: int,
    db_path: Optional[Path] = None,
    connection_string: Optional[str] = None,
    db_type: Optional[str] = None,
) -> None:
    """Rollback migrations to a specific version"""
    config = load_config()
    
    # Determine database type
    if db_type:
        db_type_enum = DatabaseType(db_type.lower())
    else:
        db_type_enum = DatabaseType(config.storage.db_type.lower())
    
    # Create storage backend
    if db_type_enum == DatabaseType.POSTGRESQL:
        conn_str = connection_string or config.storage.connection_string
        if not conn_str:
            raise ValueError("PostgreSQL requires connection_string")
        storage = create_storage_backend(db_type_enum, connection_string=conn_str)
    else:
        db_path_val = db_path or Path(config.storage.db_path)
        storage = create_storage_backend(db_type_enum, db_path=db_path_val)
    
    # Rollback migrations
    asyncio.run(_rollback_migration_async(storage, target_version))


def main():
    """CLI entry point"""
    import typer
    
    app = typer.Typer()
    
    @app.command()
    def migrate(
        db_path: Optional[str] = typer.Option(None, help="Path to SQLite database file"),
        connection_string: Optional[str] = typer.Option(None, help="PostgreSQL connection string"),
        db_type: Optional[str] = typer.Option(None, help="Database type: sqlite or postgresql"),
        target_version: Optional[int] = typer.Option(None, help="Target version"),
        dry_run: bool = typer.Option(False, help="Dry run mode"),
    ):
        """Run migrations"""
        run_migrations(
            db_path=Path(db_path) if db_path else None,
            connection_string=connection_string,
            db_type=db_type,
            target_version=target_version,
            dry_run=dry_run,
        )
    
    @app.command()
    def status(
        db_path: Optional[str] = typer.Option(None, help="Path to SQLite database file"),
        connection_string: Optional[str] = typer.Option(None, help="PostgreSQL connection string"),
        db_type: Optional[str] = typer.Option(None, help="Database type: sqlite or postgresql"),
    ):
        """Show migration status"""
        migration_status(
            db_path=Path(db_path) if db_path else None,
            connection_string=connection_string,
            db_type=db_type,
        )
    
    @app.command()
    def rollback(
        target_version: int = typer.Option(..., help="Target version to rollback to"),
        db_path: Optional[str] = typer.Option(None, help="Path to SQLite database file"),
        connection_string: Optional[str] = typer.Option(None, help="PostgreSQL connection string"),
        db_type: Optional[str] = typer.Option(None, help="Database type: sqlite or postgresql"),
    ):
        """Rollback migrations"""
        rollback_migration(
            target_version,
            db_path=Path(db_path) if db_path else None,
            connection_string=connection_string,
            db_type=db_type,
        )
    
    @app.command()
    def validate(
        db_path: Optional[str] = typer.Option(None, help="Path to SQLite database file"),
        connection_string: Optional[str] = typer.Option(None, help="PostgreSQL connection string"),
        db_type: Optional[str] = typer.Option(None, help="Database type: sqlite or postgresql"),
    ):
        """Validate migrations and database state"""
        config = load_config()
        
        if db_type:
            db_type_enum = DatabaseType(db_type.lower())
        else:
            db_type_enum = DatabaseType(config.storage.db_type.lower())
        
        if db_type_enum == DatabaseType.POSTGRESQL:
            conn_str = connection_string or config.storage.connection_string
            if not conn_str:
                raise ValueError("PostgreSQL requires connection_string")
            storage = create_storage_backend(db_type_enum, connection_string=conn_str)
        else:
            db_path_val = db_path or Path(config.storage.db_path)
            storage = create_storage_backend(db_type_enum, db_path=db_path_val)
        
        asyncio.run(_validate_migrations_async(storage))


async def _validate_migrations_async(storage_backend) -> None:
    """Validate migrations (async)"""
    await storage_backend.initialize()
    
    if isinstance(storage_backend, PostgreSQLStorage):
        runner = PostgreSQLMigrationRunner(storage_backend)
        for migration in MIGRATIONS:
            runner.add_migration(
                migration["version"],
                migration["name"],
                migration["up_postgresql"],
                migration["down_postgresql"],
            )
    elif isinstance(storage_backend, SQLiteStorage):
        runner = SQLiteMigrationRunner(storage_backend)
        for migration in MIGRATIONS:
            runner.add_migration(
                migration["version"],
                migration["name"],
                migration["up_sqlite"],
                migration["down_sqlite"],
            )
    else:
        raise ValueError(f"Unsupported storage backend: {type(storage_backend)}")
    
    # Validate migrations
    errors = runner.validate_migrations()
    if errors:
        typer.echo("Migration validation errors:", err=True)
        for error in errors:
            typer.echo(f"  - {error}", err=True)
        raise typer.Exit(1)
    
    # Validate database state
    is_valid, state_errors = await runner.validate_migration_state()
    if not is_valid:
        typer.echo("Database state validation errors:", err=True)
        for error in state_errors:
            typer.echo(f"  - {error}", err=True)
        raise typer.Exit(1)
    
    typer.echo("All migrations validated successfully")


if __name__ == "__main__":
    main()
