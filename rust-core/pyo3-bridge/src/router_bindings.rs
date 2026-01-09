use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rust_core::router::{Router, RoutingRequest, RoutingDecision};
use std::collections::HashMap;

#[pyclass]
pub struct PyRouter {
    inner: Router,
}

#[pymethods]
impl PyRouter {
    #[new]
    fn new(routing_rules: HashMap<String, Vec<String>>, default_tool: String) -> Self {
        Self {
            inner: Router::new(routing_rules, default_tool),
        }
    }

    fn route(&self, py: Python, request: &PyDict) -> PyResult<PyDict> {
        let message: String = request
            .get_item("message")?
            .and_then(|v| v.extract().ok())
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing message"))?;
        
        let conversation_id: Option<String> = request
            .get_item("conversation_id")
            .and_then(|v| v.extract().ok());
        
        let project_id: Option<String> = request
            .get_item("project_id")
            .and_then(|v| v.extract().ok());
        
        let explicit_tool: Option<String> = request
            .get_item("explicit_tool")
            .and_then(|v| v.extract().ok());

        let routing_request = RoutingRequest {
            message,
            conversation_id,
            project_id,
            explicit_tool,
        };

        let decision = self.inner.route(&routing_request);
        
        let result = PyDict::new(py);
        let tools_list = PyList::new(py, decision.selected_tools.iter());
        result.set_item("selected_tools", tools_list)?;
        result.set_item("reasoning", decision.reasoning)?;
        Ok(result)
    }
}
