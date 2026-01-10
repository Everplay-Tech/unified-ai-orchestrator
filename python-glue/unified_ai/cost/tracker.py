"""Cost tracking"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..storage import create_storage_backend, DatabaseType, StorageBackend
from ..config import load_config


class CostTracker:
    """Track API costs"""
    
    def __init__(self, storage_backend: Optional[StorageBackend] = None, config=None):
        """
        Initialize cost tracker
        
        Args:
            storage_backend: Optional storage backend instance
            config: Optional config instance (will load if not provided)
        """
        if config is None:
            config = load_config()
        
        self.config = config
        
        # Initialize storage backend
        if storage_backend:
            self.storage = storage_backend
        else:
            # Create storage backend from config
            db_type = DatabaseType(config.storage.db_type.lower())
            if db_type == DatabaseType.POSTGRESQL:
                if not config.storage.connection_string:
                    raise ValueError("PostgreSQL requires connection_string in config")
                self.storage = create_storage_backend(
                    db_type,
                    connection_string=config.storage.connection_string
                )
            else:
                self.storage = create_storage_backend(
                    db_type,
                    db_path=Path(config.storage.db_path)
                )
    
    async def initialize(self) -> None:
        """Initialize the storage backend"""
        await self.storage.initialize()
    
    async def record_cost(
        self,
        tool: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        """Record a cost entry"""
        await self.initialize()
        await self.storage.record_cost(
            tool=tool,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            conversation_id=conversation_id,
            project_id=project_id,
        )
    
    async def get_total_cost(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> float:
        """Get total cost for a period"""
        await self.initialize()
        
        costs = await self.storage.get_costs(
            start_date=start,
            end_date=end,
            project_id=project_id,
        )
        
        # Filter by user_id if provided (not stored in cost_records, would need to join)
        # For now, we'll return total for project_id
        total = sum(cost["cost_usd"] for cost in costs)
        return total
    
    async def get_costs(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        tool: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get cost entries"""
        await self.initialize()
        return await self.storage.get_costs(
            start_date=start,
            end_date=end,
            tool=tool,
            project_id=project_id,
        )
    
    async def close(self) -> None:
        """Close the storage backend connection"""
        await self.storage.close()
