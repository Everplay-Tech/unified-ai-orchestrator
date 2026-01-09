use prometheus::{Counter, Histogram, Gauge, Registry, Encoder, TextEncoder};
use std::sync::Arc;
use std::time::Instant;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestMetrics {
    pub request_id: String,
    pub tool: String,
    pub duration_ms: u64,
    pub tokens_input: Option<u32>,
    pub tokens_output: Option<u32>,
    pub cost_usd: Option<f64>,
    pub success: bool,
    pub error: Option<String>,
}

#[derive(Debug, Clone)]
pub struct ToolStats {
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub total_cost_usd: f64,
    pub avg_latency_ms: f64,
    pub p95_latency_ms: f64,
    pub p99_latency_ms: f64,
}

#[derive(Clone)]
pub struct MetricsCollector {
    registry: Arc<Registry>,
    request_counter: Counter,
    request_duration: Histogram,
    request_cost: Counter,
    request_tokens_input: Counter,
    request_tokens_output: Counter,
    error_counter: Counter,
    active_requests: Gauge,
}

impl MetricsCollector {
    pub fn new() -> Self {
        let registry = Registry::new();
        
        let request_counter = Counter::with_opts(
            prometheus::Opts::new("uai_requests_total", "Total number of requests")
                .const_label("component", "orchestrator")
        ).unwrap();
        
        let request_duration = Histogram::with_opts(
            prometheus::HistogramOpts::new("uai_request_duration_seconds", "Request duration in seconds")
                .buckets(vec![0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0])
        ).unwrap();
        
        let request_cost = Counter::with_opts(
            prometheus::Opts::new("uai_request_cost_usd_total", "Total cost in USD")
        ).unwrap();
        
        let request_tokens_input = Counter::with_opts(
            prometheus::Opts::new("uai_tokens_input_total", "Total input tokens")
        ).unwrap();
        
        let request_tokens_output = Counter::with_opts(
            prometheus::Opts::new("uai_tokens_output_total", "Total output tokens")
        ).unwrap();
        
        let error_counter = Counter::with_opts(
            prometheus::Opts::new("uai_errors_total", "Total number of errors")
        ).unwrap();
        
        let active_requests = Gauge::with_opts(
            prometheus::Opts::new("uai_active_requests", "Number of active requests")
        ).unwrap();
        
        registry.register(Box::new(request_counter.clone())).unwrap();
        registry.register(Box::new(request_duration.clone())).unwrap();
        registry.register(Box::new(request_cost.clone())).unwrap();
        registry.register(Box::new(request_tokens_input.clone())).unwrap();
        registry.register(Box::new(request_tokens_output.clone())).unwrap();
        registry.register(Box::new(error_counter.clone())).unwrap();
        registry.register(Box::new(active_requests.clone())).unwrap();
        
        Self {
            registry: Arc::new(registry),
            request_counter,
            request_duration,
            request_cost,
            request_tokens_input,
            request_tokens_output,
            error_counter,
            active_requests,
        }
    }
    
    pub fn record_request(&self, metrics: RequestMetrics) {
        let labels = &[metrics.tool.as_str()];
        
        self.request_counter.inc();
        self.request_duration.observe(metrics.duration_ms as f64 / 1000.0);
        
        if let Some(cost) = metrics.cost_usd {
            self.request_cost.inc_by(cost);
        }
        
        if let Some(tokens) = metrics.tokens_input {
            self.request_tokens_input.inc_by(tokens as f64);
        }
        
        if let Some(tokens) = metrics.tokens_output {
            self.request_tokens_output.inc_by(tokens as f64);
        }
        
        if !metrics.success {
            self.error_counter.inc();
        }
    }
    
    pub fn increment_active(&self) {
        self.active_requests.inc();
    }
    
    pub fn decrement_active(&self) {
        self.active_requests.dec();
    }
    
    pub fn export(&self) -> String {
        let encoder = TextEncoder::new();
        let mut buffer = Vec::new();
        encoder.encode(&self.registry.gather(), &mut buffer).unwrap();
        String::from_utf8(buffer).unwrap()
    }
    
    pub fn get_stats(&self, _tool: &str) -> ToolStats {
        // In a real implementation, this would query metrics by tool label
        // For now, return aggregate stats
        ToolStats {
            total_requests: self.request_counter.get() as u64,
            successful_requests: self.request_counter.get() as u64 - self.error_counter.get() as u64,
            failed_requests: self.error_counter.get() as u64,
            total_cost_usd: self.request_cost.get(),
            avg_latency_ms: 0.0, // Would need to calculate from histogram
            p95_latency_ms: 0.0,
            p99_latency_ms: 0.0,
        }
    }
}

impl Default for MetricsCollector {
    fn default() -> Self {
        Self::new()
    }
}
