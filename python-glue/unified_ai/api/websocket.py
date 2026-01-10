"""WebSocket handlers for streaming chat"""

import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from ..router import Router
from ..context_manager import ContextManager
from ..utils.adapters import get_adapters
from ..observability import get_logger
from ..config import load_config

logger = get_logger(__name__)


class WebSocketManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        logger.info(f"WebSocket connected: {connection_id}")
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """Send message to WebSocket client"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                self.disconnect(connection_id)


# Global WebSocket manager
ws_manager = WebSocketManager()


async def handle_websocket_chat(
    websocket: WebSocket,
    conversation_id: Optional[str] = None,
    project_id: Optional[str] = None,
):
    """Handle WebSocket chat connection"""
    import uuid
    import os
    connection_id = str(uuid.uuid4())
    
    await ws_manager.connect(websocket, connection_id)
    
    try:
        config = load_config()
        
        # Get mobile API key for authentication
        mobile_api_key = None
        if hasattr(config, 'api') and hasattr(config.api, 'api_key'):
            mobile_api_key = config.api.api_key
        
        # If no API key configured, allow access (development mode)
        authenticated = mobile_api_key is None
        
        routing_rules = {
            "code_editing": config.routing.code_editing,
            "research": config.routing.research,
            "general_chat": config.routing.general_chat,
        }
        router = Router(routing_rules, config.routing.default_tool)
        
        # Initialize ContextManager with db_path from config
        from pathlib import Path
        db_path = Path(config.storage.db_path).expanduser()
        context_manager = ContextManager(db_path)
        
        adapters = get_adapters(config)
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            message_type = data.get("type", "chat")
            
            # Handle authentication
            if message_type == "auth":
                provided_key = data.get("api_key")
                if mobile_api_key:
                    if provided_key == mobile_api_key:
                        authenticated = True
                        await ws_manager.send_message(connection_id, {
                            "type": "auth_success",
                        })
                    else:
                        await ws_manager.send_message(connection_id, {
                            "type": "error",
                            "message": "Invalid API key",
                        })
                        ws_manager.disconnect(connection_id)
                        return
                else:
                    # No API key configured, allow access
                    authenticated = True
                    await ws_manager.send_message(connection_id, {
                        "type": "auth_success",
                    })
                continue
            
            # Require authentication for other message types
            if not authenticated and mobile_api_key:
                await ws_manager.send_message(connection_id, {
                    "type": "error",
                    "message": "Authentication required. Send auth message first.",
                })
                continue
            
            if message_type == "chat":
                message = data.get("message", "")
                tool = data.get("tool")
                
                # Get or create context
                context = context_manager.get_or_create_context(
                    conversation_id,
                    project_id
                )
                
                # Route to tool
                routing_decision = router.route(
                    message,
                    conversation_id=context.conversation_id,
                    project_id=project_id,
                    explicit_tool=tool,
                )
                
                selected_tool = routing_decision["selected_tools"][0]
                adapter = adapters.get(selected_tool)
                
                if not adapter:
                    await ws_manager.send_message(connection_id, {
                        "type": "error",
                        "message": f"Tool {selected_tool} not available",
                    })
                    continue
                
                # Stream response
                await ws_manager.send_message(connection_id, {
                    "type": "start",
                    "tool": selected_tool,
                })
                
                try:
                    from ..adapters.base import Message as AdapterMessage
                    messages = [
                        AdapterMessage(role="user", content=message)
                    ]
                    
                    async for chunk in adapter.stream_chat(messages):
                        await ws_manager.send_message(connection_id, {
                            "type": "chunk",
                            "content": chunk,
                        })
                    
                    await ws_manager.send_message(connection_id, {
                        "type": "end",
                    })
                    
                    # Update context
                    context_manager.add_message(context, "user", message)
                    context_manager.add_message(context, "assistant", "Response streamed")
                    context_manager.save_context(context)
                    
                except Exception as e:
                    logger.error(f"Error streaming response: {e}")
                    await ws_manager.send_message(connection_id, {
                        "type": "error",
                        "message": str(e),
                    })
            
            elif message_type == "ping":
                await ws_manager.send_message(connection_id, {
                    "type": "pong",
                })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        ws_manager.disconnect(connection_id)
