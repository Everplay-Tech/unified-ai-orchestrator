"""Custom middleware for security headers and CORS"""

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import List, Optional
import os
import uuid
import secrets


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (only for HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # Content Security Policy (strict)
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "  # Needed for some UI frameworks
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # Add request ID for tracing
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        response.headers["X-Request-ID"] = request_id
        
        return response


def setup_cors(app, allowed_origins: List[str] = None):
    """Setup CORS middleware"""
    if allowed_origins is None:
        # Try to load from config
        try:
            from ..config import load_config
            config = load_config()
            if hasattr(config, 'api') and hasattr(config.api, 'allowed_origins'):
                allowed_origins = config.api.allowed_origins
        except Exception:
            pass
        
        # Default: empty list (no CORS) - must be explicitly configured
        if allowed_origins is None:
            allowed_origins = []
        
        # Replace wildcard with empty list for security
        if "*" in allowed_origins:
            import os
            if os.getenv("ENVIRONMENT") != "development":
                allowed_origins = []  # Disable wildcard in production
                import warnings
                warnings.warn("CORS wildcard (*) is disabled in production. Configure allowed_origins explicitly.")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
        max_age=3600,
    )


class APIKeyMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware"""
    
    def __init__(self, app: ASGIApp, api_key: Optional[str] = None):
        super().__init__(app)
        self.api_key = api_key or self._get_api_key()
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or keyring"""
        # Try environment variable first
        api_key = os.getenv("MOBILE_API_KEY")
        if api_key:
            return api_key
        
        # Try keyring
        try:
            from ..utils.auth import get_secret
            return get_secret("mobile_api_key")
        except Exception:
            return None
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers or query params"""
        # Try X-API-Key header (preferred)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key
        
        # Try Authorization: Bearer header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Try query parameter (fallback, less secure)
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key
        
        return None
    
    def _validate_key(self, provided_key: Optional[str]) -> bool:
        """Validate provided API key against configured key"""
        if not self.api_key:
            # If no API key configured, allow access (development mode)
            return True
        
        if not provided_key:
            return False
        
        return provided_key == self.api_key
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate API key"""
        # Skip authentication for public routes
        path = request.url.path
        
        # Check exact match for root path
        if path == "/":
            return await call_next(request)
        
        # Check prefix matches for other public paths
        public_paths = ["/health", "/metrics", "/static", "/api/v1/auth/login", "/api/v1/auth/refresh", "/docs", "/openapi.json"]
        if any(path.startswith(public) for public in public_paths):
            return await call_next(request)
        
        # Extract and validate API key
        provided_key = self._extract_api_key(request)
        
        if not self._validate_key(provided_key):
            return Response(
                status_code=401,
                content="Invalid or missing API key",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with token bucket - supports per-API-key limiting"""
    
    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        from collections import defaultdict
        from ..resilience import RateLimiter
        self.limiters = defaultdict(lambda: RateLimiter(requests_per_minute))
    
    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request for rate limiting"""
        # Try X-API-Key header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key
        
        # Try Authorization: Bearer header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Try query parameter
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key
        
        return None
    
    async def dispatch(self, request: Request, call_next):
        from fastapi.responses import Response
        
        # Skip rate limiting for public routes
        path = request.url.path
        
        # Check exact match for root path
        if path == "/":
            return await call_next(request)
        
        # Check prefix matches for other public paths
        public_paths = ["/health", "/metrics", "/static"]
        if any(path.startswith(public) for public in public_paths):
            return await call_next(request)
        
        # Get client identifier - prefer API key, fallback to IP
        api_key = self._extract_api_key(request)
        if api_key:
            client_id = f"api_key:{api_key[:8]}"  # Use first 8 chars for privacy
        else:
            client_id = request.client.host if request.client else "unknown"
        
        # Get or create rate limiter for this client
        limiter = self.limiters[client_id]
        
        # Check if request is allowed
        if not limiter.allow():
            return Response(
                status_code=429,
                content="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(limiter.remaining())
        
        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Input validation middleware for request sanitization"""
    
    async def dispatch(self, request: Request, call_next):
        from ..security.validation import validate_input, sanitize_html, sanitize_path
        
        # Skip validation for certain paths
        path = request.url.path
        skip_paths = ["/health", "/metrics", "/static", "/docs", "/openapi.json"]
        if any(path.startswith(skip) for skip in skip_paths):
            return await call_next(request)
        
        # Validate query parameters
        for key, value in request.query_params.items():
            try:
                validate_input(str(value), max_length=1000)
            except Exception as e:
                from fastapi.responses import Response
                return Response(
                    status_code=400,
                    content=f"Invalid query parameter {key}: {str(e)}",
                )
        
        # For POST/PUT requests, validate body will be handled by Pydantic models
        # But we can add additional checks here if needed
        
        response = await call_next(request)
        return response
