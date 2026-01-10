/// Context summarization for long conversation histories

use crate::context::{Context, Message};
use std::collections::HashMap;

#[derive(Clone, Copy)]
pub enum SummarizationStrategy {
    Extractive,
    Abstractive,
    Hybrid,
}

pub struct ContextSummarizer {
    message_threshold: usize,
    summary_ratio: f64, // Ratio of messages to summarize (e.g., 0.8 = summarize oldest 80%)
    strategy: SummarizationStrategy,
    abstractive_threshold: usize, // Use abstractive for conversations > this many messages
}

impl ContextSummarizer {
    pub fn new(message_threshold: usize, summary_ratio: f64) -> Self {
        Self {
            message_threshold,
            summary_ratio,
            strategy: SummarizationStrategy::Hybrid,
            abstractive_threshold: 100,
        }
    }
    
    pub fn with_strategy(mut self, strategy: SummarizationStrategy) -> Self {
        self.strategy = strategy;
        self
    }
    
    /// Summarize context if it exceeds threshold
    pub fn summarize_if_needed(&self, context: &mut Context) -> Option<String> {
        if context.messages.len() <= self.message_threshold {
            return None;
        }
        
        // Calculate how many messages to summarize
        let messages_to_summarize = (context.messages.len() as f64 * self.summary_ratio) as usize;
        
        // Extract messages to summarize
        let messages_to_summarize: Vec<Message> = context.messages
            .drain(..messages_to_summarize)
            .collect();
        
        // Generate summary based on strategy
        let summary = match self.strategy {
            SummarizationStrategy::Extractive => {
                self.generate_summary(&messages_to_summarize)
            }
            SummarizationStrategy::Abstractive => {
                if messages_to_summarize.len() > self.abstractive_threshold {
                    self.generate_abstractive_summary(&messages_to_summarize)
                } else {
                    self.generate_summary(&messages_to_summarize)
                }
            }
            SummarizationStrategy::Hybrid => {
                if messages_to_summarize.len() > self.abstractive_threshold {
                    // Use abstractive for large conversations
                    self.generate_abstractive_summary(&messages_to_summarize)
                } else {
                    // Use extractive for smaller conversations
                    self.generate_summary(&messages_to_summarize)
                }
            }
        };
        
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
    
    /// Generate summary from messages (extractive summarization with importance scoring)
    fn generate_summary(&self, messages: &[Message]) -> String {
        // Score messages by importance
        let mut scored_messages: Vec<(usize, f32, &Message)> = messages
            .iter()
            .enumerate()
            .map(|(idx, msg)| (idx, self.score_message_importance(msg), msg))
            .collect();
        
        // Sort by importance (highest first)
        scored_messages.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        
        // Extract top important messages
        let mut summary_parts = Vec::new();
        let mut seen_content = std::collections::HashSet::new();
        
        // Keep top 30% most important messages
        let top_count = (scored_messages.len() as f64 * 0.3).ceil() as usize;
        
        for (idx, score, message) in scored_messages.iter().take(top_count.max(5)) {
            if score > &0.3 && !seen_content.contains(&message.content) {
                seen_content.insert(message.content.clone());
                
                // Extract key information based on message type
                if message.content.contains("```") {
                    summary_parts.push(format!("[Code discussion: {}]", message.role));
                } else {
                    // Extract important sentences
                    let important_sentences = self.extract_important_sentences(&message.content);
                    if !important_sentences.is_empty() {
                        summary_parts.push(format!("[{}]: {}", message.role, important_sentences));
                    }
                }
            }
        }
        
        if summary_parts.is_empty() {
            format!("Summarized {} messages", messages.len())
        } else {
            summary_parts.join("; ")
        }
    }
    
    /// Score message importance (0.0 to 1.0)
    fn score_message_importance(&self, message: &Message) -> f32 {
        let mut score = 0.0;
        let content_lower = message.content.to_lowercase();
        
        // Role-based scoring
        match message.role.as_str() {
            "system" => score += 0.5,
            "user" => score += 0.3,
            "assistant" => score += 0.2,
            _ => {}
        }
        
        // Keyword-based scoring
        let important_keywords = vec![
            "decided", "decision", "important", "note", "error", "fix", "solution",
            "problem", "issue", "bug", "implement", "change", "update", "refactor"
        ];
        
        for keyword in important_keywords {
            if content_lower.contains(keyword) {
                score += 0.1;
            }
        }
        
        // Code block presence
        if message.content.contains("```") {
            score += 0.2;
        }
        
        // Recency weighting (would need timestamp comparison in real implementation)
        // For now, assume all messages are equally recent
        
        // Length-based (very short or very long might be less important)
        let len = message.content.len();
        if len > 50 && len < 2000 {
            score += 0.1;
        }
        
        score.min(1.0)
    }
    
    /// Extract important sentences from content
    fn extract_important_sentences(&self, content: &str) -> String {
        let sentences: Vec<&str> = content.split('.').collect();
        let mut important = Vec::new();
        
        let important_keywords = vec![
            "decided", "decision", "important", "note", "error", "fix", "solution",
            "problem", "issue", "bug", "implement", "change", "update"
        ];
        
        for sentence in sentences {
            let sentence_lower = sentence.to_lowercase();
            if important_keywords.iter().any(|kw| sentence_lower.contains(kw)) {
                important.push(sentence.trim());
            }
        }
        
        if important.is_empty() {
            // Fallback: return first sentence if no keywords found
            sentences.first().map(|s| s.trim().to_string()).unwrap_or_default()
        } else {
            important.join(". ").trim().to_string()
        }
    }
    
    /// Generate abstractive summary (placeholder - would call LLM API)
    fn generate_abstractive_summary(&self, messages: &[Message]) -> String {
        // For now, use improved extractive summarization
        // In a full implementation, this would:
        // 1. Prepare messages for LLM API
        // 2. Call LLM with summarization prompt
        // 3. Cache result to avoid repeated calls
        // 4. Return abstractive summary
        
        // Fallback to extractive with higher importance threshold
        let mut summary_parts = Vec::new();
        
        // Extract key themes and decisions
        for message in messages {
            let score = self.score_message_importance(message);
            if score > 0.5 {
                let important_sentences = self.extract_important_sentences(&message.content);
                if !important_sentences.is_empty() {
                    summary_parts.push(format!("[{}]: {}", message.role, important_sentences));
                }
            }
        }
        
        if summary_parts.is_empty() {
            format!("Summarized {} messages (abstractive mode)", messages.len())
        } else {
            format!("Key points from {} messages: {}", messages.len(), summary_parts.join("; "))
        }
    }
}

impl Default for ContextSummarizer {
    fn default() -> Self {
        Self::new(50, 0.8) // Summarize when >50 messages, keep recent 20%
    }
}
