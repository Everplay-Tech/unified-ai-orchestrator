"""Migration CLI commands"""

from pathlib import Path
from typing import Optional

try:
    from unified_ai_orchestrator.pyo3_bridge import PyMigrationRunner
    HAS_PYO3 = True
except ImportError:
    HAS_PYO3 = False
    # Fallback: use direct SQLite approach
    import sqlite3


def run_migrations(
    db_path: Path,
    target_version: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    """Run database migrations"""
    if HAS_PYO3:
        runner = PyMigrationRunner(str(db_path))
        
        if dry_run:
            status = runner.status()
            print("Migration status:")
            for version, name, applied in status:
                status_str = "✓" if applied else "✗"
                print(f"  {status_str} {version}: {name}")
            return
        
        runner.migrate_up(target_version)
        print("Migrations applied successfully")
    else:
        # Fallback: manual migration using SQLite
        print("PyO3 bindings not available, using fallback method")
        _run_migrations_fallback(db_path, target_version, dry_run)


def _run_migrations_fallback(
    db_path: Path,
    target_version: Optional[int],
    dry_run: bool,
) -> None:
    """Fallback migration method using direct SQLite"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create migrations table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    if dry_run:
        cursor.execute("SELECT version, name FROM schema_migrations ORDER BY version")
        applied = {row[0]: row[1] for row in cursor.fetchall()}
        print("Migration status:")
        # List expected migrations
        migrations = [
            (1, "initial_schema"),
            (2, "add_cost_tracking"),
            (3, "add_indexing"),
            (4, "add_security"),
        ]
        for version, name in migrations:
            status_str = "✓" if version in applied else "✗"
            print(f"  {status_str} {version}: {name}")
        conn.close()
        return
    
    # Note: Full migration execution requires Rust implementation
    print("Full migration execution requires PyO3 bindings")
    conn.close()


def migration_status(db_path: Path) -> None:
    """Show migration status"""
    run_migrations(db_path, dry_run=True)


def rollback_migration(db_path: Path, target_version: int) -> None:
    """Rollback migrations to a specific version"""
    if HAS_PYO3:
        runner = PyMigrationRunner(str(db_path))
        runner.migrate_down(target_version)
        print(f"Rolled back to version {target_version}")
    else:
        print("Rollback requires PyO3 bindings")


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
