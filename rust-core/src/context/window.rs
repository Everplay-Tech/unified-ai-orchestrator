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
    
    /// Truncate context to fit within window with importance-based retention
    fn truncate_context(&self, context: &mut Context, model: &str, window_size: usize) {
        let available_tokens = window_size - self.reserved_tokens;
        
        // Score messages by importance
        let mut scored_messages: Vec<(usize, f32, Message)> = context.messages
            .iter()
            .enumerate()
            .map(|(idx, msg)| {
                let importance = self.score_message_importance(msg, idx, context.messages.len());
                (idx, importance, msg.clone())
            })
            .collect();
        
        // Sort by importance (highest first), but preserve order for same importance
        scored_messages.sort_by(|a, b| {
            b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.0.cmp(&b.0)) // Preserve original order for same importance
        });
        
        // Keep messages that fit, prioritizing importance
        let mut kept_messages = Vec::new();
        let mut token_count = 0;
        let mut kept_indices = std::collections::HashSet::new();
        
        // First pass: keep all system messages and high-importance messages
        for (idx, importance, message) in &scored_messages {
            if kept_indices.contains(idx) {
                continue;
            }
            
            let tokens = self.token_counter.estimate_tokens(&message.content) + 4;
            
            // Always keep system messages if possible
            if message.role == "system" && token_count + tokens <= available_tokens {
                kept_messages.push((*idx, message.clone()));
                kept_indices.insert(*idx);
                token_count += tokens;
            }
            // Keep high-importance messages
            else if importance > 0.7 && token_count + tokens <= available_tokens {
                kept_messages.push((*idx, message.clone()));
                kept_indices.insert(*idx);
                token_count += tokens;
            }
        }
        
        // Second pass: fill remaining space with recent messages
        // Iterate in reverse order (most recent first) using enumerate to get reliable indices
        for (rev_idx, message) in context.messages.iter().rev().enumerate() {
            // Calculate original index: if we're at position rev_idx in reversed iterator,
            // the original index is len - 1 - rev_idx
            let idx = context.messages.len() - 1 - rev_idx;
            
            if kept_indices.contains(&idx) {
                continue;
            }
            
            let tokens = self.token_counter.estimate_tokens(&message.content) + 4;
            if token_count + tokens <= available_tokens {
                kept_messages.push((idx, message.clone()));
                kept_indices.insert(idx);
                token_count += tokens;
            } else {
                break;
            }
        }
        
        // Sort by original index to preserve order
        kept_messages.sort_by_key(|(idx, _)| *idx);
        context.messages = kept_messages.into_iter().map(|(_, msg)| msg).collect();
    }
    
    /// Score message importance (0.0 to 1.0)
    fn score_message_importance(&self, message: &Message, position: usize, total: usize) -> f32 {
        let mut score = 0.5; // Base score
        
        // System messages are always important
        if message.role == "system" {
            score = 1.0;
        }
        
        // Recent messages are more important
        let recency = 1.0 - (position as f32 / total as f32);
        score += recency * 0.3;
        
        // Messages with code blocks are important
        if message.content.contains("```") {
            score += 0.2;
        }
        
        // Messages with keywords indicating importance
        let content_lower = message.content.to_lowercase();
        let important_keywords = ["error", "bug", "fix", "important", "decided", "decision", "todo", "fixme"];
        for keyword in important_keywords {
            if content_lower.contains(keyword) {
                score += 0.1;
                break;
            }
        }
        
        // Cap at 1.0
        score.min(1.0)
    }
}

impl Default for ContextWindowManager {
    fn default() -> Self {
        Self::new(1000) // Reserve 1000 tokens for response
    }
}
