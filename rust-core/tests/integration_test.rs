/// Integration tests for Rust core

#[cfg(test)]
mod tests {
    use rust_core::context::{Context, ContextManager, ContextStorage};
    use rust_core::error::Result;
    use std::path::PathBuf;
    
    #[tokio::test]
    async fn test_context_storage() {
        let db_path = PathBuf::from(":memory:");
        let storage = ContextStorage::new(db_path).await.unwrap();
        
        let mut context = Context::new(None);
        context.add_message("user".to_string(), "Hello".to_string());
        
        storage.save_context(&context).await.unwrap();
        
        let loaded = storage.load_context(&context.conversation_id).await.unwrap();
        assert!(loaded.is_some());
        let loaded = loaded.unwrap();
        assert_eq!(loaded.messages.len(), 1);
    }
    
    #[tokio::test]
    async fn test_context_manager() {
        let db_path = PathBuf::from(":memory:");
        let storage = ContextStorage::new(db_path).await.unwrap();
        let manager = ContextManager::new(storage);
        
        let context = manager.get_or_create_context(None, None).await.unwrap();
        assert!(!context.conversation_id.is_empty());
    }
}
