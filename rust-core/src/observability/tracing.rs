use opentelemetry::global;
use opentelemetry::trace::TracerProvider;
use opentelemetry_sdk::trace::{Config, TracerProvider as SdkTracerProvider};
use opentelemetry_sdk::Resource;
use opentelemetry_otlp::WithExportConfig;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::Registry;
use std::sync::OnceLock;

static TRACE_INIT: OnceLock<()> = OnceLock::new();

pub fn setup_tracing(service_name: &str, endpoint: Option<&str>) {
    TRACE_INIT.get_or_init(|| {
        let resource = Resource::new(vec![
            opentelemetry::KeyValue::new("service.name", service_name.to_string()),
        ]);
        
        let mut tracer_provider_builder = opentelemetry_otlp::new_pipeline()
            .tracing()
            .with_trace_config(Config::default().with_resource(resource));
        
        if let Some(endpoint) = endpoint {
            tracer_provider_builder = tracer_provider_builder.with_endpoint(endpoint);
        }
        
        let tracer_provider = tracer_provider_builder
            .install_batch(opentelemetry_sdk::runtime::Tokio)
            .expect("Failed to create tracer provider");
        
        global::set_tracer_provider(tracer_provider);
        
        let tracer = global::tracer("uai-orchestrator");
        let telemetry = tracing_opentelemetry::layer().with_tracer(tracer);
        
        let subscriber = Registry::default().with(telemetry);
        tracing::subscriber::set_global_default(subscriber)
            .expect("Failed to set global subscriber");
    });
}

pub fn setup_tracing_console() {
    TRACE_INIT.get_or_init(|| {
        tracing_subscriber::fmt()
            .with_target(true)
            .with_file(true)
            .with_line_number(true)
            .init();
    });
}
