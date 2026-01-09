"""Migration CLI commands"""

import asyncio
from pathlib import Path
from typing import Optional

import sqlx
from rust_core import MigrationRunner, register_migrations


async def run_migrations(
    db_path: Path,
    target_version: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    """Run database migrations"""
    # Create connection pool
    pool = sqlx.sqlite.create_pool(
        str(db_path),
        min_size=1,
        max_size=5,
    ).await
    
    runner = MigrationRunner.new(pool)
    register_migrations(runner)
    
    if dry_run:
        status = await runner.status()
        print("Migration status:")
        for version, name, applied in status:
            status_str = "✓" if applied else "✗"
            print(f"  {status_str} {version}: {name}")
        return
    
    await runner.migrate_up(target_version)
    print(f"Migrations applied successfully")


async def migration_status(db_path: Path) -> None:
    """Show migration status"""
    await run_migrations(db_path, dry_run=True)


async def rollback_migration(db_path: Path, target_version: int) -> None:
    """Rollback migrations to a specific version"""
    pool = sqlx.sqlite.create_pool(
        str(db_path),
        min_size=1,
        max_size=5,
    ).await
    
    runner = MigrationRunner.new(pool)
    register_migrations(runner)
    
    await runner.migrate_down(target_version)
    print(f"Rolled back to version {target_version}")


def main():
    """CLI entry point"""
    import typer
    
    app = typer.Typer()
    
    @app.command()
    def migrate(
        db_path: str = typer.Option(..., help="Path to database file"),
        target_version: Optional[int] = typer.Option(None, help="Target version"),
        dry_run: bool = typer.Option(False, help="Dry run mode"),
    ):
        """Run migrations"""
        asyncio.run(run_migrations(Path(db_path), target_version, dry_run))
    
    @app.command()
    def status(db_path: str = typer.Option(..., help="Path to database file")):
        """Show migration status"""
        asyncio.run(migration_status(Path(db_path)))
    
    @app.command()
    def rollback(
        db_path: str = typer.Option(..., help="Path to database file"),
        target_version: int = typer.Option(..., help="Target version"),
    ):
        """Rollback migrations"""
        asyncio.run(rollback_migration(Path(db_path), target_version))
    
    app()


if __name__ == "__main__":
    main()
