/// Context compression techniques

use crate::context::{Context, Message};

pub struct ContextCompressor;

impl ContextCompressor {
    /// Compress context by removing redundancy
    pub fn compress(&self, context: &mut Context) {
        // Remove consecutive duplicate messages
        self.remove_duplicates(context);
        
        // Compress long messages
        for message in &mut context.messages {
            self.compress_message(message);
        }
    }
    
    /// Remove duplicate consecutive messages
    fn remove_duplicates(&self, context: &mut Context) {
        let mut i = 0;
        while i < context.messages.len().saturating_sub(1) {
            let current = &context.messages[i];
            let next = &context.messages[i + 1];
            
            if current.role == next.role && current.content == next.content {
                context.messages.remove(i + 1);
            } else {
                i += 1;
            }
        }
    }
    
    /// Compress individual message
    fn compress_message(&self, message: &mut Message) {
        // Remove excessive whitespace
        let compressed = message.content
            .lines()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty())
            .collect::<Vec<_>>()
            .join(" ");
        
        // Limit message length (keep first and last parts if too long)
        const MAX_LENGTH: usize = 2000;
        if compressed.len() > MAX_LENGTH {
            let first_part = &compressed[..MAX_LENGTH / 2];
            let last_part = &compressed[compressed.len() - MAX_LENGTH / 2..];
            message.content = format!("{}... [truncated] ...{}", first_part, last_part);
        } else {
            message.content = compressed;
        }
    }
}

impl Default for ContextCompressor {
    fn default() -> Self {
        Self
    }
}
