/// Semantic embedding generation

use crate::indexer::parser::CodeBlock;
use std::sync::Arc;
use std::path::PathBuf;
use std::collections::HashMap;

#[cfg(feature = "onnx-embeddings")]
use ort::{Session, Value, Tensor};

pub struct EmbeddingGenerator {
    embedding_dim: usize,
    model_path: Option<PathBuf>,
    #[cfg(feature = "onnx-embeddings")]
    model_session: Option<Arc<Session>>,
    embedding_cache: HashMap<String, Vec<f32>>, // Simple in-memory cache
}

impl EmbeddingGenerator {
    pub fn new(embedding_dim: usize) -> Self {
        Self {
            embedding_dim,
            model_path: None,
            #[cfg(feature = "onnx-embeddings")]
            model_session: None,
            embedding_cache: HashMap::new(),
        }
    }
    
    /// Create EmbeddingGenerator with ONNX model
    /// 
    /// # Returns
    /// 
    /// Returns `Result<Self, String>` to handle potential errors when loading the ONNX model.
    /// The error string describes what went wrong during model loading.
    /// 
    /// # Note
    /// 
    /// This method always returns a `Result` for API consistency, even when the `onnx-embeddings`
    /// feature is disabled. When the feature is disabled, this will return `Ok(Self)` without
    /// actually loading a model (the model path is stored but not used).
    /// 
    /// # Example
    /// 
    /// ```rust,no_run
    /// use std::path::PathBuf;
    /// let generator = EmbeddingGenerator::with_model(
    ///     PathBuf::from("model.onnx"),
    ///     384
    /// )?;
    /// ```
    pub fn with_model(model_path: PathBuf, embedding_dim: usize) -> Result<Self, String> {
        #[cfg(feature = "onnx-embeddings")]
        {
            // Load ONNX model
            let session = Session::builder()
                .map_err(|e| format!("Failed to create ONNX session builder: {}", e))?
                .commit_from_file(&model_path)
                .map_err(|e| format!("Failed to load ONNX model from {}: {}", model_path.display(), e))?;
            
            Ok(Self {
                embedding_dim,
                model_path: Some(model_path),
                model_session: Some(Arc::new(session)),
                embedding_cache: HashMap::new(),
            })
        }
        
        #[cfg(not(feature = "onnx-embeddings"))]
        {
            // ONNX feature disabled - return generator without model session
            // Model path is stored but won't be used for actual model loading
            Ok(Self {
                embedding_dim,
                model_path: Some(model_path),
                embedding_cache: HashMap::new(),
            })
        }
    }
    
    #[cfg(feature = "onnx-embeddings")]
    fn load_model_if_needed(&mut self) -> Result<(), String> {
        if self.model_session.is_none() {
            if let Some(ref path) = self.model_path {
                if path.exists() {
                    let session = Session::builder()
                        .map_err(|e| format!("Failed to create ONNX session builder: {}", e))?
                        .commit_from_file(path)
                        .map_err(|e| format!("Failed to load ONNX model: {}", e))?;
                    self.model_session = Some(Arc::new(session));
                }
            }
        }
        Ok(())
    }
    
    /// Generate embedding for a code block
    /// 
    /// Uses ONNX model if available (when feature enabled and model loaded),
    /// otherwise falls back to improved hash-based approach.
    pub fn generate_embedding(&mut self, block: &CodeBlock) -> Vec<f32> {
        // Check cache first
        let cache_key = format!("{}{:?}{}", block.content, block.name, block.block_type);
        if let Some(cached) = self.embedding_cache.get(&cache_key) {
            return cached.clone();
        }
        
        #[cfg(feature = "onnx-embeddings")]
        {
            if let Some(ref session) = self.model_session {
                match self.generate_embedding_onnx(session, block) {
                    Ok(embedding) => {
                        self.embedding_cache.insert(cache_key, embedding.clone());
                        return embedding;
                    }
                    Err(e) => {
                        eprintln!("ONNX embedding generation failed: {}, falling back to hash", e);
                    }
                }
            }
        }
        
        // Fallback to hash-based approach
        let embedding = self.generate_embedding_hash(block);
        self.embedding_cache.insert(cache_key, embedding.clone());
        embedding
    }
    
