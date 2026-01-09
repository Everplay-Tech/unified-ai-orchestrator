"""FastAPI server application"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .routes import router
from .middleware import SecurityHeadersMiddleware, setup_cors
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
    app = FastAPI(
        title="Unified AI Orchestrator API",
        version="1.0.0",
        description="Unified AI tool orchestration system API",
        lifespan=lifespan,
    )
    
    # Setup CORS
    setup_cors(app)
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Include routers
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
