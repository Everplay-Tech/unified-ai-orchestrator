use super::Context;
use crate::error::{Result, OrchestratorError};
use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};
use std::path::PathBuf;

pub struct ContextStorage {
    pool: SqlitePool,
}

impl ContextStorage {
    pub async fn new(db_path: PathBuf) -> Result<Self> {
        // Ensure parent directory exists
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let pool = SqlitePoolOptions::new()
            .max_connections(5)
            .connect_with(
                sqlx::sqlite::SqliteConnectOptions::new()
                    .filename(&db_path)
                    .create_if_missing(true),
            )
            .await
            .map_err(OrchestratorError::from)?;

        // Create tables
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS contexts (
                conversation_id TEXT PRIMARY KEY,
                project_id TEXT,
                data TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            "#,
        )
        .execute(&pool)
        .await
        .map_err(OrchestratorError::from)?;

        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES contexts(conversation_id)
            )
            "#,
        )
        .execute(&pool)
        .await
        .map_err(OrchestratorError::from)?;

        Ok(Self { pool })
    }

    pub async fn save_context(&self, context: &Context) -> Result<()> {
        let data = serde_json::to_string(context)
            .map_err(OrchestratorError::from)?;
        let updated_at = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;

        sqlx::query(
            r#"
            INSERT OR REPLACE INTO contexts (conversation_id, project_id, data, updated_at)
            VALUES (?1, ?2, ?3, ?4)
            "#,
        )
        .bind(&context.conversation_id)
        .bind(&context.project_id)
        .bind(&data)
        .bind(updated_at)
        .execute(&self.pool)
        .await
        .map_err(OrchestratorError::from)?;

        Ok(())
    }

    pub async fn load_context(&self, conversation_id: &str) -> Result<Option<Context>> {
        let row = sqlx::query_as::<_, (String,)>(
            "SELECT data FROM contexts WHERE conversation_id = ?1",
        )
        .bind(conversation_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(OrchestratorError::from)?;

        if let Some((data,)) = row {
            let context: Context = serde_json::from_str(&data)
                .map_err(OrchestratorError::from)?;
            Ok(Some(context))
        } else {
            Ok(None)
        }
    }
}
