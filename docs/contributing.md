# Contributing Guide

## Getting Started

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Code Examples

### Creating a Custom Adapter

```python
from unified_ai.adapters.base import ToolAdapter, ToolCapabilities, Message, Response

class MyAdapter(ToolAdapter):
    @property
    def name(self) -> str:
        return "my_adapter"
    
    @property
    def capabilities(self) -> ToolCapabilities:
        return ToolCapabilities(
            supports_streaming=True,
            supports_code_context=False,
        )
    
    async def chat(self, messages, context=None):
        # Implement chat logic
        return Response(content="Response", tool=self.name)
```

### Using the Router

```python
from unified_ai.router import Router

router = Router(
    routing_rules={
        "code_editing": ["claude"],
        "research": ["perplexity"],
    },
    default_tool="claude"
)

decision = router.route("Refactor this code")
print(decision["selected_tools"])  # ["claude"]
```

### Context Management

```python
from unified_ai.context_manager import ContextManager
from unified_ai.context import manage_context_window

manager = ContextManager()
context = await manager.get_or_create_context(
    conversation_id="conv-123",
    project_id="proj-456"
)

# Manage context window
context = manage_context_window(context, model="gpt-4")
```

## Testing

- Write unit tests for new features
- Add integration tests for workflows
- Ensure >80% code coverage

## Documentation

- Update API docs for new endpoints
- Add code examples
- Update README if needed
