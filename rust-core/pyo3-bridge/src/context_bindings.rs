use pyo3::prelude::*;
use pyo3::types::PyDict;
use rust_core::context::{ContextManager, ContextStorage, Context};
use rust_core::context::window::ContextWindowManager;
use rust_core::context::compression::ContextCompressor;
use rust_core::error::Result;
use std::path::PathBuf;
use pyo3_asyncio::tokio::future_into_py;

#[pyclass]
pub struct PyContextManager {
    inner: ContextManager,
    runtime: std::sync::Mutex<tokio::runtime::Runtime>,
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
                
                let storage = rt.block_on(async {
                    ContextStorage::new(path).await
                        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                            format!("Failed to create storage: {}", e)
                        ))
                })?;
                
                Ok(Self {
                    inner: ContextManager::new(storage),
                    runtime: std::sync::Mutex::new(rt),
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
        // Perform async operation without GIL
        let context = py.allow_threads(|| {
            let rt = self.runtime.lock().unwrap();
            rt.block_on(async {
                self.inner.get_or_create_context(conversation_id, project_id).await
            })
        })
        .map_err(|e: rust_core::error::Error| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            format!("Failed to get or create context: {}", e)
        ))?;
        
        // Now create Python objects while holding the GIL
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
    }

    fn update_context(&self, py: Python, context_dict: &PyDict) -> PyResult<()> {
        // Extract all data from Python dict while holding the GIL
        let conversation_id: String = context_dict
            .get_item("conversation_id")?
            .and_then(|v| v.extract().ok())
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing conversation_id"))?;
        
        let project_id: Option<String> = context_dict.get_item("project_id")
            .and_then(|v| v.extract::<Option<String>>().ok());
        
        // Extract messages if provided
        let mut messages_to_add: Vec<(String, String)> = Vec::new();
        if let Some(messages) = context_dict.get_item("messages") {
            if let Ok(msg_list) = messages.downcast::<pyo3::types::PyList>() {
                for msg_item in msg_list.iter() {
                    if let Ok(msg_dict) = msg_item.downcast::<PyDict>() {
                        let role: String = msg_dict.get_item("role")?.extract()?;
                        let content: String = msg_dict.get_item("content")?.extract()?;
                        messages_to_add.push((role, content));
                    }
                }
            }
        }
        
        // Now perform async operations without GIL
        py.allow_threads(|| {
            let rt = self.runtime.lock().unwrap();
            rt.block_on(async {
                // Load existing context
                let mut context = self.inner.get_or_create_context(
                    Some(conversation_id.clone()),
                    None,
                ).await
                .map_err(|e: rust_core::error::Error| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to get context: {}", e)
                ))?;
                
                // Update from extracted data
                if let Some(pid) = project_id {
                    context.project_id = Some(pid);
                }
                
                // Add messages
                for (role, content) in messages_to_add {
                    context.add_message(role, content);
                }
                
                self.inner.update_context(&context).await
                    .map_err(|e: rust_core::error::Error| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        format!("Failed to update context: {}", e)
                    ))
            })
        })
    }
}

#[pyclass]
pub struct PyContextWindowManager {
    inner: ContextWindowManager,
}

#[pymethods]
impl PyContextWindowManager {
    #[new]
    fn new(reserved_tokens: Option<usize>) -> Self {
        Self {
            inner: ContextWindowManager::new(reserved_tokens.unwrap_or(1000)),
        }
    }
    
    fn manage_context(&self, py: Python, context_dict: &PyDict, model: String) -> PyResult<PyDict> {
        // Convert Python dict to Rust Context
        let mut context = dict_to_context(context_dict)?;
        
        // Manage context window
        self.inner.manage_context(&mut context, &model);
        
        // Convert back to Python dict
        context_to_dict(py, &context)
    }
    
    fn manage_context_with_reserved(&self, py: Python, context_dict: &PyDict, model: String, reserved_tokens: usize) -> PyResult<PyDict> {
        // Create window manager with custom reserved tokens
        let manager = ContextWindowManager::new(reserved_tokens);
        
        // Convert Python dict to Rust Context
        let mut context = dict_to_context(context_dict)?;
        
        // Manage context window
        manager.manage_context(&mut context, &model);
        
        // Convert back to Python dict
        context_to_dict(py, &context)
    }
}

