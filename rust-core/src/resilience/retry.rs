use crate::error::OrchestratorError;
use async_trait::async_trait;
use std::time::Duration;
use std::fmt::Debug;

#[async_trait]
pub trait RetryPolicy: Send + Sync + Debug {
    async fn should_retry(&self, attempt: u32, error: &OrchestratorError) -> bool;
    fn delay(&self, attempt: u32) -> Duration;
    fn max_attempts(&self) -> u32;
}

#[derive(Debug, Clone)]
pub struct ExponentialBackoffRetry {
    max_attempts: u32,
    initial_delay: Duration,
    max_delay: Duration,
    jitter: bool,
}

impl ExponentialBackoffRetry {
    pub fn new(max_attempts: u32, initial_delay: Duration, max_delay: Duration) -> Self {
        Self {
            max_attempts,
            initial_delay,
            max_delay,
            jitter: true,
        }
    }

    pub fn with_jitter(mut self, jitter: bool) -> Self {
        self.jitter = jitter;
        self
    }
}

#[async_trait]
impl RetryPolicy for ExponentialBackoffRetry {
    async fn should_retry(&self, attempt: u32, error: &OrchestratorError) -> bool {
        if attempt >= self.max_attempts {
            return false;
        }
        
        match error {
            OrchestratorError::Network(_) => true,
            OrchestratorError::RateLimitExceeded(_) => true,
            OrchestratorError::Timeout(_) => true,
            OrchestratorError::CircuitBreakerOpen(_) => attempt < 3, // Retry circuit breaker a few times
            _ => false,
        }
    }
    
    fn delay(&self, attempt: u32) -> Duration {
        let base_delay = self.initial_delay.as_secs_f64() * 2_f64.powi(attempt as i32);
        let delay_secs = base_delay.min(self.max_delay.as_secs_f64());
        
        if self.jitter {
            // Add jitter: ±25% random variation
            use std::collections::hash_map::DefaultHasher;
            use std::hash::{Hash, Hasher};
            let mut hasher = DefaultHasher::new();
            attempt.hash(&mut hasher);
            let jitter_factor = 0.75 + (hasher.finish() % 50) as f64 / 200.0; // 0.75 to 1.0
            Duration::from_secs_f64(delay_secs * jitter_factor)
        } else {
            Duration::from_secs_f64(delay_secs)
        }
    }
    
    fn max_attempts(&self) -> u32 {
        self.max_attempts
    }
}

pub async fn retry_with_policy<F, Fut, T>(
    policy: &dyn RetryPolicy,
    mut f: F,
) -> Result<T, OrchestratorError>
where
    F: FnMut() -> Fut,
    Fut: std::future::Future<Output = Result<T, OrchestratorError>>,
{
    let mut attempt = 0;
    loop {
        match f().await {
            Ok(result) => return Ok(result),
            Err(e) => {
                attempt += 1;
                if !policy.should_retry(attempt, &e).await {
                    return Err(e);
                }
                let delay = policy.delay(attempt);
                tokio::time::sleep(delay).await;
            }
        }
    }
}
