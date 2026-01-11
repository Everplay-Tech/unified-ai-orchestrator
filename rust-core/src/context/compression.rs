/// Context compression techniques

use crate::context::{Context, Message};

pub struct ContextCompressor {
    max_message_length: usize,
    remove_comments: bool,
    normalize_whitespace: bool,
}

impl ContextCompressor {
    pub fn new() -> Self {
        Self {
            max_message_length: 2000,
            remove_comments: false, // Keep comments by default
            normalize_whitespace: true,
        }
    }
    
    pub fn with_max_length(mut self, max_length: usize) -> Self {
        self.max_message_length = max_length;
        self
    }
    
    pub fn with_remove_comments(mut self, remove: bool) -> Self {
        self.remove_comments = remove;
        self
    }
    
    /// Compress context by removing redundancy
    pub fn compress(&self, context: &mut Context) -> CompressionStats {
        let original_size = self.estimate_size(context);
        
        // Remove consecutive duplicate messages
        let duplicates_removed = self.remove_duplicates(context);
        
        // Remove semantically similar messages
        let similar_removed = self.remove_similar_messages(context);
        
        // Compress long messages
        for message in &mut context.messages {
            self.compress_message(message);
        }
        
        // Normalize whitespace if enabled
        if self.normalize_whitespace {
            self.normalize_whitespace_in_context(context);
        }
        
        let compressed_size = self.estimate_size(context);
        let compression_ratio = if original_size > 0 {
            (1.0 - compressed_size as f32 / original_size as f32) * 100.0
        } else {
            0.0
        };
        
        CompressionStats {
            original_size,
            compressed_size,
            compression_ratio,
            duplicates_removed,
            similar_removed,
        }
    }
    
    /// Remove duplicate consecutive messages
    fn remove_duplicates(&self, context: &mut Context) -> usize {
        let mut removed = 0;
        let mut i = 0;
        while i < context.messages.len().saturating_sub(1) {
            let current = &context.messages[i];
            let next = &context.messages[i + 1];
            
            if current.role == next.role && current.content == next.content {
                context.messages.remove(i + 1);
                removed += 1;
            } else {
                i += 1;
            }
        }
        removed
    }
    
    /// Remove semantically similar messages (simple similarity check)
    fn remove_similar_messages(&self, context: &mut Context) -> usize {
        let mut removed = 0;
        let mut i = 0;
        
        while i < context.messages.len().saturating_sub(1) {
            let current = &context.messages[i];
            let next = &context.messages[i + 1];
            
            // Check if messages are similar (same role and high content similarity)
            if current.role == next.role {
                let similarity = self.calculate_similarity(&current.content, &next.content);
                if similarity > 0.8 {
                    // Keep the longer message
                    if current.content.len() < next.content.len() {
                        context.messages.remove(i);
                    } else {
                        context.messages.remove(i + 1);
                    }
                    removed += 1;
                    continue;
                }
            }
            i += 1;
        }
        
        removed
    }
    
    /// Calculate simple similarity between two strings (0.0 to 1.0)
    fn calculate_similarity(&self, a: &str, b: &str) -> f32 {
        if a == b {
            return 1.0;
        }
        
        // Simple word overlap similarity
        let words_a: std::collections::HashSet<&str> = a.split_whitespace().collect();
        let words_b: std::collections::HashSet<&str> = b.split_whitespace().collect();
        
        let intersection = words_a.intersection(&words_b).count();
        let union = words_a.union(&words_b).count();
        
        if union == 0 {
            0.0
        } else {
            intersection as f32 / union as f32
        }
    }
    
    /// Compress individual message
    fn compress_message(&self, message: &mut Message) {
        let mut content = message.content.clone();
        
        // Remove comments if enabled
        if self.remove_comments {
            content = self.remove_code_comments(&content);
        }
        
        // Normalize whitespace
        if self.normalize_whitespace {
            content = self.normalize_whitespace_text(&content);
        }
        
        // Compress code blocks (remove extra whitespace but preserve structure)
        content = self.compress_code_blocks(&content);
        
        // Limit message length (keep first and last parts if too long)
        if content.len() > self.max_message_length {
            let first_part = &content[..self.max_message_length / 2];
            let last_part = &content[content.len() - self.max_message_length / 2..];
            message.content = format!("{}... [truncated {} chars] ...{}", 
                first_part, content.len() - self.max_message_length, last_part);
        } else {
            message.content = content;
        }
    }
    
    fn remove_code_comments(&self, content: &str) -> String {
        // Remove single-line comments (// and #)
        let lines: Vec<&str> = content.lines()
            .map(|line| {
                if let Some(pos) = line.find("//") {
                    &line[..pos]
                } else if let Some(pos) = line.find("#") {
                    // Don't remove # if it's part of markdown
                    if line.trim_start().starts_with("#") {
                        line // Keep markdown headers
                    } else {
                        &line[..pos]
                    }
                } else {
                    line
                }
            })
            .collect();
        lines.join("\n")
    }
    
    fn normalize_whitespace_text(&self, text: &str) -> String {
        // Replace multiple spaces with single space, but preserve newlines in code blocks
        if text.contains("```") {
            // Preserve code block formatting
            text.to_string()
        } else {
            text.lines()
                .map(|line| line.trim())
                .filter(|line| !line.is_empty())
                .collect::<Vec<_>>()
                .join(" ")
        }
    }
    
    fn compress_code_blocks(&self, content: &str) -> String {
        // For code blocks, remove trailing whitespace but preserve structure
        let mut result = String::new();
        let mut in_code_block = false;
        
        for line in content.lines() {
            if line.trim().starts_with("```") {
                in_code_block = !in_code_block;
                result.push_str(line);
                result.push('\n');
            } else if in_code_block {
                // In code block: remove trailing whitespace but keep leading
                result.push_str(line.trim_end());
                result.push('\n');
            } else {
                result.push_str(line.trim());
                result.push('\n');
            }
        }
        
        result.trim().to_string()
    }
    
    fn normalize_whitespace_in_context(&self, context: &mut Context) {
        for message in &mut context.messages {
            if self.normalize_whitespace {
                message.content = self.normalize_whitespace_text(&message.content);
            }
        }
    }
    
    fn estimate_size(&self, context: &Context) -> usize {
        context.messages.iter()
            .map(|m| m.content.len())
            .sum()
    }
}

#[derive(Debug, Clone)]
pub struct CompressionStats {
    pub original_size: usize,
    pub compressed_size: usize,
    pub compression_ratio: f32, // Percentage
    pub duplicates_removed: usize,
    pub similar_removed: usize,
}

impl Default for ContextCompressor {
    fn default() -> Self {
        Self::new()
    }
}
