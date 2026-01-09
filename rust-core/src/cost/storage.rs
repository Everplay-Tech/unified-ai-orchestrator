use crate::error::{Result, OrchestratorError};
use chrono::{DateTime, Utc};
use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};
use std::path::PathBuf;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostRecord {
    pub id: Option<i64>,
    pub tool: String,
    pub model: String,
    pub input_tokens: u32,
    pub output_tokens: u32,
    pub cost_usd: f64,
    pub timestamp: DateTime<Utc>,
    pub user_id: Option<String>,
    pub project_id: Option<String>,
    pub conversation_id: Option<String>,
}

pub struct CostStorage {
    pool: SqlitePool,
}

impl CostStorage {
    pub async fn new(db_path: PathBuf) -> Result<Self> {
        if let Some(parent) = db_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(OrchestratorError::from)?;
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

        // Create cost_records table
        sqlx::query(
            r#"
            CREATE TABLE IF NOT EXISTS cost_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                timestamp INTEGER NOT NULL,
                user_id TEXT,
                project_id TEXT,
                conversation_id TEXT
            )
            "#,
        )
        .execute(&pool)
        .await
        .map_err(OrchestratorError::from)?;

        // Create indexes
        sqlx::query(
            "CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_records(timestamp)"
        )
        .execute(&pool)
        .await
        .map_err(OrchestratorError::from)?;

        sqlx::query(
            "CREATE INDEX IF NOT EXISTS idx_cost_tool ON cost_records(tool)"
        )
        .execute(&pool)
        .await
        .map_err(OrchestratorError::from)?;

        sqlx::query(
            "CREATE INDEX IF NOT EXISTS idx_cost_user ON cost_records(user_id)"
        )
        .execute(&pool)
        .await
        .map_err(OrchestratorError::from)?;

        Ok(Self { pool })
    }

    pub async fn record_cost(&self, record: &CostRecord) -> Result<()> {
        sqlx::query(
            r#"
            INSERT INTO cost_records 
            (tool, model, input_tokens, output_tokens, cost_usd, timestamp, user_id, project_id, conversation_id)
            VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)
            "#,
        )
        .bind(&record.tool)
        .bind(&record.model)
        .bind(record.input_tokens as i64)
        .bind(record.output_tokens as i64)
        .bind(record.cost_usd)
        .bind(record.timestamp.timestamp())
        .bind(&record.user_id)
        .bind(&record.project_id)
        .bind(&record.conversation_id)
        .execute(&self.pool)
        .await
        .map_err(OrchestratorError::from)?;

        Ok(())
    }

    pub async fn get_total_cost(
        &self,
        start: DateTime<Utc>,
        end: DateTime<Utc>,
        user_id: Option<&str>,
        project_id: Option<&str>,
    ) -> Result<f64> {
        let mut query = "SELECT SUM(cost_usd) as total FROM cost_records WHERE timestamp >= ?1 AND timestamp <= ?2".to_string();
        
        let mut query_builder = sqlx::query_as::<_, (Option<f64>,)>(
            &query
        )
        .bind(start.timestamp())
        .bind(end.timestamp());

        if let Some(uid) = user_id {
            query.push_str(" AND user_id = ?3");
            query_builder = query_builder.bind(uid);
        }

        if let Some(pid) = project_id {
            query.push_str(" AND project_id = ?4");
            query_builder = query_builder.bind(pid);
        }

        let row = query_builder
            .fetch_one(&self.pool)
            .await
            .map_err(OrchestratorError::from)?;

        Ok(row.0.unwrap_or(0.0))
    }
}
