# Unified AI Orchestration System

[![CI](https://github.com/Everplay-Tech/unified-ai-orchestrator/workflows/CI/badge.svg)](https://github.com/Everplay-Tech/unified-ai-orchestrator/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Rust](https://img.shields.io/badge/rust-1.70+-orange.svg)](https://www.rust-lang.org/)

A unified AI tool orchestration system that intelligently routes tasks to optimal AI tools, maintains context across switches, and provides a single CLI/API interface for all AI interactions.

## Architecture

This system combines:
- **Rust Core**: Performance-critical components (router, indexer, storage)
- **Python Glue**: Tool adapters, API server, CLI convenience layer

## Quick Start

### Prerequisites

- Rust 1.70+ (with cargo)
- Python 3.10+
- API keys for desired AI services (Claude, GPT, etc.)

### Installation

```bash
# Install Python dependencies
pip install -e .

# Build Rust components
cargo build --release

# Configure API keys
uai config
```

### Usage

```bash
# Chat with unified interface
uai chat "your question here"

# Chat with explicit tool selection
uai chat "your question" --tool claude

# Chat with project context
uai chat "refactor this function" --project /path/to/project

# List available tools
uai tools

# Configure API keys and settings
uai config
```

## Features

### Phase 1 MVP (Implemented)

- ✅ Unified CLI interface for all AI tools
- ✅ Intelligent routing based on task type
- ✅ Context preservation across conversations
- ✅ Support for Claude and GPT
- ✅ Secure API key storage (OS keychain)
- ✅ Conversation history persistence
- ✅ Project-aware context

### Phase 2 (Planned)

- Codebase indexing and semantic search
- Advanced routing with cost optimization
- Multi-tool composition
- Streaming responses

### Phase 3 (Planned)

- REST API server
- WebSocket support
- Learning from user preferences
- Cost tracking and optimization

## Project Structure

- `rust-core/` - Rust core components (router, storage, indexer)
- `python-glue/` - Python tool adapters and CLI
- `config/` - Configuration files

## Development

See `docs/architecture.md` for detailed architecture documentation.
