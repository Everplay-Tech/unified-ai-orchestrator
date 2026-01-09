"""Python wrapper for Rust Router"""

from typing import Dict, List, Optional
from ..core import HAS_RUST_CORE

if HAS_RUST_CORE:
    try:
        import pyo3_bridge
        _PyRouter = pyo3_bridge.PyRouter
    except ImportError:
        _PyRouter = None
else:
    _PyRouter = None


class RustRouter:
    """Python wrapper for Rust Router"""
    
    def __init__(self, routing_rules: Dict[str, List[str]], default_tool: str):
        if not HAS_RUST_CORE or _PyRouter is None:
            raise RuntimeError("Rust core not available. Install with: cargo build --release")
        
        self._router = _PyRouter(routing_rules, default_tool)
    
    def route(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        explicit_tool: Optional[str] = None,
    ) -> Dict:
        """Route a request to appropriate tools"""
        import pyo3
        py = pyo3.Python::acquire_gil()
        
        request = {
            "message": message,
            "conversation_id": conversation_id,
            "project_id": project_id,
            "explicit_tool": explicit_tool,
        }
        
        return self._router.route(py, request)
