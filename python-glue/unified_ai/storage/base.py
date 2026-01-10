"""Base storage interface"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class StorageError(Exception):
    """Storage operation error"""
    pass


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend (create tables, etc.)"""
        pass
    
    @abstractmethod
    async def execute_migration(self, sql: str) -> None:
        """Execute a migration SQL statement"""
        pass
    
    @abstractmethod
    async def begin_transaction(self):
        """Begin a database transaction"""
        pass
    
    @abstractmethod
    async def commit_transaction(self) -> None:
        """Commit the current transaction"""
        pass
    
    @abstractmethod
    async def rollback_transaction(self) -> None:
        """Rollback the current transaction"""
        pass
    
    # Context operations
    @abstractmethod
    async def save_context(
        self,
        conversation_id: str,
        project_id: Optional[str],
        data: str,
        updated_at: int,
    ) -> None:
        """Save a conversation context"""
        pass
    
    @abstractmethod
    async def load_context(self, conversation_id: str) -> Optional[str]:
        """Load a conversation context by ID"""
        pass
    
    @abstractmethod
    async def delete_context(self, conversation_id: str) -> None:
        """Delete a conversation context"""
        pass
    
    @abstractmethod
    async def list_contexts(
        self,
        project_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List conversation contexts"""
        pass
    
    # Message operations
    @abstractmethod
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        timestamp: int,
    ) -> int:
        """Add a message to a conversation"""
        pass
    
    @abstractmethod
    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        pass
    
    # User operations
    @abstractmethod
    async def create_user(
        self,
        user_id: str,
        username: str,
        email: Optional[str],
        password_hash: Optional[str],
        role: str = "user",
    ) -> None:
        """Create a new user"""
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        pass
    
    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        pass
    
    @abstractmethod
    async def get_user_by_api_key_hash(self, api_key_hash: str) -> Optional[Dict[str, Any]]:
        """Get user by API key hash"""
        pass
    
    @abstractmethod
    async def update_user_api_key_hash(
        self,
        user_id: str,
        api_key_hash: str,
    ) -> None:
        """Update user's API key hash"""
        pass
    
    # API key operations
    @abstractmethod
    async def create_api_key(
        self,
        key_id: str,
        user_id: str,
        key_hash: str,
        name: Optional[str] = None,
        expires_at: Optional[int] = None,
    ) -> None:
        """Create an API key"""
        pass
    
    @abstractmethod
    async def revoke_api_key(self, key_id: str) -> None:
        """Revoke an API key"""
        pass
    
    @abstractmethod
    async def get_api_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get API key by ID"""
        pass
    
    @abstractmethod
    async def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """List API keys for a user"""
        pass
    
    # Audit log operations
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get audit logs"""
        pass
    
    # Cost tracking operations
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def get_costs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tool: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get cost entries"""
        pass
    
    # Health check
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the storage backend is healthy"""
        pass
    
    # Close connection
    @abstractmethod
    async def close(self) -> None:
        """Close the storage backend connection"""
        pass
