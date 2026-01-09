use super::{Context, ContextStorage};
use crate::error::Result;

pub struct ContextManager {
    storage: ContextStorage,
}

impl ContextManager {
    pub fn new(storage: ContextStorage) -> Self {
        Self { storage }
    }

    pub async fn get_or_create_context(
        &self,
        conversation_id: Option<String>,
        project_id: Option<String>,
    ) -> Result<Context> {
        if let Some(id) = conversation_id {
            if let Some(context) = self.storage.load_context(&id).await? {
                return Ok(context);
            }
        }

        let context = Context::new(project_id);
        let id = context.conversation_id.clone();
        self.storage.save_context(&context).await?;
        Ok(context)
    }

    pub async fn update_context(&self, context: &Context) -> Result<()> {
        self.storage.save_context(context).await
    }

    pub async fn get_context(&self, conversation_id: &str) -> Result<Option<Context>> {
        self.storage.load_context(conversation_id).await
    }
}
