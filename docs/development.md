# Development Guide

## Setup

### Prerequisites

- Rust 1.70+ (with cargo)
- Python 3.10+
- SQLite

### Installation

1. Clone the repository
2. Install Python dependencies:
   ```bash
   pip install -e .
   ```

3. Build Rust components:
   ```bash
   cd rust-core
   cargo build --release
   cd ..
   ```

4. Run migrations:
   ```bash
   python -m unified_ai.migrations.cli migrate --db-path data/app.db
   ```

## Development Workflow

### Running Tests

```bash
# Python tests
pytest python-glue/tests/ -v

# Rust tests
cd rust-core
cargo test
```

### Code Structure

- `rust-core/` - Core Rust components
- `python-glue/` - Python glue code and adapters
- `config/` - Configuration files
- `docs/` - Documentation

### Adding a New Adapter

1. Create adapter file in `python-glue/unified_ai/adapters/`
2. Implement `ToolAdapter` interface
3. Add to `__init__.py`
4. Update `utils/adapters.py` to include it

### Adding a Migration

1. Create migration module in `rust-core/src/migrations/`
2. Register in `migrations/mod.rs`
3. Test migration up and down

## Code Style

- Python: Use `black` for formatting, `ruff` for linting
- Rust: Use `rustfmt` for formatting, `clippy` for linting

## Debugging

- Enable debug logging: `RUST_LOG=debug python -m unified_ai.api.server`
- Check database: `sqlite3 data/app.db`
