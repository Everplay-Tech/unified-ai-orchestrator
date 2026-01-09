use crate::error::{OrchestratorError, Result};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

#[derive(Debug)]
struct CircuitBreakerInner {
    failure_threshold: u32,
    success_threshold: u32,
    timeout: Duration,
    state: CircuitState,
    failures: u32,
    successes: u32,
    last_failure_time: Option<Instant>,
}

impl CircuitBreakerInner {
    fn new(failure_threshold: u32, timeout: Duration) -> Self {
        Self {
            failure_threshold,
            success_threshold: 2,
            timeout,
            state: CircuitState::Closed,
            failures: 0,
            successes: 0,
            last_failure_time: None,
        }
    }
    
    fn on_success(&mut self) {
        self.failures = 0;
        match self.state {
            CircuitState::HalfOpen => {
                self.successes += 1;
                if self.successes >= self.success_threshold {
                    self.state = CircuitState::Closed;
                    self.successes = 0;
                }
            }
            _ => {}
        }
    }
    
    fn on_failure(&mut self) {
        self.failures += 1;
        self.last_failure_time = Some(Instant::now());
        
        match self.state {
            CircuitState::HalfOpen => {
                self.state = CircuitState::Open;
            }
            CircuitState::Closed => {
                if self.failures >= self.failure_threshold {
                    self.state = CircuitState::Open;
                }
            }
            _ => {}
        }
    }
    
    fn check_state(&mut self) -> Result<()> {
        match self.state {
            CircuitState::Open => {
                if let Some(last_failure) = self.last_failure_time {
                    if last_failure.elapsed() >= self.timeout {
                        self.state = CircuitState::HalfOpen;
                        self.successes = 0;
                        Ok(())
                    } else {
                        Err(OrchestratorError::CircuitBreakerOpen(
                            format!("Circuit breaker is open. Retry after {:?}", 
                                self.timeout - last_failure.elapsed())
                        ))
                    }
                } else {
                    Err(OrchestratorError::CircuitBreakerOpen(
                        "Circuit breaker is open".to_string()
                    ))
                }
            }
            CircuitState::HalfOpen | CircuitState::Closed => Ok(()),
        }
    }
}

#[derive(Debug, Clone)]
pub struct CircuitBreaker {
    inner: Arc<Mutex<CircuitBreakerInner>>,
    name: String,
}

impl CircuitBreaker {
    pub fn new(name: impl Into<String>, failure_threshold: u32, timeout: Duration) -> Self {
        Self {
            inner: Arc::new(Mutex::new(CircuitBreakerInner::new(failure_threshold, timeout))),
            name: name.into(),
        }
    }
    
    pub fn state(&self) -> CircuitState {
        self.inner.lock().unwrap().state
    }
    
    pub async fn call<T, F, Fut>(&self, f: F) -> Result<T>
    where
        F: FnOnce() -> Fut,
        Fut: std::future::Future<Output = Result<T>>,
    {
        // Check if we can proceed
        {
            let mut inner = self.inner.lock().unwrap();
            inner.check_state()?;
        }
        
        match f().await {
            Ok(result) => {
                let mut inner = self.inner.lock().unwrap();
                inner.on_success();
                Ok(result)
            }
            Err(e) => {
                let mut inner = self.inner.lock().unwrap();
                inner.on_failure();
                Err(e)
            }
        }
    }
}
