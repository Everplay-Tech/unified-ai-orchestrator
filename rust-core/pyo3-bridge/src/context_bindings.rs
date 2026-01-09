use pyo3::prelude::*;
use pyo3::types::PyDict;
use rust_core::context::{ContextManager, ContextStorage, Context};
use rust_core::error::Result;
use std::path::PathBuf;
use pyo3_asyncio::tokio::future_into_py;

#[pyclass]
pub struct PyContextManager {
    inner: ContextManager,
}

#[pymethods]
impl PyContextManager {
    #[new]
    fn new(db_path: String) -> PyResult<Self> {
        let path = PathBuf::from(db_path);
        Python::with_gil(|py| {
            py.allow_threads(|| {
                let rt = tokio::runtime::Runtime::new()
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to create runtime: {}", e)
                    ))?;
                
                rt.block_on(async {
                    let storage = ContextStorage::new(path).await
                        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                            format!("Failed to create storage: {}", e)
                        ))?;
                    Ok(Self {
                        inner: ContextManager::new(storage),
                    })
                })
            })
        })
    }

    fn get_or_create_context<'p>(
        &self,
        py: Python<'p>,
        conversation_id: Option<String>,
        project_id: Option<String>,
    ) -> PyResult<&'p PyDict> {
        Python::with_gil(|_py| {
            py.allow_threads(|| {
                let rt = tokio::runtime::Runtime::new()
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to create runtime: {}", e)
                    ))?;
                
                rt.block_on(async {
                    let context = self.inner.get_or_create_context(conversation_id, project_id).await
                        .map_err(|e| PyErr::from(e))?;
                    
                    let result = PyDict::new(py);
                    result.set_item("conversation_id", context.conversation_id)?;
                    result.set_item("project_id", context.project_id)?;
                    
                    // Serialize messages
                    let messages: Vec<PyDict> = context.messages.iter().map(|msg| {
                        let msg_dict = PyDict::new(py);
                        msg_dict.set_item("role", &msg.role).unwrap();
                        msg_dict.set_item("content", &msg.content).unwrap();
                        msg_dict.set_item("timestamp", msg.timestamp).unwrap();
                        msg_dict
                    }).collect();
                    let messages_list = pyo3::types::PyList::new(py, messages);
                    result.set_item("messages", messages_list)?;
                    
                    // Serialize codebase context
                    if let Some(cb_ctx) = context.codebase_context {
                        let cb_dict = PyDict::new(py);
                        cb_dict.set_item("relevant_files", cb_ctx.relevant_files)?;
                        cb_dict.set_item("semantic_matches", cb_ctx.semantic_matches)?;
                        result.set_item("codebase_context", cb_dict)?;
                    }
                    
                    // Serialize tool history
                    let tool_history: Vec<PyDict> = context.tool_history.iter().map(|tc| {
                        let tc_dict = PyDict::new(py);
                        tc_dict.set_item("tool", &tc.tool).unwrap();
                        tc_dict.set_item("timestamp", tc.timestamp).unwrap();
                        tc_dict.set_item("request", &tc.request).unwrap();
                        tc_dict.set_item("response", &tc.response).unwrap();
                        tc_dict
                    }).collect();
                    let tool_history_list = pyo3::types::PyList::new(py, tool_history);
                    result.set_item("tool_history", tool_history_list)?;
                    
                    Ok(result)
                })
            })
        })
    }

    fn update_context(&self, py: Python, context_dict: &PyDict) -> PyResult<()> {
        // Deserialize context from Python dict and update
        Python::with_gil(|_py| {
            py.allow_threads(|| {
                let rt = tokio::runtime::Runtime::new()
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to create runtime: {}", e)
                    ))?;
                
                rt.block_on(async {
                    let conversation_id: String = context_dict
                        .get_item("conversation_id")?
                        .and_then(|v| v.extract().ok())
                        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing conversation_id"))?;
                    
                    // Load existing context
                    let mut context = self.inner.get_or_create_context(
                        Some(conversation_id.clone()),
                        None,
                    ).await
                    .map_err(|e| PyErr::from(e))?;
                    
                    // Update from dict
                    if let Some(project_id) = context_dict.get_item("project_id")
                        .and_then(|v| v.extract::<Option<String>>().ok()) {
                        context.project_id = project_id;
                    }
                    
                    // Update messages if provided
                    if let Some(messages) = context_dict.get_item("messages") {
                        if let Ok(msg_list) = messages.downcast::<pyo3::types::PyList>() {
                            for msg_item in msg_list.iter() {
                                if let Ok(msg_dict) = msg_item.downcast::<PyDict>() {
                                    let role: String = msg_dict.get_item("role")?.extract()?;
                                    let content: String = msg_dict.get_item("content")?.extract()?;
                                    context.add_message(role, content);
                                }
                            }
                        }
                    }
                    
                    self.inner.update_context(&context).await
                        .map_err(|e| PyErr::from(e))?;
                    
                    Ok(())
                })
            })
        })
    }
}
