"""Advanced context management features"""

from typing import List, Dict, Any, Optional
from ..context_manager import Context, Message
from .token_counter import TokenCounter, get_token_counter


class ContextWindowManager:
    """Manage context window size and truncation"""
    
    def __init__(self, reserved_tokens: int = 1000):
        self.token_counter = get_token_counter()
        self.reserved_tokens = reserved_tokens
    
    def manage_context(
        self,
        context: Context,
        model: str = "default"
    ) -> Context:
        """Manage context window for a model"""
        window_size = self.token_counter.get_context_window(model)
        current_tokens = self._estimate_context_tokens(context, model)
        
        if current_tokens + self.reserved_tokens > window_size:
            return self._truncate_context(context, model, window_size)
        
        return context
    
    def _estimate_context_tokens(self, context: Context, model: str) -> int:
        """Estimate total tokens in context"""
        total = 0
        for message in context.messages:
            if isinstance(message, dict):
                total += self.token_counter.count_message_tokens([message], model)
            elif isinstance(message, Message):
                total += self.token_counter.count_message_tokens(
                    [{"role": message.role, "content": message.content}],
                    model
                )
        return total
    
    def _truncate_context(
        self,
        context: Context,
        model: str,
        window_size: int
    ) -> Context:
        """Truncate context to fit within window"""
        available_tokens = window_size - self.reserved_tokens
        
        kept_messages = []
        token_count = 0
        
        # Keep system messages first
        for message in context.messages:
            if isinstance(message, dict) and message.get("role") == "system":
                tokens = self.token_counter.count_message_tokens([message], model)
                if token_count + tokens <= available_tokens:
                    kept_messages.append(message)
                    token_count += tokens
            elif isinstance(message, Message) and message.role == "system":
                msg_dict = {"role": message.role, "content": message.content}
                tokens = self.token_counter.count_message_tokens([msg_dict], model)
                if token_count + tokens <= available_tokens:
                    kept_messages.append(message)
                    token_count += tokens
        
        # Then keep recent messages
        for message in reversed(context.messages):
            if isinstance(message, dict) and message.get("role") == "system":
                continue
            
            if isinstance(message, Message) and message.role == "system":
                continue
            
            msg_dict = (
                message if isinstance(message, dict)
                else {"role": message.role, "content": message.content}
            )
            tokens = self.token_counter.count_message_tokens([msg_dict], model)
            
            if token_count + tokens <= available_tokens:
                kept_messages.insert(len([m for m in kept_messages if (isinstance(m, dict) and m.get("role") == "system") or (isinstance(m, Message) and m.role == "system")]), message)
                token_count += tokens
            else:
                break
        
        # Reverse to get correct order
        kept_messages.reverse()
        
        # Create new context with truncated messages
        new_context = Context(
            conversation_id=context.conversation_id,
            project_id=context.project_id,
            messages=kept_messages,
            codebase_context=context.codebase_context,
            tool_history=context.tool_history,
        )
        
        return new_context


class ContextSummarizer:
    """Summarize long conversation histories"""
    
    def __init__(self, message_threshold: int = 50, summary_ratio: float = 0.8):
        self.message_threshold = message_threshold
        self.summary_ratio = summary_ratio
    
    def summarize_if_needed(self, context: Context) -> Optional[str]:
        """Summarize context if it exceeds threshold"""
        if len(context.messages) <= self.message_threshold:
            return None
        
        messages_to_summarize = int(len(context.messages) * self.summary_ratio)
        messages_to_keep = len(context.messages) - messages_to_summarize
        
        # Extract messages to summarize
        messages_to_summarize_list = context.messages[:messages_to_summarize]
        context.messages = context.messages[messages_to_summarize:]
        
        # Generate summary
        summary = self._generate_summary(messages_to_summarize_list)
        
        # Create summary message
        summary_message = Message(
            role="system",
            content=f"Previous conversation summary: {summary}",
            timestamp=messages_to_summarize_list[0].timestamp if messages_to_summarize_list else 0,
        )
        
        # Insert summary at the beginning
        context.messages.insert(0, summary_message)
        
        return summary
    
    def _generate_summary(self, messages: List[Message]) -> str:
        """Generate summary from messages"""
        summary_parts = []
        
        for message in messages:
            # Keep code blocks
            if "```" in message.content:
                summary_parts.append(f"[Code discussion: {message.role}]")
            
            # Keep decisions and important statements
            content_lower = message.content.lower()
            if any(keyword in content_lower for keyword in ["decided", "decision", "important", "note"]):
                sentences = [
                    s for s in message.content.split(".")
                    if any(kw in s.lower() for kw in ["decided", "decision", "important"])
                ]
                if sentences:
                    summary_parts.append(f"[{message.role}]: {sentences[0]}")
        
        if not summary_parts:
            return f"Summarized {len(messages)} messages"
        
        return "; ".join(summary_parts)


class ContextCompressor:
    """Compress context by removing redundancy"""
    
    def compress(self, context: Context) -> Context:
        """Compress context"""
        # Remove duplicates
        messages = self._remove_duplicates(context.messages)
        
        # Compress messages
        compressed_messages = [self._compress_message(msg) for msg in messages]
        
        return Context(
            conversation_id=context.conversation_id,
            project_id=context.project_id,
            messages=compressed_messages,
            codebase_context=context.codebase_context,
            tool_history=context.tool_history,
        )
    
    def _remove_duplicates(self, messages: List[Message]) -> List[Message]:
        """Remove duplicate consecutive messages"""
        if not messages:
            return []
        
        result = [messages[0]]
        for i in range(1, len(messages)):
            current = messages[i]
            prev = messages[i - 1]
            
            if not (current.role == prev.role and current.content == prev.content):
                result.append(current)
        
        return result
    
    def _compress_message(self, message: Message) -> Message:
        """Compress individual message"""
        # Remove excessive whitespace
        compressed = " ".join(
            line.strip() for line in message.content.splitlines()
            if line.strip()
        )
        
        # Limit length
        MAX_LENGTH = 2000
        if len(compressed) > MAX_LENGTH:
            first_part = compressed[:MAX_LENGTH // 2]
            last_part = compressed[-MAX_LENGTH // 2:]
            compressed = f"{first_part}... [truncated] ...{last_part}"
        
        return Message(
            role=message.role,
            content=compressed,
            timestamp=message.timestamp,
        )


def manage_context_window(
    context: Context,
    model: str = "default",
    reserved_tokens: int = 1000
) -> Context:
    """Convenience function to manage context window"""
    manager = ContextWindowManager(reserved_tokens)
    return manager.manage_context(context, model)


def summarize_context(context: Context) -> Optional[str]:
    """Convenience function to summarize context"""
    summarizer = ContextSummarizer()
    return summarizer.summarize_if_needed(context)


def compress_context(context: Context) -> Context:
    """Convenience function to compress context"""
    compressor = ContextCompressor()
    return compressor.compress(context)
