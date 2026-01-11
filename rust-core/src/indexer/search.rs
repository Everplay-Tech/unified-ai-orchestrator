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
    
    pub fn with_embedding_generator(mut storage: IndexStorage, embedding_gen: EmbeddingGenerator) -> Self {
        Self {
            storage,
            embedding_gen,
        }
    }
    
    /// Search for code blocks using hybrid search (semantic + keyword)
    pub async fn search(
        &mut self,
        project_id: &str,
        query: &str,
        limit: usize,
    ) -> Result<Vec<SearchResult>> {
        // Generate query embedding
        let query_embedding = self.embedding_gen.generate_query_embedding(query);
        
        // Get all block embeddings for semantic search
        let block_embeddings = self.storage.get_block_embeddings(project_id).await?;
        let embedding_map: std::collections::HashMap<i64, Vec<f32>> = 
            block_embeddings.into_iter().collect();
        
        // Perform keyword search to get candidate blocks
        let keyword_results = self.storage.search_blocks(project_id, query, limit * 5).await?;
        
        // Get block details with IDs for keyword results
        let mut keyword_results_with_ids = Vec::new();
        for (file_path, block_type, name, start_line, end_line) in keyword_results {
            if let Some(block_id) = self.storage.get_block_id(
                project_id,
                &file_path,
                name.as_deref()
            ).await.ok().flatten() {
                keyword_results_with_ids.push((block_id, file_path, block_type, name, start_line, end_line));
            }
        }
        
        // Calculate scores for keyword results
        let mut results: Vec<SearchResult> = keyword_results_with_ids
            .into_iter()
            .map(|(block_id, file_path, block_type, name, start_line, end_line)| {
                // Keyword match score
                let mut keyword_score = 0.5;
                
                // Boost if name matches exactly
                if let Some(ref n) = name {
                    let query_lower = query.to_lowercase();
                    let name_lower = n.to_lowercase();
                    if name_lower == query_lower {
                        keyword_score = 1.0;
                    } else if name_lower.contains(&query_lower) {
                        keyword_score += 0.3;
                    }
                }
                
                // Calculate semantic similarity if embedding exists
                let semantic_score = embedding_map.get(&block_id)
                    .map(|block_embedding| {
                        cosine_similarity(&query_embedding, block_embedding)
                    })
                    .unwrap_or(0.0);
                
                // Combine scores (70% semantic if available, 30% keyword)
                let combined_score = if semantic_score > 0.0 {
                    semantic_score * 0.7 + keyword_score * 0.3
                } else {
                    keyword_score
                };
                
                SearchResult {
                    file_path,
                    block_type,
                    name,
                    start_line: start_line as usize,
                    end_line: end_line as usize,
                    score: combined_score,
                    block_id: Some(block_id),
                }
            })
            .collect();
        
        // If we have embeddings, also do pure semantic search for blocks not in keyword results
        if !embedding_map.is_empty() {
            let mut semantic_results: Vec<(i64, f32)> = embedding_map
                .iter()
                .map(|(block_id, block_embedding)| {
                    let similarity = cosine_similarity(&query_embedding, block_embedding);
                    (*block_id, similarity)
                })
                .filter(|(_, similarity)| *similarity > 0.5) // Threshold for semantic matches
                .collect();
            
            // Sort by similarity
            semantic_results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
            
            // Get block details for top semantic matches not already in results
            let existing_block_ids: std::collections::HashSet<i64> = results
                .iter()
                .filter_map(|r| r.block_id)
                .collect();
            
            for (block_id, similarity) in semantic_results.into_iter().take(limit) {
                if !existing_block_ids.contains(&block_id) {
                    // Get block details by ID
                    if let Some(block_details) = self.storage.get_block_by_id(block_id).await.ok().flatten() {
                        results.push(SearchResult {
                            file_path: block_details.0,
                            block_type: block_details.1,
                            name: block_details.2,
                            start_line: block_details.3 as usize,
                            end_line: block_details.4 as usize,
                            score: similarity * 0.7, // Pure semantic score
                            block_id: Some(block_id),
                        });
                    }
                }
            }
        }
        
        // Deduplicate results (by block_id if available, otherwise by file_path + name + start_line)
        results.sort_by(|a, b| {
            // Sort by score first
            b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| {
                    // Then by block_id if available
                    match (a.block_id, b.block_id) {
                        (Some(id_a), Some(id_b)) => id_a.cmp(&id_b),
                        _ => std::cmp::Ordering::Equal,
                    }
                })
        });
        
        // Remove duplicates
        let mut seen_ids = std::collections::HashSet::new();
        let mut seen_keys = std::collections::HashSet::new();
        results.retain(|r| {
            if let Some(block_id) = r.block_id {
                seen_ids.insert(block_id)
            } else {
                let key = format!("{}:{:?}:{}", r.file_path, r.name, r.start_line);
                seen_keys.insert(key)
            }
        });
        
        // Limit results
        results.truncate(limit);
        
        Ok(results)
    }
    
    /// Semantic-only search (when keyword search fails or is not desired)
    pub async fn search_semantic_only(
        &mut self,
        project_id: &str,
        query: &str,
        limit: usize,
        threshold: f32,
    ) -> Result<Vec<SearchResult>> {
        let query_embedding = self.embedding_gen.generate_query_embedding(query);
        let block_embeddings = self.storage.get_block_embeddings(project_id).await?;
        
        let mut results: Vec<(i64, f32)> = block_embeddings
            .into_iter()
            .map(|(block_id, block_embedding)| {
                let similarity = cosine_similarity(&query_embedding, &block_embedding);
                (block_id, similarity)
            })
            .filter(|(_, similarity)| *similarity >= threshold)
            .collect();
        
        results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        
        let mut search_results = Vec::new();
        for (block_id, similarity) in results.into_iter().take(limit) {
            if let Some(block_details) = self.storage.get_block_by_id(block_id).await.ok().flatten() {
                search_results.push(SearchResult {
                    file_path: block_details.0,
                    block_type: block_details.1,
                    name: block_details.2,
                    start_line: block_details.3 as usize,
                    end_line: block_details.4 as usize,
                    score: similarity,
                    block_id: Some(block_id),
                });
            }
        }
        
        Ok(search_results)
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
    pub block_id: Option<i64>, // For deduplication and reference
}
