# Architecture Documentation

## Overview

The Unified AI Orchestration System is built with a hybrid Rust + Python architecture:

- **Rust Core**: Performance-critical components (router, storage, indexer)
- **Python Glue**: Tool adapters, API server, CLI convenience layer

## Component Architecture

### Router
The router analyzes incoming requests and selects the optimal AI tool(s) based on:
- Task type classification (code editing, research, general chat, etc.)
- Routing rules from configuration
- Tool availability and capabilities

### Context Manager
Maintains conversation history and project context:
- SQLite database for persistence
- Conversation-level context
- Project-level context
- Tool call history

### Tool Adapters
Unified interface for different AI services:
- Base `ToolAdapter` interface
- Implementations for Claude, GPT, etc.
- Capability detection
- Streaming support

### Storage Layer
- SQLite for structured data (contexts, history)
- Filesystem for indexes and caches
- Encrypted API key storage via OS keychain

## Data Flow

1. User sends request via CLI
2. Router analyzes request and selects tool(s)
3. Context Manager loads/creates conversation context
4. Tool Adapter makes API call with context
5. Response saved to context
6. Response returned to user

## Configuration

Configuration is stored in `~/.uai/config.toml`:
- Tool settings (API keys, models)
- Routing rules
- Storage paths
- Codebase indexing settings

API keys are stored securely using OS keychain (macOS Keychain, Linux Secret Service).

## System Architecture Diagram

```
┌─────────────────┐
│   CLI / API     │
│   Interface     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Router      │ ◄─── Analyzes requests, selects tools
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Manager │ ◄─── Manages conversation history
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Tool Adapters   │ ◄─── Claude, GPT, Perplexity, etc.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI Services    │
└─────────────────┘
```

## Component Details

### Indexer
- AST parsing using tree-sitter
- Semantic search with embeddings
- Incremental indexing
- File watching for real-time updates

### Context Management
- Token-aware windowing
- LLM-based summarization
- Context compression
- Importance-based retention

### Security
- JWT authentication
- API key authentication
- Role-based authorization
- Input validation and sanitization
- Rate limiting
- Audit logging

### Observability
- Structured JSON logging
- Prometheus metrics
- OpenTelemetry tracing
- Request/response logging
