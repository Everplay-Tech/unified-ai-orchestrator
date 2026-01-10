/// Semantic search engine

use crate::indexer::storage::IndexStorage;
use crate::indexer::semantic::EmbeddingGenerator;
use crate::error::Result;

pub struct SemanticSearch {
    storage: IndexStorage,
    embedding_gen: EmbeddingGenerator,
}

impl SemanticSearch {
    pub fn new(storage: IndexStorage) -> Self {
        Self {
            storage,
            embedding_gen: EmbeddingGenerator::default(),
        }
    }
    
    /// Search for code blocks using hybrid search (semantic + keyword)
    pub async fn search(
        &self,
        project_id: &str,
        query: &str,
        limit: usize,
    ) -> Result<Vec<SearchResult>> {
        // Generate query embedding
        let query_embedding = self.embedding_gen.generate_query_embedding(query);
        
        // Perform keyword search first to get candidate blocks
        let keyword_results = self.storage.search_blocks(project_id, query, limit * 3).await?;
        
        // Get embeddings for semantic similarity calculation
        let block_embeddings = self.storage.get_block_embeddings(project_id).await?;
        let embedding_map: std::collections::HashMap<i64, Vec<f32>> = 
            block_embeddings.into_iter().collect();
        
        // Calculate cosine similarity and combine with keyword scores
        let mut results: Vec<SearchResult> = keyword_results
            .into_iter()
            .map(|(file_path, block_type, name, start_line, end_line)| {
                // Keyword match score
                let mut keyword_score = 0.5;
                
                // Boost if name matches
                if let Some(ref n) = name {
                    if n.to_lowercase().contains(&query.to_lowercase()) {
                        keyword_score += 0.3;
                    }
                }
                
                // Try to find semantic similarity score
                let semantic_score = if let Some(ref n) = name {
                    // Try to get block ID and find its embedding
                    // For now, we'll calculate similarity if we have the embedding
                    // In a full implementation, we'd store block_id with results
                    0.0 // Placeholder - would need block_id in results
                } else {
                    0.0
                };
                
                // Combine scores (70% semantic, 30% keyword)
                let combined_score = semantic_score * 0.7 + keyword_score * 0.3;
                
                SearchResult {
                    file_path,
                    block_type,
                    name,
                    start_line: start_line as usize,
                    end_line: end_line as usize,
                    score: combined_score.max(keyword_score), // Use keyword score if semantic unavailable
                }
            })
            .collect();
        
        // If we have embeddings, enhance results with semantic similarity
        if !embedding_map.is_empty() {
            // Enhance existing results with semantic scores
            for result in &mut results {
                // Try to find matching embedding by getting block ID
                if let Some(block_id) = self.storage.get_block_id(
                    project_id,
                    &result.file_path,
                    result.name.as_deref()
                ).await.ok().flatten() {
                    if let Some(block_embedding) = embedding_map.get(&block_id) {
                        // Calculate cosine similarity
                        let similarity = cosine_similarity(&query_embedding, block_embedding);
                        // Update score: 70% semantic, 30% keyword
                        result.score = similarity * 0.7 + result.score * 0.3;
                    }
                }
            }
            
            // Also search semantically for blocks that might not match keywords
            for (block_id, block_embedding) in &embedding_map {
                let similarity = cosine_similarity(&query_embedding, block_embedding);
                
                // If similarity is high enough and not already in results, add it
                if similarity > 0.5 {
                    // Get block details (simplified - would need a method to get block by ID)
                    // For now, we'll rely on keyword search results
                }
            }
        }
        
        // Sort by score (highest first)
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        
        // Limit results
        results.truncate(limit);
        
        Ok(results)
    }
}

/// Calculate cosine similarity between two vectors
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() {
        return 0.0;
    }
    
    let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    
    if norm_a > 0.0 && norm_b > 0.0 {
        dot_product / (norm_a * norm_b)
    } else {
        0.0
    }
}

#[derive(Debug, Clone)]
pub struct SearchResult {
    pub file_path: String,
    pub block_type: String,
    pub name: Option<String>,
    pub start_line: usize,
    pub end_line: usize,
    pub score: f32,
}
