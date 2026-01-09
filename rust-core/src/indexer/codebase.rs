/// Codebase indexing logic

use crate::indexer::parser::{ASTParser, CodeBlock};
use crate::indexer::storage::IndexStorage;
use std::path::{Path, PathBuf};
use std::collections::HashMap;

pub struct CodebaseIndexer {
    parser: ASTParser,
    storage: IndexStorage,
    project_id: String,
}

impl CodebaseIndexer {
    pub fn new(project_id: String, storage: IndexStorage) -> Self {
        Self {
            parser: ASTParser::new(),
            storage,
            project_id,
        }
    }
    
    pub async fn index_directory(&mut self, root_path: &Path) -> Result<usize, String> {
        let mut indexed_count = 0;
        
        // Walk directory and index files
        if root_path.is_dir() {
            self.index_directory_recursive(root_path, &mut indexed_count).await?;
        } else if root_path.is_file() {
            self.index_file(root_path).await?;
            indexed_count = 1;
        }
        
        Ok(indexed_count)
    }
    
    async fn index_directory_recursive(
        &mut self,
        dir: &Path,
        count: &mut usize,
    ) -> Result<(), String> {
        let entries = std::fs::read_dir(dir)
            .map_err(|e| format!("Failed to read directory: {}", e))?;
        
        for entry in entries {
            let entry = entry.map_err(|e| format!("Failed to read entry: {}", e))?;
            let path = entry.path();
            
            // Skip hidden files and directories
            if path.file_name()
                .and_then(|n| n.to_str())
                .map(|n| n.starts_with('.'))
                .unwrap_or(false)
            {
                continue;
            }
            
            // Skip node_modules, target, etc.
            if path.file_name()
                .and_then(|n| n.to_str())
                .map(|n| matches!(n, "node_modules" | "target" | ".git" | "__pycache__" | ".venv"))
                .unwrap_or(false)
            {
                continue;
            }
            
            if path.is_dir() {
                self.index_directory_recursive(&path, count).await?;
            } else if path.is_file() {
                if let Some(language) = ASTParser::detect_language(&path) {
                    self.index_file(&path).await?;
                    *count += 1;
                }
            }
        }
        
        Ok(())
    }
    
    pub async fn index_file(&mut self, file_path: &Path) -> Result<(), String> {
        let language = ASTParser::detect_language(file_path)
            .ok_or_else(|| "Unknown language".to_string())?;
        
        // Read file content
        let content = std::fs::read_to_string(file_path)
            .map_err(|e| format!("Failed to read file: {}", e))?;
        
        // Parse AST
        let blocks = self.parser.parse_file(&content, &language)?;
        
        // Store in database
        let relative_path = file_path.to_string_lossy().to_string();
        self.storage.store_file(
            &self.project_id,
            &relative_path,
            &language,
            &blocks,
        ).await
            .map_err(|e| format!("Failed to store: {}", e))?;
        
        Ok(())
    }
    
    pub async fn update_file(&mut self, file_path: &Path) -> Result<(), String> {
        // Remove old entries and re-index
        let relative_path = file_path.to_string_lossy().to_string();
        self.storage.remove_file(&self.project_id, &relative_path).await
            .map_err(|e| format!("Failed to remove old entries: {}", e))?;
        
        self.index_file(file_path).await
    }
    
    pub async fn remove_file(&mut self, file_path: &Path) -> Result<(), String> {
        let relative_path = file_path.to_string_lossy().to_string();
        self.storage.remove_file(&self.project_id, &relative_path).await
            .map_err(|e| format!("Failed to remove: {}", e))
    }
}
