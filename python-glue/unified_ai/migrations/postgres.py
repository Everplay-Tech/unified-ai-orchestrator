"""PostgreSQL migration runner"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..storage import PostgreSQLStorage, StorageBackend


class PostgreSQLMigrationRunner:
    """PostgreSQL migration runner"""
    
    def __init__(self, storage: PostgreSQLStorage):
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
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async def get_current_version(self) -> Optional[int]:
        """Get current migration version"""
        await self.ensure_migrations_table()
        
        # Use raw query since we need to check migrations table
        import asyncpg
        if hasattr(self.storage, 'pool') and self.storage.pool:
            async with self.storage.pool.acquire() as conn:
                result = await conn.fetchval("SELECT MAX(version) FROM schema_migrations")
                return int(result) if result else None
        return None
    
    async def get_applied_migrations(self) -> Dict[int, str]:
        """Get applied migrations"""
        await self.ensure_migrations_table()
        
        import asyncpg
        if hasattr(self.storage, 'pool') and self.storage.pool:
            async with self.storage.pool.acquire() as conn:
                rows = await conn.fetch("SELECT version, name FROM schema_migrations ORDER BY version")
                return {row["version"]: row["name"] for row in rows}
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
                import asyncpg
                if hasattr(self.storage, 'pool') and self.storage.pool:
                    async with self.storage.pool.acquire() as conn:
                        async with conn.transaction():
                            # Execute migration SQL (may contain multiple statements)
                            for statement in migration["up_sql"].split(';'):
                                statement = statement.strip()
                                if statement:
                                    await conn.execute(statement)
                            
                            # Record migration
                            await conn.execute(
                                "INSERT INTO schema_migrations (version, name) VALUES ($1, $2)",
                                migration["version"],
                                migration["name"]
                            )
                
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
        
        import asyncpg
        if hasattr(self.storage, 'pool') and self.storage.pool:
            async with self.storage.pool.acquire() as conn:
                for migration in migrations_to_rollback:
                    async with conn.transaction():
                        # Execute rollback SQL (may contain multiple statements)
                        for statement in migration["down_sql"].split(';'):
                            statement = statement.strip()
                            if statement:
                                await conn.execute(statement)
                        
                        # Remove migration record
                        await conn.execute(
                            "DELETE FROM schema_migrations WHERE version = $1",
                            migration["version"]
                        )
    
    async def status(self) -> List[tuple]:
        """Get migration status"""
        await self.ensure_migrations_table()
        applied = await self.get_applied_migrations()
        
        return [
            (m["version"], m["name"], m["version"] in applied)
            for m in self.migrations
        ]
