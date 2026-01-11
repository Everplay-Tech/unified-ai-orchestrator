/// Tests for database migrations

#[cfg(test)]
mod tests {
    use rust_core::migrations::{MigrationRunner, Migration, register_migrations};
    use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};
    use std::time::Duration;

    async fn create_test_pool() -> SqlitePool {
        SqlitePoolOptions::new()
            .max_connections(1)
            .acquire_timeout(Duration::from_secs(5))
            .connect(":memory:")
            .await
            .expect("Failed to create test pool")
    }

    #[tokio::test]
    async fn test_migration_runner_initialization() {
        let pool = create_test_pool().await;
        let mut runner = MigrationRunner::new(pool);
        
        register_migrations(&mut runner);
        
        // Runner should have migrations registered
        assert!(runner.migrations.len() > 0);
    }

    #[tokio::test]
    async fn test_migration_up() {
        let pool = create_test_pool().await;
        let mut runner = MigrationRunner::new(pool);
        
        register_migrations(&mut runner);
        
        // Run migrations
        runner.migrate_up(None).await.expect("Migration should succeed");
        
        // Check current version
        let current_version = runner.get_current_version().await.expect("Should get version");
        assert!(current_version.is_some());
        assert!(current_version.unwrap() > 0);
    }

    #[tokio::test]
    async fn test_migration_target_version() {
        let pool = create_test_pool().await;
        let mut runner = MigrationRunner::new(pool);
        
        register_migrations(&mut runner);
        
        // Migrate to version 2
        runner.migrate_up(Some(2)).await.expect("Migration should succeed");
        
        let current_version = runner.get_current_version().await.expect("Should get version");
        assert_eq!(current_version, Some(2));
    }

    #[tokio::test]
    async fn test_migration_rollback() {
        let pool = create_test_pool().await;
        let mut runner = MigrationRunner::new(pool);
        
        register_migrations(&mut runner);
        
        // Run migrations up
        runner.migrate_up(None).await.expect("Migration should succeed");
        let current_version_before = runner.get_current_version().await.expect("Should get version");
        assert!(current_version_before.is_some());
        assert!(current_version_before.unwrap() > 1);
        
        // Rollback to version 1
        runner.migrate_down(1).await.expect("Rollback should succeed");
        let current_version_after = runner.get_current_version().await.expect("Should get version");
        assert_eq!(current_version_after, Some(1));
    }

    #[tokio::test]
    async fn test_migration_applied_migrations() {
        let pool = create_test_pool().await;
        let mut runner = MigrationRunner::new(pool);
        
        register_migrations(&mut runner);
        
        // Run migrations
        runner.migrate_up(None).await.expect("Migration should succeed");
        
        // Get applied migrations
        let applied = runner.get_applied_migrations().await.expect("Should get applied migrations");
        assert!(applied.len() > 0);
    }

    #[tokio::test]
    async fn test_migration_idempotency() {
        let pool = create_test_pool().await;
        let mut runner = MigrationRunner::new(pool);
        
        register_migrations(&mut runner);
        
        // Run migrations twice
        runner.migrate_up(None).await.expect("First migration should succeed");
        let version_after_first = runner.get_current_version().await.expect("Should get version");
        
        runner.migrate_up(None).await.expect("Second migration should succeed");
        let version_after_second = runner.get_current_version().await.expect("Should get version");
        
        // Versions should be the same (idempotent)
        assert_eq!(version_after_first, version_after_second);
    }

    #[tokio::test]
    async fn test_migration_error_handling() {
        let pool = create_test_pool().await;
        let mut runner = MigrationRunner::new(pool);
        
        // Add invalid migration
        runner.add_migration(Migration {
            version: 999,
            name: "invalid".to_string(),
            up: Box::new(|_pool| {
                Box::pin(async move {
                    sqlx::query("INVALID SQL SYNTAX!!!").execute(_pool).await?;
                    Ok(())
                })
            }),
            down: Box::new(|_pool| {
                Box::pin(async move {
                    Ok(())
                })
            }),
        });
        
        // Should fail
        let result = runner.migrate_up(None).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_migration_ensures_table() {
        let pool = create_test_pool().await;
        let runner = MigrationRunner::new(pool);
        
        // Ensure migrations table exists
        runner.ensure_migrations_table().await.expect("Should create table");
        
        // Check that table exists by querying it
        let result = sqlx::query("SELECT COUNT(*) FROM schema_migrations")
            .fetch_one(&runner.pool)
            .await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_migration_version_tracking() {
        let pool = create_test_pool().await;
        let mut runner = MigrationRunner::new(pool);
        
        register_migrations(&mut runner);
        
        // Run migrations one by one and verify version
        let total_migrations = runner.migrations.len();
        for i in 1..=total_migrations.min(4) {
            runner.migrate_up(Some(i as u32)).await.expect("Migration should succeed");
            let current_version = runner.get_current_version().await.expect("Should get version");
            assert_eq!(current_version, Some(i as u32));
        }
    }
}
