pub mod merge;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResponse {
    pub tool: String,
    pub content: String,
    pub metadata: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComposedResponse {
    pub content: String,
    pub sources: Vec<String>,
    pub metadata: Option<serde_json::Value>,
}

pub struct Composer;

impl Composer {
    pub fn compose(responses: Vec<ToolResponse>) -> ComposedResponse {
        merge::merge_responses(responses)
    }
}
