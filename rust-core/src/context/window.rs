/// Context window management

use crate::context::{Context, Message};
use crate::context::token_counter::TokenCounter;
use crate::context::summarizer::ContextSummarizer;

pub struct ContextWindowManager {
    token_counter: TokenCounter,
    summarizer: ContextSummarizer,
    reserved_tokens: usize, // Reserve tokens for response
}

impl ContextWindowManager {
    pub fn new(reserved_tokens: usize) -> Self {
        Self {
            token_counter: TokenCounter::new(),
            summarizer: ContextSummarizer::default(),
            reserved_tokens,
        }
    }
    
    /// Manage context window for a model
    pub fn manage_context(&self, context: &mut Context, model: &str) {
        // First, try summarization if needed
        self.summarizer.summarize_if_needed(context);
        
        // Then check token limits
        let window_size = self.token_counter.get_context_window(model);
        let current_tokens = self.estimate_context_tokens(context);
        
        if current_tokens + self.reserved_tokens > window_size {
            // Need to truncate
            self.truncate_context(context, model, window_size);
        }
    }
    
    /// Estimate total tokens in context
    fn estimate_context_tokens(&self, context: &Context) -> usize {
        let mut total = 0;
        
        for message in &context.messages {
            total += self.token_counter.estimate_tokens(&message.content);
            total += 4; // Overhead per message
        }
        
        total
    }
    
    /// Truncate context to fit within window
    fn truncate_context(&self, context: &mut Context, model: &str, window_size: usize) {
        let available_tokens = window_size - self.reserved_tokens;
        
        // Keep system messages and recent messages
        let mut kept_messages = Vec::new();
        let mut token_count = 0;
        
        // First, keep all system messages
        for message in &context.messages {
            if message.role == "system" {
                let tokens = self.token_counter.estimate_tokens(&message.content) + 4;
                if token_count + tokens <= available_tokens {
                    kept_messages.push(message.clone());
                    token_count += tokens;
                }
            }
        }
        
        // Then, keep recent messages (in reverse order)
        for message in context.messages.iter().rev() {
            if message.role == "system" {
                continue; // Already added
            }
            
            let tokens = self.token_counter.estimate_tokens(&message.content) + 4;
            if token_count + tokens <= available_tokens {
                kept_messages.insert(kept_messages.len() - kept_messages.iter().filter(|m| m.role == "system").count(), message.clone());
                token_count += tokens;
            } else {
                break; // Can't fit more
            }
        }
        
        // Reverse to get correct order
        kept_messages.reverse();
        context.messages = kept_messages;
    }
}

impl Default for ContextWindowManager {
    fn default() -> Self {
        Self::new(1000) // Reserve 1000 tokens for response
    }
}
