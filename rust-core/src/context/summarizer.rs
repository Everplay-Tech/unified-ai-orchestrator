/// Context summarization for long conversation histories

use crate::context::{Context, Message};
use std::collections::HashMap;

pub struct ContextSummarizer {
    message_threshold: usize,
    summary_ratio: f64, // Ratio of messages to summarize (e.g., 0.8 = summarize oldest 80%)
}

impl ContextSummarizer {
    pub fn new(message_threshold: usize, summary_ratio: f64) -> Self {
        Self {
            message_threshold,
            summary_ratio,
        }
    }
    
    /// Summarize context if it exceeds threshold
    pub fn summarize_if_needed(&self, context: &mut Context) -> Option<String> {
        if context.messages.len() <= self.message_threshold {
            return None;
        }
        
        // Calculate how many messages to summarize
        let messages_to_summarize = (context.messages.len() as f64 * self.summary_ratio) as usize;
        let messages_to_keep = context.messages.len() - messages_to_summarize;
        
        // Extract messages to summarize
        let messages_to_summarize: Vec<Message> = context.messages
            .drain(..messages_to_summarize)
            .collect();
        
        // Generate summary
        let summary = self.generate_summary(&messages_to_summarize);
        
        // Create summary message
        let summary_message = Message {
            role: "system".to_string(),
            content: format!("Previous conversation summary: {}", summary),
            timestamp: messages_to_summarize
                .first()
                .map(|m| m.timestamp)
                .unwrap_or(0),
        };
        
        // Insert summary at the beginning
        context.messages.insert(0, summary_message);
        
        Some(summary)
    }
    
    /// Generate summary from messages (extractive summarization)
    fn generate_summary(&self, messages: &[Message]) -> String {
        // Extractive summarization: keep important parts
        let mut summary_parts = Vec::new();
        
        for message in messages {
            // Keep code blocks
            if message.content.contains("```") {
                summary_parts.push(format!("[Code discussion: {}]", message.role));
            }
            
            // Keep decisions and important statements
            let content_lower = message.content.to_lowercase();
            if content_lower.contains("decided") 
                || content_lower.contains("decision")
                || content_lower.contains("important")
                || content_lower.contains("note")
            {
                // Extract key sentence
                let sentences: Vec<&str> = message.content
                    .split('.')
                    .filter(|s| {
                        let s_lower = s.to_lowercase();
                        s_lower.contains("decided") 
                            || s_lower.contains("decision")
                            || s_lower.contains("important")
                    })
                    .collect();
                
                if !sentences.is_empty() {
                    summary_parts.push(format!("[{}]: {}", message.role, sentences[0]));
                }
            }
        }
        
        if summary_parts.is_empty() {
            format!("Summarized {} messages", messages.len())
        } else {
            summary_parts.join("; ")
        }
    }
}

impl Default for ContextSummarizer {
    fn default() -> Self {
        Self::new(50, 0.8) // Summarize when >50 messages, keep recent 20%
    }
}
