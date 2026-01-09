use anyhow::Result;
use std::collections::HashMap;
use std::path::PathBuf;
use tokio::fs;

pub struct KeyValueStore {
    path: PathBuf,
    cache: HashMap<String, String>,
}

impl KeyValueStore {
    pub async fn new(path: PathBuf) -> Result<Self> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).await?;
        }

        let cache = if path.exists() {
            let content = fs::read_to_string(&path).await?;
            toml::from_str(&content).unwrap_or_default()
        } else {
            HashMap::new()
        };

        Ok(Self { path, cache })
    }

    pub async fn get(&self, key: &str) -> Option<&String> {
        self.cache.get(key)
    }

    pub async fn set(&mut self, key: String, value: String) -> Result<()> {
        self.cache.insert(key, value);
        self.save().await
    }

    async fn save(&self) -> Result<()> {
        let content = toml::to_string(&self.cache)?;
        fs::write(&self.path, content).await?;
        Ok(())
    }
}