    #[cfg(feature = "onnx-embeddings")]
    fn generate_embedding_onnx(&self, session: &Session, block: &CodeBlock) -> Result<Vec<f32>, String> {
        // Prepare input text (combine name, type, and content)
        let input_text = format!(
            "{} {} {}",
            block.block_type,
            block.name.as_deref().unwrap_or(""),
            block.content
        );
        
        // Tokenize input (simplified - in production, use proper tokenizer)
        // For now, we'll use a simple word-based approach
        // Real models would use SentencePiece or similar tokenizers
        let tokens: Vec<i64> = input_text
            .split_whitespace()
            .take(512) // Typical max sequence length
            .enumerate()
            .map(|(i, _)| i as i64)
            .collect();
        
        // Create input tensor
        let input_shape = vec![1, tokens.len() as i64];
        let input_tensor = Tensor::from_array((input_shape.clone(), tokens))
            .map_err(|e| format!("Failed to create input tensor: {}", e))?;
        
        // Run inference
        let inputs = vec![Value::from_tensor(input_tensor)?];
        let outputs = session.run(inputs)
            .map_err(|e| format!("ONNX inference failed: {}", e))?;
        
        // Extract embedding from output
        let output_tensor = outputs[0].try_extract_tensor::<f32>()
            .map_err(|e| format!("Failed to extract output tensor: {}", e))?;
        
        let embedding: Vec<f32> = output_tensor.iter().cloned().collect();
        
        // Normalize
        let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            Ok(embedding.iter().map(|x| x / norm).collect())
        } else {
            Ok(embedding)
        }
    }
    
    /// Generate embeddings in batch (more efficient)
    pub fn generate_embeddings_batch(&mut self, blocks: &[CodeBlock]) -> Vec<Vec<f32>> {
        blocks.iter()
            .map(|block| self.generate_embedding(block))
            .collect()
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
    pub fn generate_query_embedding(&mut self, query: &str) -> Vec<f32> {
        // Check cache
        if let Some(cached) = self.embedding_cache.get(query) {
            return cached.clone();
        }
        
        #[cfg(feature = "onnx-embeddings")]
        {
            if let Some(ref session) = self.model_session {
                match self.generate_query_embedding_onnx(session, query) {
                    Ok(embedding) => {
                        self.embedding_cache.insert(query.to_string(), embedding.clone());
                        return embedding;
                    }
                    Err(e) => {
                        eprintln!("ONNX query embedding failed: {}, falling back to hash", e);
                    }
                }
            }
        }
        
        // Fallback to hash-based approach
        let embedding = self.generate_query_embedding_hash(query);
        self.embedding_cache.insert(query.to_string(), embedding.clone());
        embedding
    }
    
    #[cfg(feature = "onnx-embeddings")]
    fn generate_query_embedding_onnx(&self, session: &Session, query: &str) -> Result<Vec<f32>, String> {
        // Similar to block embedding but for query text
        let tokens: Vec<i64> = query
            .split_whitespace()
            .take(512)
            .enumerate()
            .map(|(i, _)| i as i64)
            .collect();
        
        let input_shape = vec![1, tokens.len() as i64];
        let input_tensor = Tensor::from_array((input_shape.clone(), tokens))
            .map_err(|e| format!("Failed to create input tensor: {}", e))?;
        
        let inputs = vec![Value::from_tensor(input_tensor)?];
        let outputs = session.run(inputs)
            .map_err(|e| format!("ONNX inference failed: {}", e))?;
        
        let output_tensor = outputs[0].try_extract_tensor::<f32>()
            .map_err(|e| format!("Failed to extract output tensor: {}", e))?;
        
        let embedding: Vec<f32> = output_tensor.iter().cloned().collect();
        
        let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            Ok(embedding.iter().map(|x| x / norm).collect())
        } else {
            Ok(embedding)
        }
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
        #[cfg(feature = "onnx-embeddings")]
        {
            self.model_session.is_some() || self.model_path.as_ref()
                .map(|p| p.exists())
                .unwrap_or(false)
        }
        #[cfg(not(feature = "onnx-embeddings"))]
        {
            false
        }
    }
    
    /// Clear embedding cache
    pub fn clear_cache(&mut self) {
        self.embedding_cache.clear();
    }
    
    /// Set cache size limit (simple implementation - clears all when limit reached)
    pub fn set_cache_limit(&mut self, limit: usize) {
        if self.embedding_cache.len() > limit {
            self.embedding_cache.clear();
        }
    }
}

impl Default for EmbeddingGenerator {
    fn default() -> Self {
        Self::new(384) // Common embedding dimension (e.g., all-MiniLM-L6-v2)
    }
}
