use crate::error::{OrchestratorError, Result};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

#[derive(Debug, Clone)]
pub struct TokenBucket {
    capacity: u32,
    tokens: u32,
    refill_rate: f64, // tokens per second
    last_refill: Instant,
}

impl TokenBucket {
    pub fn new(capacity: u32, refill_rate: f64) -> Self {
        Self {
            capacity,
            tokens: capacity,
            refill_rate,
            last_refill: Instant::now(),
        }
    }
    
    fn refill(&mut self) {
        let now = Instant::now();
        let elapsed = now.duration_since(self.last_refill).as_secs_f64();
        let tokens_to_add = (elapsed * self.refill_rate) as u32;
        
        if tokens_to_add > 0 {
            self.tokens = (self.tokens + tokens_to_add).min(self.capacity);
            self.last_refill = now;
        }
    }
    
    pub fn try_acquire(&mut self, tokens: u32) -> bool {
        self.refill();
        if self.tokens >= tokens {
            self.tokens -= tokens;
            true
        } else {
            false
        }
    }
    
    pub fn wait_time(&self) -> Duration {
        if self.tokens >= 1 {
            Duration::ZERO
        } else {
            let tokens_needed = 1.0 - self.tokens as f64;
            let seconds = tokens_needed / self.refill_rate;
            Duration::from_secs_f64(seconds)
        }
    }
}

#[derive(Debug, Clone)]
pub struct RateLimiter {
    bucket: Arc<Mutex<TokenBucket>>,
    name: String,
}

impl RateLimiter {
    pub fn new(name: impl Into<String>, capacity: u32, refill_rate: f64) -> Self {
        Self {
            bucket: Arc::new(Mutex::new(TokenBucket::new(capacity, refill_rate))),
            name: name.into(),
        }
    }
    
    pub async fn acquire(&self, tokens: u32) -> Result<()> {
        loop {
            let acquired = {
                let mut bucket = self.bucket.lock().unwrap();
                bucket.try_acquire(tokens)
            };
            
            if acquired {
                return Ok(());
            }
            
            let wait_time = {
                let bucket = self.bucket.lock().unwrap();
                bucket.wait_time()
            };
            
            if wait_time > Duration::ZERO {
                tokio::time::sleep(wait_time).await;
            }
        }
    }
    
    pub fn try_acquire(&self, tokens: u32) -> Result<()> {
        let mut bucket = self.bucket.lock().unwrap();
        if bucket.try_acquire(tokens) {
            Ok(())
        } else {
            Err(OrchestratorError::RateLimitExceeded(
                format!("Rate limit exceeded for {}", self.name)
            ))
        }
    }
}
