/// Codebase indexing logic

use crate::indexer::parser::{ASTParser, CodeBlock};
use crate::indexer::storage::IndexStorage;
use std::path::{Path, PathBuf};
use std::collections::HashMap;
use std::time::SystemTime;

pub struct CodebaseIndexer {
    parser: ASTParser,
    storage: IndexStorage,
    project_id: String,
    indexed_files: HashMap<String, SystemTime>, // Track indexed files and their modification times
    skip_patterns: Vec<String>, // Patterns to skip (e.g., "*.log", "node_modules/**")
}

impl CodebaseIndexer {
    pub fn new(project_id: String, storage: IndexStorage) -> Self {
        Self {
            parser: ASTParser::new(),
            storage,
            project_id,
            indexed_files: HashMap::new(),
            skip_patterns: vec![
                "node_modules".to_string(),
                "target".to_string(),
                ".git".to_string(),
                "__pycache__".to_string(),
                ".venv".to_string(),
                "venv".to_string(),
                ".env".to_string(),
                "*.log".to_string(),
                "*.tmp".to_string(),
            ],
        }
    }
    
    pub fn with_skip_patterns(mut self, patterns: Vec<String>) -> Self {
        self.skip_patterns = patterns;
        self
    }
    
    pub async fn index_directory(&mut self, root_path: &Path) -> Result<usize, String> {
        let mut indexed_count = 0;
        let mut errors = Vec::new();
        
        // Walk directory and index files
        if root_path.is_dir() {
            self.index_directory_recursive(root_path, &mut indexed_count, &mut errors).await?;
        } else if root_path.is_file() {
            match self.index_file(root_path).await {
                Ok(_) => indexed_count += 1,
                Err(e) => errors.push(format!("Failed to index {}: {}", root_path.display(), e)),
            }
        }
        
        // Log errors but don't fail completely
        if !errors.is_empty() {
            eprintln!("Indexing completed with {} errors:", errors.len());
            for error in &errors[..errors.len().min(10)] {
                eprintln!("  {}", error);
            }
            if errors.len() > 10 {
                eprintln!("  ... and {} more errors", errors.len() - 10);
            }
        }
        
        Ok(indexed_count)
    }
    
    /// Incremental indexing - only index changed files
    pub async fn index_incremental(&mut self, root_path: &Path) -> Result<usize, String> {
        let mut indexed_count = 0;
        let mut errors = Vec::new();
        
        if root_path.is_dir() {
            self.index_directory_recursive_incremental(root_path, &mut indexed_count, &mut errors).await?;
        } else if root_path.is_file() {
            if self.should_index_file(root_path).await? {
                match self.index_file(root_path).await {
                    Ok(_) => indexed_count += 1,
                    Err(e) => errors.push(format!("Failed to index {}: {}", root_path.display(), e)),
                }
            }
        }
        
        if !errors.is_empty() {
            eprintln!("Incremental indexing completed with {} errors", errors.len());
        }
        
        Ok(indexed_count)
    }
    
    pub async fn should_index_file(&self, file_path: &Path) -> Result<bool, String> {
        // Check if file should be skipped
        if self.should_skip_file(file_path) {
            return Ok(false);
        }
        
        // Check if file has been modified since last indexing
        let metadata = std::fs::metadata(file_path)
            .map_err(|e| format!("Failed to get metadata for {}: {}", file_path.display(), e))?;
        
        let modified_time = metadata.modified()
            .map_err(|e| format!("Failed to get modification time: {}", e))?;
        
        let file_key = file_path.to_string_lossy().to_string();
        if let Some(&last_indexed) = self.indexed_files.get(&file_key) {
            // Only re-index if file was modified after last indexing
            return Ok(modified_time > last_indexed);
        }
        
        // New file, should be indexed
        Ok(true)
    }
    
    fn should_skip_file(&self, file_path: &Path) -> bool {
        let path_str = file_path.to_string_lossy();
        
        // Check skip patterns
        for pattern in &self.skip_patterns {
            if pattern.contains('*') {
                // Simple glob matching
                let pattern_parts: Vec<&str> = pattern.split('*').collect();
                if pattern_parts.len() == 2 {
                    if path_str.ends_with(pattern_parts[1]) {
                        return true;
                    }
                }
            } else if path_str.contains(pattern) {
                return true;
            }
        }
        
        false
    }
    
