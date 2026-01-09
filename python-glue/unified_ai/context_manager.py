"""Context manager for maintaining conversation history"""

import json
import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class Message:
    """A message in a conversation"""
    role: str
    content: str
    timestamp: int


@dataclass
class Context:
    """Context for a conversation"""
    conversation_id: str
    project_id: Optional[str]
    messages: List[Message]
    codebase_context: Optional[Dict[str, Any]]
    tool_history: List[Dict[str, Any]]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "conversation_id": self.conversation_id,
            "project_id": self.project_id,
            "messages": [asdict(msg) for msg in self.messages],
            "codebase_context": self.codebase_context,
            "tool_history": self.tool_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Context":
        """Create from dictionary"""
        messages = [
            Message(**msg) if isinstance(msg, dict) else msg
            for msg in data.get("messages", [])
        ]
        return cls(
            conversation_id=data["conversation_id"],
            project_id=data.get("project_id"),
            messages=messages,
            codebase_context=data.get("codebase_context"),
            tool_history=data.get("tool_history", []),
        )


class ContextManager:
    """Manages conversation context and history"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                conversation_id TEXT PRIMARY KEY,
                project_id TEXT,
                data TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES contexts(conversation_id)
            )
        """)

        conn.commit()
        conn.close()

    def get_or_create_context(
        self,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Context:
        """Get existing context or create new one"""
        if conversation_id:
            context = self.get_context(conversation_id)
            if context:
                return context

        # Create new context
        context = Context(
            conversation_id=conversation_id or str(uuid.uuid4()),
            project_id=project_id,
            messages=[],
            codebase_context=None,
            tool_history=[],
        )

        self.save_context(context)
        return context

    def get_context(self, conversation_id: str) -> Optional[Context]:
        """Get context by conversation ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT data FROM contexts WHERE conversation_id = ?",
            (conversation_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            data = json.loads(row[0])
            return Context.from_dict(data)

        return None

    def save_context(self, context: Context):
        """Save context to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        data = json.dumps(context.to_dict())
        updated_at = int(datetime.now().timestamp())

        cursor.execute("""
            INSERT OR REPLACE INTO contexts (conversation_id, project_id, data, updated_at)
            VALUES (?, ?, ?, ?)
        """, (context.conversation_id, context.project_id, data, updated_at))

        conn.commit()
        conn.close()

    def add_message(self, context: Context, role: str, content: str):
        """Add a message to the context"""
        timestamp = int(datetime.now().timestamp())
        message = Message(role=role, content=content, timestamp=timestamp)
        context.messages.append(message)
        self.save_context(context)

    def add_tool_call(
        self, context: Context, tool: str, request: str, response: str
    ):
        """Add a tool call to the history"""
        timestamp = int(datetime.now().timestamp())
        tool_call = {
            "tool": tool,
            "timestamp": timestamp,
            "request": request,
            "response": response,
        }
        context.tool_history.append(tool_call)
        self.save_context(context)
