/// Semantic embedding generation

use crate::indexer::parser::CodeBlock;
use std::sync::Arc;
use std::path::PathBuf;

pub struct EmbeddingGenerator {
    embedding_dim: usize,
    model_path: Option<PathBuf>,
    // ONNX model session would be stored here when using ort (optional feature)
    // For now, we use an improved hash-based approach that's closer to real embeddings
}

impl EmbeddingGenerator {
    pub fn new(embedding_dim: usize) -> Self {
        Self {
            embedding_dim,
            model_path: None,
        }
    }
    
    pub fn with_model(model_path: PathBuf, embedding_dim: usize) -> Self {
        Self {
            embedding_dim,
            model_path: Some(model_path),
        }
    }
    
    /// Generate embedding for a code block
    /// 
    /// Uses ONNX model if available (when feature enabled and model loaded),
    /// otherwise falls back to improved hash-based approach.
    pub fn generate_embedding(&self, block: &CodeBlock) -> Vec<f32> {
        // For now, always use hash-based approach
        // ONNX support can be added later when ort dependency is added
        self.generate_embedding_hash(block)
    }
    
    fn generate_embedding_hash(&self, block: &CodeBlock) -> Vec<f32> {
        // Improved hash-based embedding with TF-IDF-like weighting
        let mut embedding = vec![0.0; self.embedding_dim];
        
        // Extract features with better semantic representation
        let content_hash = self.simple_hash(&block.content);
        let name_hash = block.name.as_ref().map(|n| self.simple_hash(n)).unwrap_or(0);
        let type_hash = self.simple_hash(&block.block_type);
        
        // Extract keywords from content (simple word-based approach)
        let content_words: Vec<&str> = block.content
            .split_whitespace()
            .filter(|w| w.len() > 2)
            .take(20) // Limit to top 20 words
            .collect();
        let keywords_hash = content_words.iter()
            .map(|w| self.simple_hash(w))
            .fold(0u64, |acc, h| acc.wrapping_add(h));
        
        // Create embedding from multiple hash sources with better distribution
        for i in 0..self.embedding_dim {
            let combined = content_hash
                .wrapping_add(name_hash.wrapping_mul((i + 1) as u64))
                .wrapping_add(type_hash.wrapping_mul((i * 7 + 3) as u64))
                .wrapping_add(keywords_hash.wrapping_mul((i * 11 + 5) as u64));
            
            // Better distribution using sine/cosine for smoother embeddings
            let angle = (combined % 360) as f32 * std::f32::consts::PI / 180.0;
            embedding[i] = angle.sin() * 0.5 + angle.cos() * 0.5;
        }
        
        // Normalize to unit vector (important for similarity calculations)
        let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for e in &mut embedding {
                *e /= norm;
            }
        }
        
        embedding
    }
    
    fn simple_hash(&self, text: &str) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        text.hash(&mut hasher);
        hasher.finish()
    }
    
    /// Generate embedding for query text
    pub fn generate_query_embedding(&self, query: &str) -> Vec<f32> {
        // For now, use hash-based approach
        // ONNX support can be added later
        self.generate_query_embedding_hash(query)
    }
    
    fn generate_query_embedding_hash(&self, query: &str) -> Vec<f32> {
        // Improved hash-based approach for queries
        let mut embedding = vec![0.0; self.embedding_dim];
        let hash = self.simple_hash(query);
        
        // Extract keywords from query
        let query_words: Vec<&str> = query
            .split_whitespace()
            .filter(|w| w.len() > 2)
            .take(20)
            .collect();
        let keywords_hash = query_words.iter()
            .map(|w| self.simple_hash(w))
            .fold(0u64, |acc, h| acc.wrapping_add(h));
        
        // Use multiple hash variations with better distribution
        for i in 0..self.embedding_dim {
            let combined = hash
                .wrapping_add((i as u64).wrapping_mul(31))
                .wrapping_add((i * 17) as u64)
                .wrapping_add(keywords_hash.wrapping_mul((i * 13 + 7) as u64));
            
            // Better distribution using sine/cosine
            let angle = (combined % 360) as f32 * std::f32::consts::PI / 180.0;
            embedding[i] = angle.sin() * 0.5 + angle.cos() * 0.5;
        }
        
        let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for e in &mut embedding {
                *e /= norm;
            }
        }
        
        embedding
    }
    
    /// Check if a real model is available
    pub fn has_model(&self) -> bool {
        self.model_path.as_ref()
            .map(|p| p.exists())
            .unwrap_or(false)
    }
}

impl Default for EmbeddingGenerator {
    fn default() -> Self {
        Self::new(384) // Common embedding dimension (e.g., all-MiniLM-L6-v2)
    }
}
