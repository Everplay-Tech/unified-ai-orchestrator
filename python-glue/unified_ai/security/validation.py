"""Input validation and sanitization"""

import re
import html
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote

from pydantic import BaseModel, validator, ValidationError as PydanticValidationError


class ValidationError(Exception):
    """Custom validation error"""
    pass


def validate_input(
    input_str: str,
    max_length: Optional[int] = None,
    min_length: int = 0,
    allow_empty: bool = False,
    pattern: Optional[str] = None,
) -> str:
    """
    Validate user input
    
    Args:
        input_str: Input string to validate
        max_length: Maximum allowed length
        min_length: Minimum required length
        allow_empty: Whether empty strings are allowed
        pattern: Optional regex pattern to match
    
    Returns:
        Validated input string
    
    Raises:
        ValidationError: If validation fails
    """
    if not allow_empty and not input_str.strip():
        raise ValidationError("Input cannot be empty")
    
    if len(input_str) < min_length:
        raise ValidationError(f"Input too short: minimum {min_length} characters")
    
    if max_length and len(input_str) > max_length:
        raise ValidationError(f"Input too long: maximum {max_length} characters")
    
    # Check for null bytes
    if '\0' in input_str:
        raise ValidationError("Input contains invalid null bytes")
    
    # Check for control characters (except newline, tab, carriage return)
    if re.search(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', input_str):
        raise ValidationError("Input contains invalid control characters")
    
    # Pattern matching
    if pattern and not re.match(pattern, input_str):
        raise ValidationError(f"Input does not match required pattern: {pattern}")
    
    return input_str


def sanitize_html(html_str: str) -> str:
    """
    Sanitize HTML to prevent XSS attacks
    
    Args:
        html_str: HTML string to sanitize
    
    Returns:
        Sanitized HTML string
    """
    # Escape HTML special characters
    sanitized = html.escape(html_str)
    
    # Remove script tags and event handlers (basic)
    sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized


def sanitize_path(base_path: Path, user_path: str) -> Path:
    """
    Sanitize and validate file paths to prevent path traversal
    
    Args:
        base_path: Base directory path
        user_path: User-provided path
    
    Returns:
        Resolved, sanitized path
    
    Raises:
        ValidationError: If path traversal is detected
    """
    # Remove null bytes
    cleaned = user_path.replace('\0', '')
    
    # Normalize the path
    path = Path(cleaned)
    
    # Resolve relative to base path
    try:
        resolved = (base_path / path).resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid path: {e}")
    
    # Ensure the resolved path is still within base_path
    try:
        base_resolved = base_path.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise ValidationError(f"Path traversal detected: {user_path}")
    except OSError:
        raise ValidationError(f"Cannot resolve base path: {base_path}")
    
    return resolved


def validate_sql_safe(input_str: str) -> str:
    """
    Basic SQL injection prevention check
    
    Note: This is a basic check. Always use parameterized queries!
    
    Args:
        input_str: Input string to check
    
    Returns:
        Input string if safe
    
    Raises:
        ValidationError: If potentially dangerous patterns detected
    """
    dangerous_patterns = [
        r"';",
        r'";',
        r'--',
        r'/\*',
        r'\*/',
        r'xp_',
        r'sp_',
        r'exec\s*\(',
        r'execute\s*\(',
        r'union\s+select',
        r'union\s+all\s+select',
    ]
    
    lower_input = input_str.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, lower_input):
            raise ValidationError(f"Potentially dangerous SQL pattern detected")
    
    return input_str


def validate_command_safe(input_str: str) -> str:
    """
    Basic command injection prevention check
    
    Args:
        input_str: Input string to check
    
    Returns:
        Input string if safe
    
    Raises:
        ValidationError: If potentially dangerous patterns detected
    """
    dangerous_patterns = [
        '&&',
        '||',
        ';',
        '|',
        '`',
        '$(',
        '<(',
        '>',
        '<',
        '\n',
    ]
    
    for pattern in dangerous_patterns:
        if pattern in input_str:
            raise ValidationError(f"Potentially dangerous command pattern detected")
    
    return input_str


def validate_email(email: str) -> str:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError("Invalid email format")
    return email


def validate_url(url: str) -> str:
    """Validate URL format"""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(pattern, url):
        raise ValidationError("Invalid URL format")
    return url
