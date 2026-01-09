"""API routes"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..router import Router
from ..context_manager import ContextManager
from ..utils.adapters import get_adapters
from ..config import load_config
from ..cost import CostTracker
from ..observability import trace_request, RequestMetrics
from ..resilience import retry, ExponentialBackoffRetry
from pathlib import Path

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    project_id: Optional[str] = Field(None, description="Project ID")
    tool: Optional[str] = Field(None, description="Explicit tool to use")
    stream: bool = Field(False, description="Stream response")


class ChatResponse(BaseModel):
    """Chat response model"""
    content: str
    tool: str
    conversation_id: str
    metadata: Dict[str, Any]


class ConversationResponse(BaseModel):
    """Conversation response model"""
    conversation_id: str
    project_id: Optional[str]
    messages: List[Dict[str, Any]]
    tool_history: List[Dict[str, Any]]


def get_router() -> Router:
    """Get router instance"""
    config = load_config()
    routing_rules = {
        "code_editing": config.routing.code_editing,
        "research": config.routing.research,
        "general_chat": config.routing.general_chat,
    }
    return Router(routing_rules, config.routing.default_tool)


def get_context_manager() -> ContextManager:
    """Get context manager instance"""
    config = load_config()
    db_path = Path(config.storage.db_path).expanduser()
    return ContextManager(db_path)


def get_cost_tracker() -> CostTracker:
    """Get cost tracker instance"""
    config = load_config()
    db_path = Path(config.storage.db_path).expanduser()
    return CostTracker(db_path)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    router: Router = Depends(get_router),
    context_mgr: ContextManager = Depends(get_context_manager),
    cost_tracker: CostTracker = Depends(get_cost_tracker),
):
    """Chat endpoint"""
    from ..adapters.base import Message as AdapterMessage, Context as AdapterContext
    import time
    
    start_time = time.time()
    
    with trace_request("chat", {"message_length": len(request.message)}):
        # Get adapters
        config = load_config()
        adapters = get_adapters(config)
        
        if not adapters:
            raise HTTPException(status_code=500, detail="No AI tools configured")
        
        # Route request
        routing_decision = router.route(
            message=request.message,
            conversation_id=request.conversation_id,
            project_id=request.project_id,
            explicit_tool=request.tool,
        )
        
        # Select tool
        selected_tool_name = None
        if request.tool:
            selected_tool_name = request.tool
        else:
            for tool_name in routing_decision["selected_tools"]:
                if tool_name in adapters:
                    selected_tool_name = tool_name
                    break
        
        if not selected_tool_name or selected_tool_name not in adapters:
            raise HTTPException(
                status_code=400,
                detail=f"No suitable tool available. Available: {list(adapters.keys())}"
            )
        
        selected_tool = adapters[selected_tool_name]
        
        # Get or create context
        context = context_mgr.get_or_create_context(
            conversation_id=request.conversation_id,
            project_id=request.project_id,
        )
        
        # Prepare messages
        messages = []
        for msg in context.messages[-10:]:
            messages.append(AdapterMessage(role=msg.role, content=msg.content))
        
        messages.append(AdapterMessage(role="user", content=request.message))
        
        # Prepare adapter context
        adapter_context = None
        if request.project_id or context.codebase_context:
            adapter_context = AdapterContext(
                conversation_id=context.conversation_id,
                project_id=request.project_id or context.project_id,
                codebase_context=context.codebase_context,
            )
        
        # Make request with retry
        retry_policy = ExponentialBackoffRetry(max_attempts=3)
        
        @retry(policy=retry_policy)
        async def call_tool():
            return await selected_tool.chat(messages, adapter_context)
        
        try:
            response = await call_tool()
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Record cost
            if response.metadata and "usage" in response.metadata:
                usage = response.metadata["usage"]
                input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens", 0)
                output_tokens = usage.get("output_tokens") or usage.get("completion_tokens", 0)
                
                # Calculate cost (simplified - would use CostCalculator in production)
                cost_usd = 0.0  # Would calculate based on model pricing
                
                background_tasks.add_task(
                    cost_tracker.record_cost,
                    tool=selected_tool.name,
                    model=selected_tool.model if hasattr(selected_tool, "model") else "unknown",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                    conversation_id=context.conversation_id,
                    project_id=request.project_id,
                )
            
            # Save to context
            context_mgr.add_message(context, "user", request.message)
            context_mgr.add_message(context, "assistant", response.content)
            context_mgr.add_tool_call(
                context,
                selected_tool.name,
                request.message,
                response.content,
            )
            
            return ChatResponse(
                content=response.content,
                tool=selected_tool.name,
                conversation_id=context.conversation_id,
                metadata=response.metadata or {},
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    context_mgr: ContextManager = Depends(get_context_manager),
):
    """Get conversation history"""
    context = context_mgr.get_context(conversation_id)
    
    if not context:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationResponse(
        conversation_id=context.conversation_id,
        project_id=context.project_id,
        messages=[
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
            for msg in context.messages
        ],
        tool_history=context.tool_history,
    )


@router.get("/tools")
async def list_tools():
    """List available tools"""
    config = load_config()
    adapters = get_adapters(config)
    
    tools = []
    for name, adapter in adapters.items():
        caps = adapter.capabilities
        tools.append({
            "name": name,
            "model": adapter.model if hasattr(adapter, "model") else "N/A",
            "capabilities": [cap.value for cap in caps.supported_capabilities],
            "supports_streaming": caps.supports_streaming,
            "supports_code_context": caps.supports_code_context,
            "max_context_length": caps.max_context_length,
        })
    
    return {"tools": tools}


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket chat endpoint for streaming"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            
            # Handle streaming chat
            # Implementation would stream responses
            await websocket.send_json({"content": "Streaming not fully implemented yet"})
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