#[pyclass]
pub struct PyContextCompressor {
    inner: ContextCompressor,
}

#[pymethods]
impl PyContextCompressor {
    #[new]
    fn new() -> Self {
        Self {
            inner: ContextCompressor::default(),
        }
    }
    
    fn compress(&self, py: Python, context_dict: &PyDict) -> PyResult<PyDict> {
        // Convert Python dict to Rust Context
        let mut context = dict_to_context(context_dict)?;
        
        // Compress context
        self.inner.compress(&mut context);
        
        // Convert back to Python dict
        context_to_dict(py, &context)
    }
}

// Helper functions to convert between Python dicts and Rust Context
fn dict_to_context(dict: &PyDict) -> PyResult<Context> {
    let conversation_id: String = dict.get_item("conversation_id")?
        .and_then(|v| v.extract().ok())
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing conversation_id"))?;
    
    let project_id: Option<String> = dict.get_item("project_id")
        .and_then(|v| v.extract::<Option<String>>().ok());
    
    let mut context = Context::new(project_id);
    context.conversation_id = conversation_id;
    
    // Deserialize messages
    if let Some(messages) = dict.get_item("messages") {
        if let Ok(msg_list) = messages.downcast::<pyo3::types::PyList>() {
            for msg_item in msg_list.iter() {
                if let Ok(msg_dict) = msg_item.downcast::<PyDict>() {
                    let role: String = msg_dict.get_item("role")?.extract()?;
                    let content: String = msg_dict.get_item("content")?.extract()?;
                    let timestamp: i64 = msg_dict.get_item("timestamp")
                        .and_then(|v| v.extract().ok())
                        .unwrap_or(0);
                    
                    context.messages.push(rust_core::context::Message {
                        role,
                        content,
                        timestamp,
                    });
                }
            }
        }
    }
    
    // Deserialize codebase context if present
    if let Some(cb_dict) = dict.get_item("codebase_context") {
        if let Ok(cb_dict) = cb_dict.downcast::<PyDict>() {
            let relevant_files: Vec<String> = cb_dict.get_item("relevant_files")
                .and_then(|v| v.extract().ok())
                .unwrap_or_default();
            let semantic_matches: Vec<String> = cb_dict.get_item("semantic_matches")
                .and_then(|v| v.extract().ok())
                .unwrap_or_default();
            
            context.codebase_context = Some(rust_core::context::CodebaseContext {
                relevant_files,
                semantic_matches,
            });
        }
    }
    
    // Deserialize tool history
    if let Some(tool_history) = dict.get_item("tool_history") {
        if let Ok(tool_history_list) = tool_history.downcast::<pyo3::types::PyList>() {
            for tc_item in tool_history_list.iter() {
                if let Ok(tc_dict) = tc_item.downcast::<PyDict>() {
                    let tool: String = tc_dict.get_item("tool")
                        .and_then(|v| v.extract().ok())
                        .unwrap_or_default();
                    let timestamp: i64 = tc_dict.get_item("timestamp")
                        .and_then(|v| v.extract().ok())
                        .unwrap_or(0);
                    let request: String = tc_dict.get_item("request")
                        .and_then(|v| v.extract().ok())
                        .unwrap_or_default();
                    let response: String = tc_dict.get_item("response")
                        .and_then(|v| v.extract().ok())
                        .unwrap_or_default();
                    
                    context.tool_history.push(rust_core::context::ToolCall {
                        tool,
                        timestamp,
                        request,
                        response,
                    });
                }
            }
        }
    }
    
    Ok(context)
}

fn context_to_dict(py: Python, context: &Context) -> PyResult<PyDict> {
    let result = PyDict::new(py);
    result.set_item("conversation_id", &context.conversation_id)?;
    result.set_item("project_id", context.project_id.as_ref())?;
    
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
    
    // Serialize codebase context if present
    if let Some(ref cb_ctx) = context.codebase_context {
        let cb_dict = PyDict::new(py);
        cb_dict.set_item("relevant_files", &cb_ctx.relevant_files)?;
        cb_dict.set_item("semantic_matches", &cb_ctx.semantic_matches)?;
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
}
