use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, fmt};
use tracing_subscriber::fmt::format::JsonFields;
use std::sync::OnceLock;

static LOG_INIT: OnceLock<()> = OnceLock::new();

pub fn setup_logging() {
    LOG_INIT.get_or_init(|| {
        let filter = EnvFilter::try_from_default_env()
            .unwrap_or_else(|_| EnvFilter::new("info"));
        
        let json_layer = fmt::layer()
            .json()
            .with_target(true)
            .with_file(true)
            .with_line_number(true);
        
        let fmt_layer = fmt::layer()
            .with_target(true)
            .with_file(true)
            .with_line_number(true);
        
        tracing_subscriber::registry()
            .with(filter)
            .with(json_layer)
            .with(fmt_layer)
            .init();
    });
}

#[macro_export]
macro_rules! log_request {
    ($level:ident, $($arg:tt)*) => {
        tracing::$level!(
            target: "request",
            $($arg)*
        );
    };
}

#[macro_export]
macro_rules! log_tool {
    ($level:ident, $tool:expr, $($arg:tt)*) => {
        tracing::$level!(
            target: "tool",
            tool = $tool,
            $($arg)*
        );
    };
}
