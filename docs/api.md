# API Reference

## Overview

The Unified AI Orchestrator provides a REST API and WebSocket interface for interacting with multiple AI tools.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

The API supports two authentication methods:

1. **JWT Tokens**: Include in `Authorization: Bearer <token>` header
2. **API Keys**: Include in `X-API-Key` header or `api_key` query parameter

## Endpoints

### Health Check

```
GET /health
```

Returns the health status of the API.

**Response:**
```json
{
  "status": "healthy"
}
```

### List Tools

```
GET /api/v1/tools
```

List all available AI tools and their capabilities.

**Response:**
```json
{
  "tools": [
    {
      "name": "claude",
      "capabilities": {
        "supports_streaming": true,
        "supports_code_context": true
      }
    }
  ]
}
```

### Chat

```
POST /api/v1/chat
```

Send a chat message and get a response.

**Request:**
```json
{
  "message": "Hello, how are you?",
  "conversation_id": "optional-conversation-id",
  "project_id": "optional-project-id",
  "tool": "optional-explicit-tool",
  "stream": false
}
```

**Response:**
```json
{
  "content": "Response content",
  "tool": "claude",
  "conversation_id": "conversation-id",
  "metadata": {}
}
```

### WebSocket Chat

```
WS /api/v1/ws/chat
```

Stream chat responses via WebSocket.

**Message Format:**
```json
{
  "type": "chat",
  "message": "Hello",
  "conversation_id": "optional",
  "project_id": "optional",
  "tool": "optional"
}
```

**Response Messages:**
- `{"type": "start", "tool": "claude"}` - Stream started
- `{"type": "chunk", "content": "..."}` - Content chunk
- `{"type": "end"}` - Stream ended
- `{"type": "error", "message": "..."}` - Error occurred

## Error Responses

All errors follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

Common status codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error
