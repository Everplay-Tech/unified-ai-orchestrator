# Multi-stage production Dockerfile

# Stage 1: Build Rust components
FROM rust:1.70-slim as rust-builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Rust source
COPY rust-core/ ./rust-core/
COPY Cargo.toml ./
COPY rust-core/Cargo.toml ./rust-core/
COPY rust-core/pyo3-bridge/Cargo.toml ./rust-core/pyo3-bridge/

# Build Rust components
WORKDIR /build/rust-core
RUN cargo build --release

# Stage 2: Build Python package
FROM python:3.11-slim as python-builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python source
COPY pyproject.toml setup.py ./
COPY python-glue/ ./python-glue/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Stage 3: Runtime
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r uai && useradd -r -g uai -u 1000 -d /app -s /bin/bash uai

WORKDIR /app

# Copy Python package from builder
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy Rust binaries
COPY --from=rust-builder /build/rust-core/target/release/libunified_ai_orchestrator*.so /usr/local/lib/
COPY --from=rust-builder /build/rust-core/pyo3-bridge/target/release/libunified_ai_orchestrator*.so /usr/local/lib/

# Copy application code
COPY python-glue/ ./python-glue/
COPY config/ ./config/
COPY pyproject.toml setup.py ./

# Set Python path
ENV PYTHONPATH=/app/python-glue:$PYTHONPATH
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R uai:uai /app

# Switch to non-root user
USER uai

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "unified_ai.api.server"]
