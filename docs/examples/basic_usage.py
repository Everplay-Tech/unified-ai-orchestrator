"""Basic usage examples"""

from unified_ai.router import Router
from unified_ai.context_manager import ContextManager
from unified_ai.utils.adapters import get_adapters

# Initialize router
router = Router(
    routing_rules={
        "code_editing": ["claude"],
        "research": ["perplexity"],
    },
    default_tool="claude"
)

# Get adapters
adapters = get_adapters()

# Route a message
decision = router.route("How do I implement a binary search?")
selected_tool = decision["selected_tools"][0]
adapter = adapters[selected_tool]

# Chat
from unified_ai.adapters.base import Message
messages = [Message(role="user", content="Hello")]
response = await adapter.chat(messages)
print(response.content)
