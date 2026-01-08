"""
FastAPI application entry point for Overlord Trading System v8.1
Simplified version for CI/CD compatibility
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("="*60)
    logger.info("Starting Overlord Trading System v8.1...")
    logger.info("="*60)
    
    try:
        logger.info("✅ Application initialized")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("="*60)
    logger.info("Shutting down Overlord Trading System v8.1...")
    logger.info("✅ Shutdown complete")
    logger.info("="*60)


# Create FastAPI application
app = FastAPI(
    title="Overlord Trading System v8.1",
    description="Enterprise-Grade Autonomous Trading System with Multi-Exchange Integration",
    version="8.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check."""
    return JSONResponse(
        content={
            "status": "online",
            "service": "Overlord Trading System",
            "version": "8.1.0",
            "docs": "/api/docs"
        }
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Kubernetes/Docker probes."""
    return JSONResponse(
        content={
            "status": "healthy",
            "version": "8.1.0"
        }
    )


@app.get("/api/v1/status", tags=["Status"])
async def api_status():
    """API status endpoint with detailed information."""
    return JSONResponse(
        content={
            "api_version": "v1",
            "status": "operational",
            "mode": "production"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
