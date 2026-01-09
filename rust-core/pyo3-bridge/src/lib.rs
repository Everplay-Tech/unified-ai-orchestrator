use pyo3::prelude::*;

mod router_bindings;
mod context_bindings;

use router_bindings::PyRouter;
use context_bindings::PyContextManager;

#[pymodule]
fn pyo3_bridge(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyRouter>()?;
    m.add_class::<PyContextManager>()?;
    
    // Initialize observability
    rust_core::observability::setup_logging();
    
    Ok(())
}
