use pyo3::prelude::*;

mod router_bindings;
mod context_bindings;
mod migration_bindings;
mod indexer_bindings;

use router_bindings::PyRouter;
use context_bindings::PyContextManager;
use migration_bindings::PyMigrationRunner;
use indexer_bindings::{PyCodebaseIndexer, PySemanticSearch};

#[pymodule]
fn pyo3_bridge(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyRouter>()?;
    m.add_class::<PyContextManager>()?;
    m.add_class::<PyMigrationRunner>()?;
    m.add_class::<PyCodebaseIndexer>()?;
    m.add_class::<PySemanticSearch>()?;
    
    // Initialize observability
    rust_core::observability::setup_logging();
    
    Ok(())
}
