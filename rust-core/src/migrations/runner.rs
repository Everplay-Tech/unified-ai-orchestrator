/// Migration runner for database schema versioning

use sqlx::{sqlite::SqlitePool, Executor};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum MigrationError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    
    #[error("Migration {version} already applied")]
    AlreadyApplied { version: u32 },
    
    #[error("Migration {version} not found")]
    NotFound { version: u32 },
    
    #[error("Migration execution failed: {0}")]
    ExecutionFailed(String),
    
    #[error("Invalid migration: {0}")]
    InvalidMigration(String),
}

pub struct Migration {
    pub version: u32,
    pub name: String,
    pub up: fn(&SqlitePool) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), sqlx::Error>> + Send>>,
    pub down: fn(&SqlitePool) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<(), sqlx::Error>> + Send>>,
}

pub struct MigrationRunner {
    pool: SqlitePool,
    migrations: Vec<Migration>,
}

impl MigrationRunner {
    pub fn new(pool: SqlitePool) -> Self {
        Self {
            pool,
            migrations: Vec::new(),
        }
    }
    
    pub fn add_migration(&mut self, migration: Migration) {
        self.migrations.push(migration);
        // Sort by version
        self.migrations.sort_by_key(|m| m.version);
    }
    
    pub async fn ensure_migrations_table(&self) -> Result<(), MigrationError> {
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            "#,
        )
        .execute(&self.pool)
        .await?;
        
        Ok(())
    }
    
    pub async fn get_current_version(&self) -> Result<Option<u32>, MigrationError> {
        self.ensure_migrations_table().await?;
        
        let result = sqlx::query_as::<_, (i64,)>(
            "SELECT MAX(version) FROM schema_migrations"
        )
        .fetch_optional(&self.pool)
        .await?;
        
        Ok(result.map(|(v,)| v as u32))
    }
    
    pub async fn get_applied_migrations(&self) -> Result<HashMap<u32, String>, MigrationError> {
        self.ensure_migrations_table().await?;
        
        let rows = sqlx::query_as::<_, (i64, String)>(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        )
        .fetch_all(&self.pool)
        .await?;
        
        Ok(rows.into_iter().map(|(v, n)| (v as u32, n)).collect())
    }
    
    pub async fn migrate_up(&self, target_version: Option<u32>) -> Result<(), MigrationError> {
        self.ensure_migrations_table().await?;
        
        let current_version = self.get_current_version().await?;
        let applied = self.get_applied_migrations().await?;
        
        let target = target_version.unwrap_or_else(|| {
            self.migrations
                .iter()
                .map(|m| m.version)
                .max()
                .unwrap_or(0)
        });
        
        for migration in &self.migrations {
            if migration.version <= target {
                // Check if already applied
                if applied.contains_key(&migration.version) {
                    continue;
                }
                
                // Check for gaps
                if let Some(current) = current_version {
                    if migration.version != current + 1 {
                        return Err(MigrationError::InvalidMigration(
                            format!(
                                "Migration {} cannot be applied: expected version {}",
                                migration.version,
                                current + 1
                            )
                        ));
                    }
                }
                
                // Execute migration
                (migration.up)(&self.pool).await.map_err(|e| {
                    MigrationError::ExecutionFailed(format!(
                        "Migration {} ({}) failed: {}",
                        migration.version, migration.name, e
                    ))
                })?;
                
                // Record migration
                sqlx::query(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)"
                )
                .bind(migration.version as i64)
                .bind(&migration.name)
                .execute(&self.pool)
                .await?;
            }
        }
        
        Ok(())
    }
    
    pub async fn migrate_down(&self, target_version: u32) -> Result<(), MigrationError> {
        self.ensure_migrations_table().await?;
        
        let current_version = self.get_current_version().await?
            .ok_or_else(|| MigrationError::NotFound { version: 0 })?;
        
        // Find migrations to rollback (in reverse order)
        let migrations_to_rollback: Vec<_> = self.migrations
            .iter()
            .rev()
            .filter(|m| m.version > target_version && m.version <= current_version)
            .collect();
        
        for migration in migrations_to_rollback {
            // Execute rollback
            (migration.down)(&self.pool).await.map_err(|e| {
                MigrationError::ExecutionFailed(format!(
                    "Rollback of migration {} ({}) failed: {}",
                    migration.version, migration.name, e
                ))
            })?;
            
            // Remove migration record
            sqlx::query("DELETE FROM schema_migrations WHERE version = ?")
                .bind(migration.version as i64)
                .execute(&self.pool)
                .await?;
        }
        
        Ok(())
    }
    
    pub async fn status(&self) -> Result<Vec<(u32, String, bool)>, MigrationError> {
        self.ensure_migrations_table().await?;
        
        let applied = self.get_applied_migrations().await?;
        
        let mut status = Vec::new();
        for migration in &self.migrations {
            let applied = applied.contains_key(&migration.version);
            status.push((migration.version, migration.name.clone(), applied));
        }
        
        Ok(status)
    }
}
