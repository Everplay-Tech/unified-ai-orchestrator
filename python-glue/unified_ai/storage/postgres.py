"""PostgreSQL storage backend implementation"""

import json
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncpg
from asyncpg import Pool, Connection

from .base import StorageBackend, StorageError


class PostgreSQLStorage(StorageBackend):
    """PostgreSQL storage backend"""
    
    def __init__(self, connection_string: str):
        """
        Initialize PostgreSQL storage backend
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.pool: Optional[Pool] = None
    
    async def initialize(self) -> None:
        """Initialize the storage backend"""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
        
        # Create tables if they don't exist
        async with self.pool.acquire() as conn:
            await self._create_tables(conn)
    
    async def _create_tables(self, conn: Connection) -> None:
        """Create database tables"""
        # Contexts table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                conversation_id VARCHAR(255) PRIMARY KEY,
                project_id VARCHAR(255),
                data TEXT NOT NULL,
                updated_at BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Messages table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                timestamp BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES contexts(conversation_id) ON DELETE CASCADE
            )
        """)
        
        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(255) PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                password_hash VARCHAR(255),
                role VARCHAR(50) NOT NULL DEFAULT 'user',
                api_key_hash VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # API keys table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id VARCHAR(255) PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                key_hash VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255),
                expires_at BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                revoked_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Audit logs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                event_type VARCHAR(100) NOT NULL,
                user_id VARCHAR(255),
                resource_type VARCHAR(100),
                resource_id VARCHAR(255),
                ip_address VARCHAR(45),
                user_agent TEXT,
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Cost tracking table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cost_records (
                id SERIAL PRIMARY KEY,
                tool VARCHAR(100) NOT NULL,
                model VARCHAR(100) NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd DECIMAL(10, 6) NOT NULL,
                conversation_id VARCHAR(255),
                project_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_updated_at ON contexts(updated_at)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_api_key_hash ON users(api_key_hash)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_records_tool ON cost_records(tool)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_records_project_id ON cost_records(project_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_records_created_at ON cost_records(created_at)
        """)
    
    async def execute_migration(self, sql: str) -> None:
        """Execute a migration SQL statement"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute(sql)
    
    async def begin_transaction(self):
        """Begin a database transaction"""
        if self.pool is None:
            await self.initialize()
        
        return self.pool.acquire()
    
    async def commit_transaction(self) -> None:
        """Commit the current transaction (handled by context manager)"""
        pass
    
    async def rollback_transaction(self) -> None:
        """Rollback the current transaction (handled by context manager)"""
        pass
    
    async def save_context(
        self,
        conversation_id: str,
        project_id: Optional[str],
        data: str,
        updated_at: int,
    ) -> None:
        """Save a conversation context"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO contexts (conversation_id, project_id, data, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (conversation_id) 
                DO UPDATE SET project_id = $2, data = $3, updated_at = $4
            """, conversation_id, project_id, data, updated_at)
    
    async def load_context(self, conversation_id: str) -> Optional[str]:
        """Load a conversation context by ID"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM contexts WHERE conversation_id = $1",
                conversation_id
            )
            
            if row:
                return row["data"]
            return None
    
    async def delete_context(self, conversation_id: str) -> None:
        """Delete a conversation context"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM contexts WHERE conversation_id = $1",
                conversation_id
            )
    
    async def list_contexts(
        self,
        project_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List conversation contexts"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            if project_id:
                rows = await conn.fetch("""
                    SELECT conversation_id, project_id, updated_at
                    FROM contexts
                    WHERE project_id = $1
                    ORDER BY updated_at DESC
                    LIMIT $2 OFFSET $3
                """, project_id, limit, offset)
            else:
                rows = await conn.fetch("""
                    SELECT conversation_id, project_id, updated_at
                    FROM contexts
                    ORDER BY updated_at DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            
            return [
                {
                    "conversation_id": row["conversation_id"],
                    "project_id": row["project_id"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        timestamp: int,
    ) -> int:
        """Add a message to a conversation"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO messages (conversation_id, role, content, timestamp)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, conversation_id, role, content, timestamp)
            
            return row["id"]
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            if limit:
                rows = await conn.fetch("""
                    SELECT id, role, content, timestamp
                    FROM messages
                    WHERE conversation_id = $1
                    ORDER BY timestamp ASC
                    LIMIT $2 OFFSET $3
                """, conversation_id, limit, offset)
            else:
                rows = await conn.fetch("""
                    SELECT id, role, content, timestamp
                    FROM messages
                    WHERE conversation_id = $1
                    ORDER BY timestamp ASC
                    OFFSET $2
                """, conversation_id, offset)
            
            return [
                {
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                }
                for row in rows
            ]
    
    async def create_user(
        self,
        user_id: str,
        username: str,
        email: Optional[str],
        password_hash: Optional[str],
        role: str = "user",
    ) -> None:
        """Create a new user"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (id, username, email, password_hash, role)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET
                    username = $2,
                    email = $3,
                    password_hash = $4,
                    role = $5,
                    updated_at = CURRENT_TIMESTAMP
            """, user_id, username, email, password_hash, role)
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, username, email, role, api_key_hash FROM users WHERE id = $1",
                user_id
            )
            
            if row:
                return {
                    "user_id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "role": row["role"],
                    "api_key_hash": row["api_key_hash"],
                }
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, username, email, password_hash, role, api_key_hash FROM users WHERE username = $1",
                username
            )
            
            if row:
                return {
                    "user_id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "role": row["role"],
                    "api_key_hash": row["api_key_hash"],
                }
            return None
    
    async def get_user_by_api_key_hash(self, api_key_hash: str) -> Optional[Dict[str, Any]]:
        """Get user by API key hash"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            # First try users table (legacy)
            row = await conn.fetchrow(
                "SELECT id, username, email, role FROM users WHERE api_key_hash = $1",
                api_key_hash
            )
            
            if row:
                return {
                    "user_id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "role": row["role"],
                }
            
            # Then try api_keys table
            row = await conn.fetchrow("""
                SELECT u.id, u.username, u.email, u.role
                FROM users u
                JOIN api_keys ak ON u.id = ak.user_id
                WHERE ak.key_hash = $1 AND ak.revoked_at IS NULL
                AND (ak.expires_at IS NULL OR ak.expires_at > EXTRACT(EPOCH FROM NOW())::BIGINT)
            """, api_key_hash)
            
            if row:
                return {
                    "user_id": row["id"],
                    "username": row["username"],
                    "email": row["email"],
                    "role": row["role"],
                }
            
            return None
    
    async def update_user_api_key_hash(
        self,
        user_id: str,
        api_key_hash: str,
    ) -> None:
        """Update user's API key hash"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET api_key_hash = $1, updated_at = CURRENT_TIMESTAMP
                WHERE id = $2
            """, api_key_hash, user_id)
    
    async def create_api_key(
        self,
        key_id: str,
        user_id: str,
        key_hash: str,
        name: Optional[str] = None,
        expires_at: Optional[int] = None,
    ) -> None:
        """Create an API key"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO api_keys (id, user_id, key_hash, name, expires_at)
                VALUES ($1, $2, $3, $4, $5)
            """, key_id, user_id, key_hash, name, expires_at)
    
    async def revoke_api_key(self, key_id: str) -> None:
        """Revoke an API key"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE api_keys SET revoked_at = CURRENT_TIMESTAMP WHERE id = $1
            """, key_id)
    
    async def get_api_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get API key by ID"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, user_id, key_hash, name, expires_at, created_at, revoked_at FROM api_keys WHERE id = $1",
                key_id
            )
            
            if row:
                return {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "key_hash": row["key_hash"],
                    "name": row["name"],
                    "expires_at": row["expires_at"],
                    "created_at": row["created_at"],
                    "revoked_at": row["revoked_at"],
                }
            return None
    
    async def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """List API keys for a user"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, key_hash, name, expires_at, created_at, revoked_at
                FROM api_keys
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, user_id)
            
            return [
                {
                    "id": row["id"],
                    "key_hash": row["key_hash"][:8] + "..." if row["key_hash"] else None,  # Partial hash for display
                    "name": row["name"],
                    "expires_at": row["expires_at"],
                    "created_at": row["created_at"],
                    "revoked_at": row["revoked_at"],
                    "is_active": row["revoked_at"] is None and (
                        row["expires_at"] is None or row["expires_at"] > int(datetime.now().timestamp())
                    ),
                }
                for row in rows
            ]
    
    async def log_audit_event(
        self,
        event_type: str,
        user_id: Optional[str],
        resource_type: Optional[str],
        resource_id: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        details: Optional[Dict[str, Any]],
    ) -> None:
        """Log an audit event"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit_logs (event_type, user_id, resource_type, resource_id, ip_address, user_agent, details)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, event_type, user_id, resource_type, resource_id, ip_address, user_agent, json.dumps(details) if details else None)
    
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get audit logs"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            conditions = []
            params = []
            param_idx = 1
            
            if user_id:
                conditions.append(f"user_id = ${param_idx}")
                params.append(user_id)
                param_idx += 1
            
            if event_type:
                conditions.append(f"event_type = ${param_idx}")
                params.append(event_type)
                param_idx += 1
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            params.extend([limit, offset])
            
            rows = await conn.fetch(f"""
                SELECT id, event_type, user_id, resource_type, resource_id, ip_address, user_agent, details, created_at
                FROM audit_logs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """, *params)
            
            return [
                {
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "user_id": row["user_id"],
                    "resource_type": row["resource_type"],
                    "resource_id": row["resource_id"],
                    "ip_address": row["ip_address"],
                    "user_agent": row["user_agent"],
                    "details": json.loads(row["details"]) if row["details"] else {},
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]
    
    async def record_cost(
        self,
        tool: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        conversation_id: Optional[str],
        project_id: Optional[str],
    ) -> None:
        """Record a cost entry"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO cost_records (tool, model, input_tokens, output_tokens, cost_usd, conversation_id, project_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, tool, model, input_tokens, output_tokens, cost_usd, conversation_id, project_id)
    
    async def get_costs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tool: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get cost entries"""
        if self.pool is None:
            await self.initialize()
        
        async with self.pool.acquire() as conn:
            conditions = []
            params = []
            param_idx = 1
            
            if start_date:
                conditions.append(f"created_at >= ${param_idx}")
                params.append(start_date)
                param_idx += 1
            
            if end_date:
                conditions.append(f"created_at <= ${param_idx}")
                params.append(end_date)
                param_idx += 1
            
            if tool:
                conditions.append(f"tool = ${param_idx}")
                params.append(tool)
                param_idx += 1
            
            if project_id:
                conditions.append(f"project_id = ${param_idx}")
                params.append(project_id)
                param_idx += 1
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            rows = await conn.fetch(f"""
                SELECT id, tool, model, input_tokens, output_tokens, cost_usd, conversation_id, project_id, created_at
                FROM cost_records
                {where_clause}
                ORDER BY created_at DESC
            """, *params)
            
            return [
                {
                    "id": row["id"],
                    "tool": row["tool"],
                    "model": row["model"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "cost_usd": float(row["cost_usd"]),
                    "conversation_id": row["conversation_id"],
                    "project_id": row["project_id"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]
    
    async def health_check(self) -> bool:
        """Check if the storage backend is healthy"""
        try:
            if self.pool is None:
                await self.initialize()
            
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close the storage backend connection"""
        if self.pool:
            await self.pool.close()
            self.pool = None
