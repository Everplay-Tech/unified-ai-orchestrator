"""CSRF protection middleware"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Optional
import secrets


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware"""
    
    def __init__(self, app: ASGIApp, secret_key: Optional[str] = None):
        super().__init__(app)
        self.secret_key = secret_key or secrets.token_urlsafe(32)
    
    def _get_csrf_token(self, request: Request) -> Optional[str]:
        """Get CSRF token from request"""
        # Try header first
        token = request.headers.get("X-CSRF-Token")
        if token:
            return token
        
        # Try cookie
        token = request.cookies.get("csrf_token")
        return token
    
    def _generate_csrf_token(self) -> str:
        """Generate a CSRF token"""
        return secrets.token_urlsafe(32)
    
    def _is_safe_method(self, method: str) -> bool:
        """Check if HTTP method is safe (doesn't modify state)"""
        return method.upper() in ["GET", "HEAD", "OPTIONS"]
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate CSRF token"""
        # Skip CSRF check for safe methods
        if self._is_safe_method(request.method):
            response = await call_next(request)
            # Set CSRF token cookie for safe methods
            csrf_token = self._generate_csrf_token()
            response.set_cookie(
                "csrf_token",
                csrf_token,
                httponly=False,  # JavaScript needs access for AJAX
                samesite="strict",
                secure=request.url.scheme == "https",
            )
            return response
        
        # For state-changing methods, require CSRF token
        csrf_token = self._get_csrf_token(request)
        
        if not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing"
            )
        
        # Verify token matches cookie
        cookie_token = request.cookies.get("csrf_token")
        if csrf_token != cookie_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token"
            )
        
        response = await call_next(request)
        
        # Refresh CSRF token after successful request
        new_token = self._generate_csrf_token()
        response.set_cookie(
            "csrf_token",
            new_token,
            httponly=False,
            samesite="strict",
            secure=request.url.scheme == "https",
        )
        
        return response
