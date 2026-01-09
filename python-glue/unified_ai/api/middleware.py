"""Custom middleware for security headers and CORS"""

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import List, Optional
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS (only for HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
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
        
        # Default: allow all origins in development, restrict in production
        if allowed_origins is None:
            allowed_origins = ["*"]  # Should be restricted in production
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
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
        public_paths = ["/health", "/metrics", "/static"]
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
