/// Database migration system

pub mod runner;

mod migrations;

pub use runner::{MigrationRunner, Migration, MigrationError};

use sqlx::sqlite::SqlitePool;

/// Register all migrations
pub fn register_migrations(runner: &mut MigrationRunner) {
    use migrations::*;
    
    runner.add_migration(Migration {
        version: 1,
        name: "initial_schema".to_string(),
        up: Box::new(|pool| Box::pin(m001_initial_schema::up(pool))),
        down: Box::new(|pool| Box::pin(m001_initial_schema::down(pool))),
    });
    
    runner.add_migration(Migration {
        version: 2,
        name: "add_cost_tracking".to_string(),
        up: Box::new(|pool| Box::pin(m002_add_cost_tracking::up(pool))),
        down: Box::new(|pool| Box::pin(m002_add_cost_tracking::down(pool))),
    });
    
    runner.add_migration(Migration {
        version: 3,
        name: "add_indexing".to_string(),
        up: Box::new(|pool| Box::pin(m003_add_indexing::up(pool))),
        down: Box::new(|pool| Box::pin(m003_add_indexing::down(pool))),
    });
    
    runner.add_migration(Migration {
        version: 4,
        name: "add_security".to_string(),
        up: Box::new(|pool| Box::pin(m004_add_security::up(pool))),
        down: Box::new(|pool| Box::pin(m004_add_security::down(pool))),
    });
    
    runner.add_migration(Migration {
        version: 5,
        name: "add_codeblock_metadata".to_string(),
        up: Box::new(|pool| Box::pin(m005_add_codeblock_metadata::up(pool))),
        down: Box::new(|pool| Box::pin(m005_add_codeblock_metadata::down(pool))),
    });
}

mod migrations {
    pub mod m001_initial_schema {
        use sqlx::sqlite::SqlitePool;
        pub async fn up(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            sqlx::query(
                r#"
                CREATE TABLE IF NOT EXISTS contexts (
                    conversation_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                "#,
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id)"
            )
            .execute(pool)
            .await?;
            
            Ok(())
        }
        
        pub async fn down(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            sqlx::query("DROP INDEX IF EXISTS idx_contexts_project_id")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP TABLE IF EXISTS contexts")
                .execute(pool)
                .await?;
            
            Ok(())
        }
    }
    
    pub mod m002_add_cost_tracking {
        use sqlx::sqlite::SqlitePool;
        pub async fn up(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            sqlx::query(
                r#"
                CREATE TABLE IF NOT EXISTS cost_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    model TEXT,
                    tokens_input INTEGER,
                    tokens_output INTEGER,
                    cost_usd REAL NOT NULL,
                    project_id TEXT,
                    user_id TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                "#,
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_cost_records_tool ON cost_records(tool)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_cost_records_project_id ON cost_records(project_id)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_cost_records_user_id ON cost_records(user_id)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_cost_records_created_at ON cost_records(created_at)"
            )
            .execute(pool)
            .await?;
            
            Ok(())
        }
        
        pub async fn down(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            sqlx::query("DROP INDEX IF EXISTS idx_cost_records_created_at")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_cost_records_user_id")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_cost_records_project_id")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_cost_records_tool")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP TABLE IF EXISTS cost_records")
                .execute(pool)
                .await?;
            
            Ok(())
        }
    }
    
    pub mod m003_add_indexing {
        use sqlx::sqlite::SqlitePool;
        pub async fn up(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            sqlx::query(
                r#"
                CREATE TABLE IF NOT EXISTS indexed_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    language TEXT,
                    file_hash TEXT,
                    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_id, file_path)
                )
                "#,
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                r#"
                CREATE TABLE IF NOT EXISTS code_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    block_type TEXT NOT NULL,
                    name TEXT,
                    content TEXT NOT NULL,
                    start_line INTEGER,
                    end_line INTEGER,
                    embedding BLOB,
                    FOREIGN KEY(file_id) REFERENCES indexed_files(id) ON DELETE CASCADE
                )
                "#,
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_indexed_files_project_id ON indexed_files(project_id)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_code_blocks_file_id ON code_blocks(file_id)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_code_blocks_type ON code_blocks(block_type)"
            )
            .execute(pool)
            .await?;
            
            Ok(())
        }
        
        pub async fn down(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            sqlx::query("DROP INDEX IF EXISTS idx_code_blocks_type")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_code_blocks_file_id")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_indexed_files_project_id")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP TABLE IF EXISTS code_blocks")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP TABLE IF EXISTS indexed_files")
                .execute(pool)
                .await?;
            
            Ok(())
        }
    }
    
    pub mod m004_add_security {
        use sqlx::sqlite::SqlitePool;
        pub async fn up(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            sqlx::query(
                r#"
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    api_key_hash TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                "#,
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                r#"
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                "#,
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                r#"
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                "#,
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type)"
            )
            .execute(pool)
            .await?;
            
            sqlx::query(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)"
            )
            .execute(pool)
            .await?;
            
            Ok(())
        }
        
        pub async fn down(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            sqlx::query("DROP INDEX IF EXISTS idx_audit_logs_created_at")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_audit_logs_event_type")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_audit_logs_user_id")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_sessions_expires_at")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_sessions_user_id")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_users_email")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP INDEX IF EXISTS idx_users_username")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP TABLE IF EXISTS audit_logs")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP TABLE IF EXISTS sessions")
                .execute(pool)
                .await?;
            
            sqlx::query("DROP TABLE IF EXISTS users")
                .execute(pool)
                .await?;
            
            Ok(())
        }
    }
    
    pub mod m005_add_codeblock_metadata {
        use sqlx::sqlite::SqlitePool;
        pub async fn up(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            // Add docstring column (nullable)
            sqlx::query(
                "ALTER TABLE code_blocks ADD COLUMN docstring TEXT"
            )
            .execute(pool)
            .await?;
            
            // Add decorators column (nullable, stores JSON array)
            sqlx::query(
                "ALTER TABLE code_blocks ADD COLUMN decorators TEXT"
            )
            .execute(pool)
            .await?;
            
            Ok(())
        }
        
        pub async fn down(pool: &SqlitePool) -> Result<(), sqlx::Error> {
            // SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
            // For now, we'll just note that rollback requires manual intervention
            // In production, you'd use a more sophisticated migration strategy
            Ok(())
        }
    }
}
