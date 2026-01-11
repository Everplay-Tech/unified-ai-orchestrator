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
- `400` - Bad Request (validation error, invalid input)
- `401` - Unauthorized (missing or invalid API key/token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (resource doesn't exist)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

### Rate Limiting

Rate limits are applied per API key or IP address:
- Default: 60 requests per minute
- Headers included in responses:
  - `X-RateLimit-Limit`: Maximum requests per minute
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `Retry-After`: Seconds to wait before retrying (when rate limited)

### Pagination

List endpoints support pagination:
- `limit`: Number of items per page (default: 20, max: 100)
- `offset`: Number of items to skip (default: 0)

### Filtering

Some endpoints support filtering:
- `created_after`: Filter by creation date
- `project_id`: Filter by project
- `tool`: Filter by AI tool used