    async fn index_directory_recursive(
        &mut self,
        dir: &Path,
        count: &mut usize,
        errors: &mut Vec<String>,
    ) -> Result<(), String> {
        let entries = match std::fs::read_dir(dir) {
            Ok(entries) => entries,
            Err(e) => {
                errors.push(format!("Failed to read directory {}: {}", dir.display(), e));
                return Ok(()); // Continue with other directories
            }
        };
        
        for entry in entries {
            let entry = match entry {
                Ok(e) => e,
                Err(e) => {
                    errors.push(format!("Failed to read entry in {}: {}", dir.display(), e));
                    continue;
                }
            };
            let path = entry.path();
            
            // Skip hidden files and directories
            if path.file_name()
                .and_then(|n| n.to_str())
                .map(|n| n.starts_with('.'))
                .unwrap_or(false)
            {
                continue;
            }
            
            // Check skip patterns
            if self.should_skip_file(&path) {
                continue;
            }
            
            if path.is_dir() {
                // Recursively index subdirectories
                if let Err(e) = self.index_directory_recursive(&path, count, errors).await {
                    errors.push(format!("Error indexing directory {}: {}", path.display(), e));
                }
            } else if path.is_file() {
                if let Some(language) = ASTParser::detect_language(&path) {
                    match self.index_file(&path).await {
                        Ok(_) => *count += 1,
                        Err(e) => {
                            errors.push(format!("Failed to index {}: {}", path.display(), e));
                            // Continue with other files
                        }
                    }
                }
            }
        }
        
        Ok(())
    }
    
    async fn index_directory_recursive_incremental(
        &mut self,
        dir: &Path,
        count: &mut usize,
        errors: &mut Vec<String>,
    ) -> Result<(), String> {
        let entries = match std::fs::read_dir(dir) {
            Ok(entries) => entries,
            Err(e) => {
                errors.push(format!("Failed to read directory {}: {}", dir.display(), e));
                return Ok(());
            }
        };
        
        for entry in entries {
            let entry = match entry {
                Ok(e) => e,
                Err(e) => {
                    errors.push(format!("Failed to read entry: {}", e));
                    continue;
                }
            };
            let path = entry.path();
            
            if self.should_skip_file(&path) {
                continue;
            }
            
            if path.is_dir() {
                if let Err(e) = self.index_directory_recursive_incremental(&path, count, errors).await {
                    errors.push(format!("Error in incremental indexing: {}", e));
                }
            } else if path.is_file() {
                if let Some(_language) = ASTParser::detect_language(&path) {
                    if let Ok(true) = self.should_index_file(&path).await {
                        match self.index_file(&path).await {
                            Ok(_) => *count += 1,
                            Err(e) => errors.push(format!("Failed to index {}: {}", path.display(), e)),
                        }
                    }
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
        
        // Parse AST (with error recovery)
        let blocks = match self.parser.parse_file(&content, &language) {
            Ok(blocks) => blocks,
            Err(e) => {
                // If parsing fails, still try to index as a single block
                eprintln!("Warning: AST parsing failed for {}: {}", file_path.display(), e);
                vec![CodeBlock {
                    block_type: "file".to_string(),
                    name: file_path.file_name().and_then(|n| n.to_str()).map(|s| s.to_string()),
                    content: content.clone(),
                    start_line: 0,
                    end_line: content.lines().count(),
                    language: language.clone(),
                    docstring: None,
                    decorators: Vec::new(),
                }]
            }
        };
        
        // Validate blocks before storing
        let valid_blocks: Vec<CodeBlock> = blocks.into_iter()
            .filter(|block| {
                // Filter out blocks that are too small or invalid
                block.content.len() >= 10 && !block.content.trim().is_empty()
            })
            .collect();
        
        if valid_blocks.is_empty() {
            return Err("No valid blocks found in file".to_string());
        }
        
        // Store in database
        let relative_path = file_path.to_string_lossy().to_string();
        self.storage.store_file(
            &self.project_id,
            &relative_path,
            &language,
            &valid_blocks,
        ).await
            .map_err(|e| format!("Failed to store: {}", e))?;
        
        // Track indexed file
        let metadata = std::fs::metadata(file_path)
            .map_err(|e| format!("Failed to get metadata: {}", e))?;
        if let Ok(modified_time) = metadata.modified() {
            self.indexed_files.insert(relative_path.clone(), modified_time);
        }
        
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
            .map_err(|e| format!("Failed to remove: {}", e))?;
        
        // Remove from tracked files
        self.indexed_files.remove(&relative_path);
        
        Ok(())
    }
    
    /// Validate index integrity
    pub async fn validate_index(&self) -> Result<IndexValidationResult, String> {
        let mut result = IndexValidationResult {
            total_files: 0,
            total_blocks: 0,
            orphaned_blocks: 0,
            missing_files: Vec::new(),
            errors: Vec::new(),
        };
        
        // This would require additional storage methods to check integrity
        // For now, return a basic validation
        Ok(result)
    }
    
    /// Repair index (remove orphaned entries, etc.)
    pub async fn repair_index(&mut self) -> Result<usize, String> {
        // Implementation would clean up orphaned blocks, missing files, etc.
        // For now, return 0 (no repairs needed)
        Ok(0)
    }
}

#[derive(Debug)]
pub struct IndexValidationResult {
    pub total_files: usize,
    pub total_blocks: usize,
    pub orphaned_blocks: usize,
    pub missing_files: Vec<String>,
    pub errors: Vec<String>,
}
