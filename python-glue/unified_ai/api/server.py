"""FastAPI server application"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .routes import router
from .auth_routes import router as auth_router
from .middleware import SecurityHeadersMiddleware, setup_cors, APIKeyMiddleware
from .csrf import CSRFProtectionMiddleware
from ..config import load_config
from ..observability import setup_logging, MetricsCollector


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    config = load_config()
    app.state.config = config
    app.state.metrics = MetricsCollector()
    setup_logging()
    
    yield
    
    # Shutdown
    # Cleanup if needed


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    
    app = FastAPI(
        title="Unified AI Orchestrator API",
        version="1.0.0",
        description="Unified AI tool orchestration system API",
        lifespan=lifespan,
    )
    
    # Add request size limit middleware (10MB)
    @app.middleware("http")
    async def limit_request_size(request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            if size > 10 * 1024 * 1024:  # 10MB
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request too large. Maximum size is 10MB."}
                )
        return await call_next(request)
    
    # Setup CORS
    setup_cors(app)
    
    # Add API key authentication middleware
    config = load_config()
    mobile_api_key = None
    if hasattr(config, 'api') and hasattr(config.api, 'api_key'):
        mobile_api_key = config.api.api_key
    
    app.add_middleware(APIKeyMiddleware, api_key=mobile_api_key)
    
    # Add rate limiting middleware
    rate_limit = 60
    if hasattr(config, 'api') and hasattr(config.api, 'rate_limit_per_minute'):
        rate_limit = config.api.rate_limit_per_minute
    
    from .middleware import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit)
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add CSRF protection (only for state-changing operations)
    # Note: CSRF protection can be disabled for API-only usage
    import os
    if os.getenv("ENABLE_CSRF", "true").lower() == "true":
        app.add_middleware(CSRFProtectionMiddleware)
    
    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Root route - serve mobile UI
    @app.get("/")
    async def root():
        """Serve mobile UI"""
        mobile_html = static_dir / "mobile.html"
        if mobile_html.exists():
            return FileResponse(str(mobile_html))
        return {"message": "Unified AI Orchestrator API", "version": "1.0.0"}
    
    # Include routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy"}
    
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        metrics_collector = app.state.metrics
        from fastapi.responses import Response
        return Response(
            content=metrics_collector.export(),
            media_type="text/plain",
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler"""
        from fastapi.responses import JSONResponse
        from pydantic import ValidationError
        from ..security.validation import ValidationError as SecurityValidationError
        
        # Handle Pydantic validation errors
        if isinstance(exc, ValidationError):
            return JSONResponse(
                status_code=422,
                content={"error": "Validation error", "details": exc.errors()},
            )
        
        # Handle security validation errors
        if isinstance(exc, SecurityValidationError):
            return JSONResponse(
                status_code=400,
                content={"error": str(exc)},
            )
        
        # Handle HTTP exceptions
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": exc.detail},
            )
        
        # Generic error
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )
    
    return app


def main():
    """Run the API server"""
    app = create_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
