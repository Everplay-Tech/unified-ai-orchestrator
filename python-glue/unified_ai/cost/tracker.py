"""Cost tracking"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import sqlite3


class CostTracker:
    """Track API costs"""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize cost tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                timestamp INTEGER NOT NULL,
                user_id TEXT,
                project_id TEXT,
                conversation_id TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_records(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cost_tool ON cost_records(tool)
        """)
        
        conn.commit()
        conn.close()
    
    def record_cost(
        self,
        tool: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ):
        """Record a cost entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = int(datetime.now().timestamp())
        
        cursor.execute("""
            INSERT INTO cost_records 
            (tool, model, input_tokens, output_tokens, cost_usd, timestamp, user_id, project_id, conversation_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tool, model, input_tokens, output_tokens, cost_usd,
            timestamp, user_id, project_id, conversation_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_total_cost(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> float:
        """Get total cost for a period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT SUM(cost_usd) FROM cost_records WHERE 1=1"
        params = []
        
        if start:
            query += " AND timestamp >= ?"
            params.append(int(start.timestamp()))
        
        if end:
            query += " AND timestamp <= ?"
            params.append(int(end.timestamp()))
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else 0.0
