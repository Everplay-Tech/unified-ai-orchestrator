/// PyO3 bindings for codebase indexer

use pyo3::prelude::*;
use rust_core::indexer::codebase::CodebaseIndexer;
use rust_core::indexer::search::SemanticSearch;
use rust_core::indexer::storage::IndexStorage;
use rust_core::indexer::watcher::FileWatcher;
use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::Mutex;

#[pyclass]
pub struct PyCodebaseIndexer {
    indexer: CodebaseIndexer,
}

#[pymethods]
impl PyCodebaseIndexer {
    #[new]
    fn new(project_id: String, db_path: String) -> PyResult<Self> {
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
                
                let storage = IndexStorage::new(pool);
                let indexer = CodebaseIndexer::new(project_id, storage);
                
                Ok(Self { indexer })
            })
        })
    }
    
    fn index_directory(&mut self, py: Python, root_path: String) -> PyResult<usize> {
        let indexer = &mut self.indexer;
        let path = PathBuf::from(root_path);
        
        py.allow_threads(|| {
            let rt = tokio::runtime::Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create runtime: {}", e)
                ))?;
            
            rt.block_on(async {
                indexer.index_directory(&path).await
            })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Indexing failed: {}", e)
            ))
        })
    }
    
    fn index_file(&mut self, py: Python, file_path: String) -> PyResult<()> {
        let indexer = &mut self.indexer;
        let path = PathBuf::from(file_path);
        
        py.allow_threads(|| {
            let rt = tokio::runtime::Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create runtime: {}", e)
                ))?;
            
            rt.block_on(async {
                indexer.index_file(&path).await
            })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("File indexing failed: {}", e)
            ))
        })
    }
    
    fn update_file(&mut self, py: Python, file_path: String) -> PyResult<()> {
        let indexer = &mut self.indexer;
        let path = PathBuf::from(file_path);
        
        py.allow_threads(|| {
            let rt = tokio::runtime::Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create runtime: {}", e)
                ))?;
            
            rt.block_on(async {
                indexer.update_file(&path).await
            })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("File update failed: {}", e)
            ))
        })
    }
    
    fn remove_file(&mut self, py: Python, file_path: String) -> PyResult<()> {
        let indexer = &mut self.indexer;
        let path = PathBuf::from(file_path);
        
        py.allow_threads(|| {
            let rt = tokio::runtime::Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create runtime: {}", e)
                ))?;
            
            rt.block_on(async {
                indexer.remove_file(&path).await
            })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("File removal failed: {}", e)
            ))
        })
    }
}

#[pyclass]
pub struct PySemanticSearch {
    search: SemanticSearch,
}

#[pymethods]
impl PySemanticSearch {
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
                
                let storage = IndexStorage::new(pool);
                let search = SemanticSearch::new(storage);
                
                Ok(Self { search })
            })
        })
    }
    
    fn search(&self, py: Python, project_id: String, query: String, limit: usize) -> PyResult<Vec<(String, String, Option<String>, usize, usize, f32)>> {
        let search = &self.search;
        
        py.allow_threads(|| {
            let rt = tokio::runtime::Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create runtime: {}", e)
                ))?;
            
            rt.block_on(async {
                let results = search.search(&project_id, &query, limit).await
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Search error: {}", e)
                    ))?;
                Ok(results.into_iter().map(|r| {
                    (r.file_path, r.block_type, r.name, r.start_line, r.end_line, r.score)
                }).collect())
            })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Search failed: {}", e)
            ))
        })
    }
}

#[pyclass]
pub struct PyFileWatcher {
    watcher: Arc<Mutex<FileWatcher>>,
}

#[pymethods]
impl PyFileWatcher {
    #[new]
    fn new(project_id: String, db_path: String) -> PyResult<Self> {
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
                        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                            format!("Failed to create pool: {}", e)
                        ))
                })?;
                
                let storage = IndexStorage::new(pool);
                let indexer = CodebaseIndexer::new(project_id, storage);
                let watcher = FileWatcher::new(indexer)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to create watcher: {}", e)
                    ))?;
                
                Ok(Self {
                    watcher: Arc::new(Mutex::new(watcher)),
                })
            })
        })
    }
    
    fn watch(&self, py: Python, path: String) -> PyResult<()> {
        let watcher = self.watcher.clone();
        let path_buf = PathBuf::from(path);
        
        py.allow_threads(|| {
            let rt = tokio::runtime::Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create runtime: {}", e)
                ))?;
            
            rt.block_on(async {
                let mut w = watcher.lock().await;
                w.watch(path_buf)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to watch path: {}", e)
                    ))
            })
        })
    }
    
    fn start(&self, py: Python) -> PyResult<()> {
        let watcher = self.watcher.clone();
        
        // Start processing events in background
        py.allow_threads(|| {
            let rt = tokio::runtime::Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create runtime: {}", e)
                ))?;
            
            rt.spawn(async move {
                let mut w = watcher.lock().await;
                if let Err(e) = w.process_events().await {
                    eprintln!("File watcher error: {}", e);
                }
            });
            
            Ok(())
        })
    }
    
    fn stop(&self, py: Python) -> PyResult<()> {
        let watcher = self.watcher.clone();
        
        py.allow_threads(|| {
            let rt = tokio::runtime::Runtime::new()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create runtime: {}", e)
                ))?;
            
            rt.block_on(async {
                let mut w = watcher.lock().await;
                w.stop()
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to stop watcher: {}", e)
                    ))
            })
        })
    }
}
