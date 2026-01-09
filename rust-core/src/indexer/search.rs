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
    
    /// Search for code blocks using hybrid search
    pub async fn search(
        &self,
        project_id: &str,
        query: &str,
        limit: usize,
    ) -> Result<Vec<SearchResult>> {
        // Generate query embedding
        let query_embedding = self.embedding_gen.generate_query_embedding(query);
        
        // Perform keyword search first
        let keyword_results = self.storage.search_blocks(project_id, query, limit * 2).await?;
        
        // Score and rank results
        let mut results: Vec<SearchResult> = keyword_results
            .into_iter()
            .map(|(file_path, block_type, name, start_line, end_line)| {
                // Simple scoring: keyword match gets base score
                let mut score = 0.5;
                
                // Boost if name matches
                if let Some(ref n) = name {
                    if n.to_lowercase().contains(&query.to_lowercase()) {
                        score += 0.3;
                    }
                }
                
                SearchResult {
                    file_path,
                    block_type,
                    name,
                    start_line: start_line as usize,
                    end_line: end_line as usize,
                    score,
                }
            })
            .collect();
        
        // Sort by score
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        
        // Limit results
        results.truncate(limit);
        
        Ok(results)
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
