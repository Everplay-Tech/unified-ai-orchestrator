/// Input validation and sanitization utilities

use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ValidationError {
    #[error("Input too long: max {max} characters, got {actual}")]
    InputTooLong { max: usize, actual: usize },
    
    #[error("Invalid characters detected")]
    InvalidCharacters,
    
    #[error("Path traversal detected: {0}")]
    PathTraversal(String),
    
    #[error("Empty input not allowed")]
    EmptyInput,
    
    #[error("Invalid format: {0}")]
    InvalidFormat(String),
}

/// Validate user input for security
pub fn validate_input(input: &str, max_length: usize) -> Result<(), ValidationError> {
    if input.is_empty() {
        return Err(ValidationError::EmptyInput);
    }
    
    if input.len() > max_length {
        return Err(ValidationError::InputTooLong {
            max: max_length,
            actual: input.len(),
        });
    }
    
    // Check for null bytes (potential injection)
    if input.contains('\0') {
        return Err(ValidationError::InvalidCharacters);
    }
    
    // Check for control characters (except newline, tab, carriage return)
    if input.chars().any(|c| {
        c.is_control() && c != '\n' && c != '\t' && c != '\r'
    }) {
        return Err(ValidationError::InvalidCharacters);
    }
    
    Ok(())
}

/// Sanitize and validate file paths to prevent path traversal
pub fn sanitize_path(base_path: &Path, user_path: &str) -> Result<PathBuf, ValidationError> {
    // Remove any null bytes
    let cleaned = user_path.replace('\0', "");
    
    // Normalize the path
    let path = PathBuf::from(&cleaned);
    
    // Resolve relative to base path
    let resolved = base_path.join(&path);
    
    // Canonicalize to resolve any ".." components
    let canonical = resolved.canonicalize()
        .map_err(|_| ValidationError::PathTraversal(user_path.to_string()))?;
    
    // Ensure the canonical path is still within base_path
    let base_canonical = base_path.canonicalize()
        .map_err(|_| ValidationError::PathTraversal(user_path.to_string()))?;
    
    if !canonical.starts_with(&base_canonical) {
        return Err(ValidationError::PathTraversal(user_path.to_string()));
    }
    
    Ok(canonical)
}

/// Validate SQL injection patterns (basic check)
pub fn validate_sql_safe(input: &str) -> Result<(), ValidationError> {
    // Check for common SQL injection patterns
    let dangerous_patterns = [
        "';",
        "\";",
        "--",
        "/*",
        "*/",
        "xp_",
        "sp_",
        "exec(",
        "execute(",
        "union select",
        "union all select",
    ];
    
    let lower_input = input.to_lowercase();
    for pattern in &dangerous_patterns {
        if lower_input.contains(pattern) {
            return Err(ValidationError::InvalidFormat(
                format!("Potentially dangerous SQL pattern detected: {}", pattern)
            ));
        }
    }
    
    Ok(())
}

/// Validate command injection patterns
pub fn validate_command_safe(input: &str) -> Result<(), ValidationError> {
    // Check for command injection patterns
    let dangerous_patterns = [
        "&&",
        "||",
        ";",
        "|",
        "`",
        "$(",
        "<(",
        ">",
        "<",
        "\n",
    ];
    
    for pattern in &dangerous_patterns {
        if input.contains(pattern) {
            return Err(ValidationError::InvalidFormat(
                format!("Potentially dangerous command pattern detected: {}", pattern)
            ));
        }
    }
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_validate_input() {
        assert!(validate_input("hello", 100).is_ok());
        assert!(validate_input("", 100).is_err());
        assert!(validate_input(&"a".repeat(101), 100).is_err());
    }
    
    #[test]
    fn test_sanitize_path() {
        let base = Path::new("/safe/base");
        
        // Valid relative path
        assert!(sanitize_path(base, "subdir/file.txt").is_ok());
        
        // Path traversal attempt
        assert!(sanitize_path(base, "../../etc/passwd").is_err());
    }
    
    #[test]
    fn test_validate_sql_safe() {
        assert!(validate_sql_safe("SELECT * FROM users").is_ok());
        assert!(validate_sql_safe("'; DROP TABLE users--").is_err());
    }
    
    #[test]
    fn test_validate_command_safe() {
        assert!(validate_command_safe("echo hello").is_ok());
        assert!(validate_command_safe("echo hello; rm -rf /").is_err());
    }
}
