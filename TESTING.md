# Testing Guide

## Test Results Summary

Basic smoke tests show:
- ✅ Resilience patterns working (retry, circuit breaker, rate limiter)
- ✅ Router functionality working
- ⚠️ Some dependencies need installation (expected)

## Running Tests

### Prerequisites

Install dependencies:
```bash
pip install -e .
```

Or install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov
```

### Run Basic Tests

```bash
python3 python-glue/tests/test_basic.py
```

### Run Full Test Suite

```bash
pytest python-glue/tests/ -v
```

### Run Specific Test Files

```bash
pytest python-glue/tests/test_resilience.py -v
pytest python-glue/tests/test_context_manager.py -v
pytest python-glue/tests/test_cost_tracker.py -v
pytest python-glue/tests/test_router.py -v
```

## Test Coverage

### Unit Tests

- **Resilience**: Retry policies, circuit breakers, rate limiters
- **Context Manager**: Context creation, persistence, message handling
- **Cost Tracker**: Cost recording, aggregation, filtering
- **Router**: Routing logic, tool selection
- **Adapters**: Adapter initialization, capability detection (mocked API calls)

### Integration Tests

- Context persistence across sessions
- Cost tracking with multiple projects
- Router with real configuration

### Test Fixtures

Located in `python-glue/tests/conftest.py`:
- `temp_db_path`: Temporary database for testing
- `test_config`: Test configuration
- `context_manager`: Context manager instance
- `cost_tracker`: Cost tracker instance

## Manual Testing

### Test CLI

```bash
# Configure API keys
uai config

# Test chat
uai chat "Hello, how are you?"

# Test with explicit tool
uai chat "What is Python?" --tool claude

# List tools
uai tools
```

### Test API Server

```bash
# Start server
python3 -m unified_ai.api.server

# In another terminal, test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/tools
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

## Expected Test Results

When dependencies are installed:
- All unit tests should pass
- Integration tests verify persistence
- Mocked adapter tests verify interface compliance

## Known Issues

1. **Missing Dependencies**: Some tests require `anthropic`, `openai`, `toml` packages
   - Solution: Install with `pip install -e .`

2. **Rust Core**: PyO3 bridge requires Rust compilation
   - Solution: Run `cargo build --release` in `rust-core/pyo3-bridge`

3. **API Keys**: Adapter tests require API keys for full testing
   - Solution: Set environment variables or use `uai config`

## Continuous Integration

For CI/CD, run:
```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest python-glue/tests/ --cov=unified_ai --cov-report=html

# Check Rust code
cd rust-core && cargo test
```
