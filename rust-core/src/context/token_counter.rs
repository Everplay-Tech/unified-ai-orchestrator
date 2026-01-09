/// Token counting utilities

use std::collections::HashMap;

/// Model context window sizes (approximate)
pub const MODEL_CONTEXT_WINDOWS: &[(&str, usize)] = &[
    ("gpt-4", 8192),
    ("gpt-4-turbo", 128000),
    ("gpt-4o", 128000),
    ("gpt-3.5-turbo", 16385),
    ("gpt-3.5-turbo-16k", 16385),
    ("claude-3-opus", 200000),
    ("claude-3-sonnet", 200000),
    ("claude-3-haiku", 200000),
    ("claude-3-5-sonnet", 200000),
];

pub struct TokenCounter {
    context_windows: HashMap<String, usize>,
}

impl TokenCounter {
    pub fn new() -> Self {
        let mut context_windows = HashMap::new();
        for (model, size) in MODEL_CONTEXT_WINDOWS {
            context_windows.insert(model.to_string(), *size);
        }
        Self { context_windows }
    }
    
    /// Get context window size for a model
    pub fn get_context_window(&self, model: &str) -> usize {
        self.context_windows
            .get(model)
            .copied()
            .unwrap_or(8192) // Default
    }
    
    /// Estimate token count (rough approximation: 1 token ≈ 4 characters)
    pub fn estimate_tokens(&self, text: &str) -> usize {
        text.chars().count() / 4
    }
    
    /// Check if text would exceed context window
    pub fn would_exceed_window(&self, text: &str, model: &str, reserved_tokens: usize) -> bool {
        let window = self.get_context_window(model);
        let estimated = self.estimate_tokens(text);
        estimated + reserved_tokens > window
    }
}

impl Default for TokenCounter {
    fn default() -> Self {
        Self::new()
    }
}
