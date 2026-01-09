/// Index storage and persistence

use crate::indexer::parser::CodeBlock;
use sqlx::sqlite::SqlitePool;
use crate::error::Result;

pub struct IndexStorage {
    pool: SqlitePool,
}

impl IndexStorage {
    pub fn new(pool: SqlitePool) -> Self {
        Self { pool }
    }
    
    pub async fn store_file(
        &self,
        project_id: &str,
        file_path: &str,
        language: &str,
        blocks: &[CodeBlock],
    ) -> Result<()> {
        // Calculate file hash (simple for now)
        let file_hash = format!("{:x}", md5::compute(format!("{}{}", project_id, file_path)));
        
        // Insert or update file record
        sqlx::query(
            r#"
            INSERT INTO indexed_files (project_id, file_path, language, file_hash)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(project_id, file_path) DO UPDATE SET
                language = ?,
                file_hash = ?,
                indexed_at = CURRENT_TIMESTAMP
            "#,
        )
        .bind(project_id)
        .bind(file_path)
        .bind(language)
        .bind(&file_hash)
        .bind(language)
        .bind(&file_hash)
        .execute(&self.pool)
        .await?;
        
        // Get file ID
        let file_id: (i64,) = sqlx::query_as(
            "SELECT id FROM indexed_files WHERE project_id = ? AND file_path = ?"
        )
        .bind(project_id)
        .bind(file_path)
        .fetch_one(&self.pool)
        .await?;
        
        // Delete old blocks
        sqlx::query("DELETE FROM code_blocks WHERE file_id = ?")
            .bind(file_id.0)
            .execute(&self.pool)
            .await?;
        
        // Insert new blocks
        for block in blocks {
            sqlx::query(
                r#"
                INSERT INTO code_blocks (file_id, block_type, name, content, start_line, end_line)
                VALUES (?, ?, ?, ?, ?, ?)
                "#,
            )
            .bind(file_id.0)
            .bind(&block.block_type)
            .bind(&block.name)
            .bind(&block.content)
            .bind(block.start_line as i64)
            .bind(block.end_line as i64)
            .execute(&self.pool)
            .await?;
        }
        
        Ok(())
    }
    
    pub async fn remove_file(&self, project_id: &str, file_path: &str) -> Result<()> {
        // Get file ID
        let file_id_result: Option<(i64,)> = sqlx::query_as(
            "SELECT id FROM indexed_files WHERE project_id = ? AND file_path = ?"
        )
        .bind(project_id)
        .bind(file_path)
        .fetch_optional(&self.pool)
        .await?;
        
        if let Some((file_id,)) = file_id_result {
            // Delete blocks (CASCADE should handle this, but explicit is better)
            sqlx::query("DELETE FROM code_blocks WHERE file_id = ?")
                .bind(file_id)
                .execute(&self.pool)
                .await?;
            
            // Delete file record
            sqlx::query("DELETE FROM indexed_files WHERE id = ?")
                .bind(file_id)
                .execute(&self.pool)
                .await?;
        }
        
        Ok(())
    }
    
    pub async fn search_blocks(
        &self,
        project_id: &str,
        query: &str,
        limit: usize,
    ) -> Result<Vec<(String, String, String, i64, i64)>> {
        // Simple keyword search for now (will be enhanced with semantic search)
        let results = sqlx::query_as::<_, (String, String, String, i64, i64)>(
            r#"
            SELECT f.file_path, c.block_type, c.name, c.start_line, c.end_line
            FROM code_blocks c
            JOIN indexed_files f ON c.file_id = f.id
            WHERE f.project_id = ?
            AND (c.content LIKE ? OR c.name LIKE ?)
            LIMIT ?
            "#,
        )
        .bind(project_id)
        .bind(format!("%{}%", query))
        .bind(format!("%{}%", query))
        .bind(limit as i64)
        .fetch_all(&self.pool)
        .await?;
        
        Ok(results)
    }
}
