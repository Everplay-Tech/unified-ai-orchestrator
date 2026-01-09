use thiserror::Error;
use sqlx::Error as SqlxError;
use reqwest::Error as ReqwestError;
use serde_json::Error as JsonError;
use std::io::Error as IoError;

#[derive(Error, Debug)]
pub enum OrchestratorError {
    #[error("Storage error: {0}")]
    Storage(#[from] SqlxError),
    
    #[error("Network error: {0}")]
    Network(#[from] ReqwestError),
    
    #[error("Serialization error: {0}")]
    Serialization(#[from] JsonError),
    
    #[error("IO error: {0}")]
    Io(#[from] IoError),
    
    #[error("Tool unavailable: {0}")]
    ToolUnavailable(String),
    
    #[error("Rate limit exceeded: {0}")]
    RateLimitExceeded(String),
    
    #[error("Context too large: {0} tokens (max: {1})")]
    ContextTooLarge(usize, usize),
    
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
    
    #[error("Authentication failed: {0}")]
    Authentication(String),
    
    #[error("Authorization denied: {0}")]
    Authorization(String),
    
    #[error("Timeout: {0}")]
    Timeout(String),
    
    #[error("Circuit breaker open: {0}")]
    CircuitBreakerOpen(String),
    
    #[error("Invalid input: {0}")]
    InvalidInput(String),
    
    #[error("Indexing error: {0}")]
    Indexing(String),
    
    #[error("Unknown error: {0}")]
    Unknown(String),
}

impl From<anyhow::Error> for OrchestratorError {
    fn from(err: anyhow::Error) -> Self {
        OrchestratorError::Unknown(err.to_string())
    }
}

impl From<OrchestratorError> for pyo3::PyErr {
    fn from(err: OrchestratorError) -> Self {
        use pyo3::exceptions::*;
        match err {
            OrchestratorError::Storage(e) => PyRuntimeError::new_err(format!("Storage error: {}", e)),
            OrchestratorError::Network(e) => PyConnectionError::new_err(format!("Network error: {}", e)),
            OrchestratorError::Serialization(e) => PyValueError::new_err(format!("Serialization error: {}", e)),
            OrchestratorError::Io(e) => PyIOError::new_err(format!("IO error: {}", e)),
            OrchestratorError::ToolUnavailable(msg) => PyRuntimeError::new_err(msg),
            OrchestratorError::RateLimitExceeded(msg) => PyRuntimeError::new_err(msg),
            OrchestratorError::ContextTooLarge(current, max) => {
                PyValueError::new_err(format!("Context too large: {} tokens (max: {})", current, max))
            }
            OrchestratorError::InvalidConfig(msg) => PyValueError::new_err(format!("Invalid config: {}", msg)),
            OrchestratorError::Authentication(msg) => PyPermissionError::new_err(format!("Authentication failed: {}", msg)),
            OrchestratorError::Authorization(msg) => PyPermissionError::new_err(format!("Authorization denied: {}", msg)),
            OrchestratorError::Timeout(msg) => PyTimeoutError::new_err(msg),
            OrchestratorError::CircuitBreakerOpen(msg) => PyRuntimeError::new_err(format!("Circuit breaker open: {}", msg)),
            OrchestratorError::InvalidInput(msg) => PyValueError::new_err(format!("Invalid input: {}", msg)),
            OrchestratorError::Indexing(msg) => PyRuntimeError::new_err(format!("Indexing error: {}", msg)),
            OrchestratorError::Unknown(msg) => PyRuntimeError::new_err(format!("Unknown error: {}", msg)),
        }
    }
}

pub type Result<T> = std::result::Result<T, OrchestratorError>;
