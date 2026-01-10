"""SQLite storage backend implementation"""

import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import aiosqlite

from .base import StorageBackend, StorageError


class SQLiteStorage(StorageBackend):
    """SQLite storage backend"""
    
    def __init__(self, db_path: Path):
        """
        Initialize SQLite storage backend
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def initialize(self) -> None:
        """Initialize the storage backend"""
        if self.connection is None:
            self.connection = await aiosqlite.connect(str(self.db_path))
            self.connection.row_factory = aiosqlite.Row
            await self._create_tables()
    
    async def _create_tables(self) -> None:
        """Create database tables"""
        if self.connection is None:
            await self.initialize()
        
        # Contexts table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                conversation_id TEXT PRIMARY KEY,
                project_id TEXT,
                data TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        # Messages table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (conversation_id) REFERENCES contexts(conversation_id) ON DELETE CASCADE
            )
        """)
        
        # Users table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                api_key_hash TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        # API keys table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key_hash TEXT NOT NULL UNIQUE,
                name TEXT,
                expires_at INTEGER,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                revoked_at INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Audit logs table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id TEXT,
                resource_type TEXT,
                resource_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                details TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        # Cost tracking table
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS cost_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                conversation_id TEXT,
                project_id TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        # Create indexes
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_updated_at ON contexts(updated_at)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_api_key_hash ON users(api_key_hash)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_records_tool ON cost_records(tool)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_records_project_id ON cost_records(project_id)
        """)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_records_created_at ON cost_records(created_at)
        """)
        
        await self.connection.commit()
    
    async def execute_migration(self, sql: str) -> None:
        """Execute a migration SQL statement"""
        if self.connection is None:
            await self.initialize()
        
        await self.connection.execute(sql)
        await self.connection.commit()
    
    async def begin_transaction(self):
        """Begin a database transaction"""
        if self.connection is None:
            await self.initialize()
        
        await self.connection.execute("BEGIN")
        return self
    
    async def commit_transaction(self) -> None:
        """Commit the current transaction"""
        if self.connection:
            await self.connection.commit()
    
    async def rollback_transaction(self) -> None:
        """Rollback the current transaction"""
        if self.connection:
            await self.connection.rollback()
    
    async def save_context(
        self,
        conversation_id: str,
        project_id: Optional[str],
        data: str,
        updated_at: int,
    ) -> None:
        """Save a conversation context"""
        if self.connection is None:
            await self.initialize()
        
        await self.connection.execute("""
            INSERT OR REPLACE INTO contexts (conversation_id, project_id, data, updated_at)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, project_id, data, updated_at))
        await self.connection.commit()
    
    async def load_context(self, conversation_id: str) -> Optional[str]:
        """Load a conversation context by ID"""
        if self.connection is None:
            await self.initialize()
        
        cursor = await self.connection.execute(
            "SELECT data FROM contexts WHERE conversation_id = ?",
            (conversation_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return row["data"]
        return None
    
    async def delete_context(self, conversation_id: str) -> None:
        """Delete a conversation context"""
        if self.connection is None:
            await self.initialize()
        
        await self.connection.execute(
            "DELETE FROM contexts WHERE conversation_id = ?",
            (conversation_id,)
        )
        await self.connection.commit()
    
    async def list_contexts(
        self,
        project_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List conversation contexts"""
        if self.connection is None:
            await self.initialize()
        
        if project_id:
            cursor = await self.connection.execute("""
                SELECT conversation_id, project_id, updated_at
                FROM contexts
                WHERE project_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (project_id, limit, offset))
        else:
            cursor = await self.connection.execute("""
                SELECT conversation_id, project_id, updated_at
                FROM contexts
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        rows = await cursor.fetchall()
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
        if self.connection is None:
            await self.initialize()
        
        cursor = await self.connection.execute("""
            INSERT INTO messages (conversation_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (conversation_id, role, content, timestamp))
        await self.connection.commit()
        return cursor.lastrowid
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        if self.connection is None:
            await self.initialize()
        
        if limit:
            cursor = await self.connection.execute("""
                SELECT id, role, content, timestamp
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
                LIMIT ? OFFSET ?
            """, (conversation_id, limit, offset))
        else:
            cursor = await self.connection.execute("""
                SELECT id, role, content, timestamp
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
                OFFSET ?
            """, (conversation_id, offset))
        
        rows = await cursor.fetchall()
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
        if self.connection is None:
            await self.initialize()
        
        await self.connection.execute("""
            INSERT OR REPLACE INTO users (id, username, email, password_hash, role, updated_at)
            VALUES (?, ?, ?, ?, ?, strftime('%s', 'now'))
        """, (user_id, username, email, password_hash, role))
        await self.connection.commit()
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        if self.connection is None:
            await self.initialize()
        
        cursor = await self.connection.execute(
            "SELECT id, username, email, role, api_key_hash FROM users WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
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
        if self.connection is None:
            await self.initialize()
        
        cursor = await self.connection.execute(
            "SELECT id, username, email, password_hash, role, api_key_hash FROM users WHERE username = ?",
            (username,)
        )
        row = await cursor.fetchone()
        
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
        if self.connection is None:
            await self.initialize()
        
        # First try users table (legacy)
        cursor = await self.connection.execute(
            "SELECT id, username, email, role FROM users WHERE api_key_hash = ?",
            (api_key_hash,)
        )
        row = await cursor.fetchone()
        
        if row:
            return {
                "user_id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "role": row["role"],
            }
        
        # Then try api_keys table
        cursor = await self.connection.execute("""
            SELECT u.id, u.username, u.email, u.role
            FROM users u
            JOIN api_keys ak ON u.id = ak.user_id
            WHERE ak.key_hash = ? AND ak.revoked_at IS NULL
            AND (ak.expires_at IS NULL OR ak.expires_at > strftime('%s', 'now'))
        """, (api_key_hash,))
        row = await cursor.fetchone()
        
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
        if self.connection is None:
            await self.initialize()
        
        await self.connection.execute("""
            UPDATE users SET api_key_hash = ?, updated_at = strftime('%s', 'now')
            WHERE id = ?
        """, (api_key_hash, user_id))
        await self.connection.commit()
    
    async def create_api_key(
        self,
        key_id: str,
        user_id: str,
        key_hash: str,
        name: Optional[str] = None,
        expires_at: Optional[int] = None,
    ) -> None:
        """Create an API key"""
        if self.connection is None:
            await self.initialize()
        
        await self.connection.execute("""
            INSERT INTO api_keys (id, user_id, key_hash, name, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (key_id, user_id, key_hash, name, expires_at))
        await self.connection.commit()
    
    async def revoke_api_key(self, key_id: str) -> None:
        """Revoke an API key"""
        if self.connection is None:
            await self.initialize()
        
        await self.connection.execute("""
            UPDATE api_keys SET revoked_at = strftime('%s', 'now') WHERE id = ?
        """, (key_id,))
        await self.connection.commit()
    
    async def get_api_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get API key by ID"""
        if self.connection is None:
            await self.initialize()
        
        cursor = await self.connection.execute(
            "SELECT id, user_id, key_hash, name, expires_at, created_at, revoked_at FROM api_keys WHERE id = ?",
            (key_id,)
        )
        row = await cursor.fetchone()
        
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
        if self.connection is None:
            await self.initialize()
        
        cursor = await self.connection.execute("""
            SELECT id, key_hash, name, expires_at, created_at, revoked_at
            FROM api_keys
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        
        current_timestamp = int(datetime.now().timestamp())
        
        return [
            {
                "id": row["id"],
                "key_hash": row["key_hash"][:8] + "..." if row["key_hash"] else None,  # Partial hash for display
                "name": row["name"],
                "expires_at": row["expires_at"],
                "created_at": row["created_at"],
                "revoked_at": row["revoked_at"],
                "is_active": row["revoked_at"] is None and (
                    row["expires_at"] is None or row["expires_at"] > current_timestamp
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
        if self.connection is None:
            await self.initialize()
        
        details_json = json.dumps(details) if details else None
        await self.connection.execute("""
            INSERT INTO audit_logs (event_type, user_id, resource_type, resource_id, ip_address, user_agent, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_type, user_id, resource_type, resource_id, ip_address, user_agent, details_json))
        await self.connection.commit()
    
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get audit logs"""
        if self.connection is None:
            await self.initialize()
        
        conditions = []
        params = []
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])
        
        cursor = await self.connection.execute(f"""
            SELECT id, event_type, user_id, resource_type, resource_id, ip_address, user_agent, details, created_at
            FROM audit_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params)
        
        rows = await cursor.fetchall()
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
                "created_at": datetime.fromtimestamp(row["created_at"]).isoformat() if row["created_at"] else None,
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
        if self.connection is None:
            await self.initialize()
        
        await self.connection.execute("""
            INSERT INTO cost_records (tool, model, input_tokens, output_tokens, cost_usd, conversation_id, project_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tool, model, input_tokens, output_tokens, cost_usd, conversation_id, project_id))
        await self.connection.commit()
    
    async def get_costs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tool: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get cost entries"""
        if self.connection is None:
            await self.initialize()
        
        conditions = []
        params = []
        
        if start_date:
            conditions.append("created_at >= ?")
            params.append(int(start_date.timestamp()))
        
        if end_date:
            conditions.append("created_at <= ?")
            params.append(int(end_date.timestamp()))
        
        if tool:
            conditions.append("tool = ?")
            params.append(tool)
        
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        cursor = await self.connection.execute(f"""
            SELECT id, tool, model, input_tokens, output_tokens, cost_usd, conversation_id, project_id, created_at
            FROM cost_records
            {where_clause}
            ORDER BY created_at DESC
        """, params)
        
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "tool": row["tool"],
                "model": row["model"],
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "cost_usd": row["cost_usd"],
                "conversation_id": row["conversation_id"],
                "project_id": row["project_id"],
                "created_at": datetime.fromtimestamp(row["created_at"]).isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
    
    async def health_check(self) -> bool:
        """Check if the storage backend is healthy"""
        try:
            if self.connection is None:
                await self.initialize()
            
            await self.connection.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close the storage backend connection"""
        if self.connection:
            await self.connection.close()
            self.connection = None
