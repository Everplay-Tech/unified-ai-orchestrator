"""Structured logging setup with request IDs and correlation IDs"""

import logging
import json
import sys
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from contextvars import ContextVar

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


def get_request_id() -> Optional[str]:
    """Get current request ID"""
    return request_id_var.get()


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set current request ID"""
    request_id_var.set(request_id)


def set_correlation_id(correlation_id: str) -> None:
    """Set current correlation ID"""
    correlation_id_var.set(correlation_id)


def set_user_id(user_id: str) -> None:
    """Set current user ID"""
    user_id_var.set(user_id)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging with request/correlation IDs"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add request ID if available
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add correlation ID if available
        correlation_id = get_correlation_id()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        # Add user ID if available
        user_id = get_user_id()
        if user_id:
            log_data["user_id"] = user_id
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Mask sensitive data
        log_data = self._mask_sensitive_data(log_data)
        
        return json.dumps(log_data)
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in log entries"""
        sensitive_keys = [
            "password", "api_key", "token", "secret", "authorization",
            "x-api-key", "bearer", "credential", "access_token", "refresh_token"
        ]
        
        masked_data = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 8:
                    masked_data[key] = value[:4] + "***" + value[-4:]
                else:
                    masked_data[key] = "***"
            elif isinstance(value, dict):
                masked_data[key] = self._mask_sensitive_data(value)
            else:
                masked_data[key] = value
        
        return masked_data


def get_user_id() -> Optional[str]:
    """Get current user ID"""
    return user_id_var.get()


def setup_logging(
    level: str = "INFO",
    json_output: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """Setup structured logging"""
    import os
    
    # Get log level from environment or use default
    log_level_str = os.getenv("LOG_LEVEL", level).upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_output or os.getenv("LOG_FORMAT", "").lower() == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"
            )
        )
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )
    
    # Set log levels for specific loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


class RequestIDFilter(logging.Filter):
    """Filter to add request ID to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = get_request_id()
        if request_id:
            record.request_id = request_id
        else:
            record.request_id = "N/A"
        
        correlation_id = get_correlation_id()
        if correlation_id:
            record.correlation_id = correlation_id
        else:
            record.correlation_id = "N/A"
        
        user_id = get_user_id()
        if user_id:
            record.user_id = user_id
        
        return True
