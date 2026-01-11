"""SQLite migration runner"""

import asyncio
from typing import Optional, List, Dict, Any

from ..storage import SQLiteStorage


class SQLiteMigrationRunner:
    """SQLite migration runner"""
    
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage
        self.migrations = []
    
    def add_migration(self, version: int, name: str, up_sql: str, down_sql: str):
        """Add a migration"""
        self.migrations.append({
            "version": version,
            "name": name,
            "up_sql": up_sql,
            "down_sql": down_sql,
        })
        self.migrations.sort(key=lambda m: m["version"])
    
    async def ensure_migrations_table(self):
        """Ensure migrations table exists"""
        await self.storage.execute_migration("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
    
    async def get_current_version(self) -> Optional[int]:
        """Get current migration version"""
        await self.ensure_migrations_table()
        
        if self.storage.connection:
            cursor = await self.storage.connection.execute(
                "SELECT MAX(version) FROM schema_migrations"
            )
            row = await cursor.fetchone()
            return int(row[0]) if row and row[0] else None
        return None
    
    async def get_applied_migrations(self) -> Dict[int, str]:
        """Get applied migrations"""
        await self.ensure_migrations_table()
        
        if self.storage.connection:
            cursor = await self.storage.connection.execute(
                "SELECT version, name FROM schema_migrations ORDER BY version"
            )
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}
        return {}
    
    async def migrate_up(self, target_version: Optional[int] = None) -> None:
        """Run migrations up"""
        await self.ensure_migrations_table()
        
        current_version = await self.get_current_version()
        applied = await self.get_applied_migrations()
        
        target = target_version or (max([m["version"] for m in self.migrations]) if self.migrations else 0)
        
        for migration in self.migrations:
            if migration["version"] <= target:
                if migration["version"] in applied:
                    continue
                
                # Check for gaps
                if current_version is not None and migration["version"] != current_version + 1:
                    raise ValueError(
                        f"Migration {migration['version']} cannot be applied: expected version {current_version + 1}"
                    )
                
                # Execute migration in transaction
                if self.storage.connection:
                    await self.storage.begin_transaction()
                    try:
                        await self.storage.execute_migration(migration["up_sql"])
                        await self.storage.connection.execute(
                            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                            (migration["version"], migration["name"])
                        )
                        await self.storage.commit_transaction()
                    except Exception:
                        await self.storage.rollback_transaction()
                        raise
                
                current_version = migration["version"]
    
    async def migrate_down(self, target_version: int) -> None:
        """Rollback migrations"""
        await self.ensure_migrations_table()
        
        current_version = await self.get_current_version()
        if current_version is None:
            raise ValueError("No migrations to rollback")
        
        # Find migrations to rollback (in reverse order)
        migrations_to_rollback = [
            m for m in reversed(self.migrations)
            if m["version"] > target_version and m["version"] <= current_version
        ]
        
        if self.storage.connection:
            for migration in migrations_to_rollback:
                await self.storage.begin_transaction()
                try:
                    await self.storage.execute_migration(migration["down_sql"])
                    await self.storage.connection.execute(
                        "DELETE FROM schema_migrations WHERE version = ?",
                        (migration["version"],)
                    )
                    await self.storage.commit_transaction()
                except Exception:
                    await self.storage.rollback_transaction()
                    raise
    
    async def status(self) -> List[tuple]:
        """Get migration status"""
        await self.ensure_migrations_table()
        applied = await self.get_applied_migrations()
        
        return [
            (m["version"], m["name"], m["version"] in applied)
            for m in self.migrations
        ]
    
    def validate_migrations(self) -> List[str]:
        """Validate migrations for conflicts and issues"""
        errors = []
        
        # Check for duplicate versions
        versions = [m["version"] for m in self.migrations]
        seen_versions = set()
        for version in versions:
            if version in seen_versions:
                errors.append(f"Duplicate migration version: {version}")
            seen_versions.add(version)
        
        # Check for gaps in versions
        if versions:
            sorted_versions = sorted(versions)
            for i in range(len(sorted_versions) - 1):
                if sorted_versions[i + 1] != sorted_versions[i] + 1:
                    errors.append(
                        f"Gap in migration versions: {sorted_versions[i]} -> {sorted_versions[i + 1]}"
                    )
        
        # Check for empty SQL
        for migration in self.migrations:
            if not migration["up_sql"] or not migration["up_sql"].strip():
                errors.append(f"Migration {migration['version']} has empty up_sql")
            if not migration["down_sql"] or not migration["down_sql"].strip():
                errors.append(f"Migration {migration['version']} has empty down_sql")
        
        return errors
    
    async def validate_sql_syntax(self, sql: str) -> tuple[bool, Optional[str]]:
        """Validate SQL syntax (basic check)"""
        # Basic SQL syntax validation
        sql_upper = sql.upper().strip()
        
        # Check for basic SQL keywords
        if not any(keyword in sql_upper for keyword in ["CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE", "SELECT"]):
            return False, "SQL does not contain valid SQL statements"
        
        # Check for balanced parentheses
        if sql.count('(') != sql.count(')'):
            return False, "Unbalanced parentheses in SQL"
        
        # Check for balanced quotes
        single_quotes = sql.count("'") % 2
        double_quotes = sql.count('"') % 2
        if single_quotes != 0 or double_quotes != 0:
            return False, "Unbalanced quotes in SQL"
        
        return True, None
    
    async def validate_migration_state(self) -> tuple[bool, List[str]]:
        """Validate database state matches migration history"""
        errors = []
        await self.ensure_migrations_table()
        
        applied = await self.get_applied_migrations()
        current_version = await self.get_current_version()
        
        # Check that applied migrations match registered migrations
        for version, name in applied.items():
            migration = next((m for m in self.migrations if m["version"] == version), None)
            if not migration:
                errors.append(f"Applied migration {version}:{name} not found in registered migrations")
            elif migration["name"] != name:
                errors.append(
                    f"Migration {version} name mismatch: applied '{name}' vs registered '{migration['name']}'"
                )
        
        # Check for missing migrations
        for migration in self.migrations:
            if migration["version"] <= (current_version or 0):
                if migration["version"] not in applied:
                    errors.append(
                        f"Migration {migration['version']}:{migration['name']} should be applied but is missing"
                    )
        
        return len(errors) == 0, errors
