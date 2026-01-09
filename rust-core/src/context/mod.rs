pub mod manager;
pub mod storage;
pub mod token_counter;
pub mod summarizer;
pub mod window;
pub mod compression;

pub use manager::ContextManager;
pub use storage::ContextStorage;

use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
    pub timestamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Context {
    pub conversation_id: String,
    pub project_id: Option<String>,
    pub messages: Vec<Message>,
    pub codebase_context: Option<CodebaseContext>,
    pub tool_history: Vec<ToolCall>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodebaseContext {
    pub relevant_files: Vec<String>,
    pub semantic_matches: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub tool: String,
    pub timestamp: i64,
    pub request: String,
    pub response: String,
}

impl Context {
    pub fn new(project_id: Option<String>) -> Self {
        Self {
            conversation_id: Uuid::new_v4().to_string(),
            project_id,
            messages: Vec::new(),
            codebase_context: None,
            tool_history: Vec::new(),
        }
    }

    pub fn add_message(&mut self, role: String, content: String) {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;
        
        self.messages.push(Message {
            role,
            content,
            timestamp,
        });
    }

    pub fn add_tool_call(&mut self, tool: String, request: String, response: String) {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;
        
        self.tool_history.push(ToolCall {
            tool,
            timestamp,
            request,
            response,
        });
    }
}
