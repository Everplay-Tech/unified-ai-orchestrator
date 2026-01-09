pub mod analyzer;
pub mod selector;

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingRequest {
    pub message: String,
    pub conversation_id: Option<String>,
    pub project_id: Option<String>,
    pub explicit_tool: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingDecision {
    pub selected_tools: Vec<String>,
    pub reasoning: String,
}

pub struct Router {
    routing_rules: HashMap<String, Vec<String>>,
    default_tool: String,
}

impl Router {
    pub fn new(routing_rules: HashMap<String, Vec<String>>, default_tool: String) -> Self {
        Self {
            routing_rules,
            default_tool,
        }
    }

    pub fn route(&self, request: &RoutingRequest) -> RoutingDecision {
        // If explicit tool requested, use it
        if let Some(tool) = &request.explicit_tool {
            return RoutingDecision {
                selected_tools: vec![tool.clone()],
                reasoning: format!("Explicit tool selection: {}", tool),
            };
        }

        // Analyze request to determine task type
        let task_type = analyzer::analyze_request(&request.message);
        
        // Select tools based on task type
        let tools = selector::select_tools(&task_type, &self.routing_rules, &self.default_tool);
        
        RoutingDecision {
            selected_tools: tools.clone(),
            reasoning: format!("Task type: {:?}, Selected tools: {:?}", task_type, tools),
        }
    }
}
