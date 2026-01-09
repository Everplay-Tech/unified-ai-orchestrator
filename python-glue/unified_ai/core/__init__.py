"""Core Rust-Python bridge module"""

try:
    import pyo3_bridge
    HAS_RUST_CORE = True
except ImportError:
    HAS_RUST_CORE = False
    pyo3_bridge = None

if HAS_RUST_CORE:
    from .router import RustRouter
    from .context import RustContextManager
else:
    RustRouter = None
    RustContextManager = None

__all__ = [
    "HAS_RUST_CORE",
    "RustRouter",
    "RustContextManager",
]
