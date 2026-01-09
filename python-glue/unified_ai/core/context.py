"""Python wrapper for Rust ContextManager"""

from typing import Optional, Dict
from pathlib import Path
from ..core import HAS_RUST_CORE

if HAS_RUST_CORE:
    try:
        import pyo3_bridge
        _PyContextManager = pyo3_bridge.PyContextManager
    except ImportError:
        _PyContextManager = None
else:
    _PyContextManager = None


class RustContextManager:
    """Python wrapper for Rust ContextManager"""
    
    def __init__(self, db_path: Path):
        if not HAS_RUST_CORE or _PyContextManager is None:
            raise RuntimeError("Rust core not available. Install with: cargo build --release")
        
        self._manager = _PyContextManager(str(db_path))
    
    def get_or_create_context(
        self,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict:
        """Get or create a conversation context"""
        import pyo3
        py = pyo3.Python::acquire_gil()
        return self._manager.get_or_create_context(py, conversation_id, project_id)
    
    def update_context(self, context: Dict) -> None:
        """Update a conversation context"""
        import pyo3
        py = pyo3.Python::acquire_gil()
        self._manager.update_context(py, context)
