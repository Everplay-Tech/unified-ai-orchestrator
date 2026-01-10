/// PyO3 bindings for database migrations

use pyo3::prelude::*;
use pyo3_asyncio::tokio::into_future;
use rust_core::migrations::MigrationRunner;
use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};

#[pyclass]
pub struct PyMigrationRunner {
    pool: SqlitePool,
    runtime: std::sync::Mutex<tokio::runtime::Runtime>,
}

#[pymethods]
impl PyMigrationRunner {
    #[new]
    fn new(db_path: String) -> PyResult<Self> {
        Python::with_gil(|py| {
            py.allow_threads(|| {
                let rt = tokio::runtime::Runtime::new()
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to create runtime: {}", e)
                    ))?;
                
                let pool = rt.block_on(async {
                    SqlitePoolOptions::new()
                        .max_connections(5)
                        .connect_with(
                            sqlx::sqlite::SqliteConnectOptions::new()
                                .filename(&db_path)
                                .create_if_missing(true),
                        )
                        .await
                })
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create pool: {}", e)
                ))?;
                
                Ok(Self {
                    pool,
                    runtime: std::sync::Mutex::new(rt),
                })
            })
        })
    }
    
    fn migrate_up(&mut self, py: Python, target_version: Option<u32>) -> PyResult<()> {
        let pool = self.pool.clone();
        
        py.allow_threads(|| {
            let rt = self.runtime.lock().unwrap();
            rt.block_on(async {
                let mut runner = MigrationRunner::new(pool);
                rust_core::migrations::register_migrations(&mut runner);
                runner.migrate_up(target_version).await
            })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Migration failed: {}", e)
            ))
        })
    }
    
    fn migrate_down(&mut self, py: Python, target_version: u32) -> PyResult<()> {
        let pool = self.pool.clone();
        
        py.allow_threads(|| {
            let rt = self.runtime.lock().unwrap();
            rt.block_on(async {
                let mut runner = MigrationRunner::new(pool);
                rust_core::migrations::register_migrations(&mut runner);
                runner.migrate_down(target_version).await
            })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Rollback failed: {}", e)
            ))
        })
    }
    
    fn status(&self, py: Python) -> PyResult<Vec<(u32, String, bool)>> {
        let pool = self.pool.clone();
        
        py.allow_threads(|| {
            let rt = self.runtime.lock().unwrap();
            rt.block_on(async {
                let mut runner = MigrationRunner::new(pool);
                rust_core::migrations::register_migrations(&mut runner);
                runner.status().await
            })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Status check failed: {}", e)
            ))
        })
    }
}
