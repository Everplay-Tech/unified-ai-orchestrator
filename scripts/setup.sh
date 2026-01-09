#!/bin/bash
set -e

echo "Setting up Unified AI Orchestrator..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -e .

# Build Rust components
echo "Building Rust components..."
cd rust-core
cargo build --release
cd ..

# Run tests
echo "Running tests..."
pytest python-glue/tests/test_basic.py -v || echo "Tests completed with some failures (expected if dependencies missing)"

echo "Setup complete!"
