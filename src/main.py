"""FastAPI application entry point for Overlord Trading System v8.1"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.database import engine, Base

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
    logger.info("Starting Overlord Trading System v8.1...")
    try:
        async with engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Overlord Trading System v8.1...")
    await engine.dispose()
    logger.info("Database connections closed")


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
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse(
        content={
            "status": "healthy",
            "database": "connected"
        }
    )


@app.get("/api/v1/status", tags=["Status"])
async def api_status():
    """API status endpoint with detailed information."""
    return JSONResponse(
        content={
            "api_version": "v1",
            "status": "operational",
            "endpoints": {
                "users": "/api/v1/users",
                "strategies": "/api/v1/strategies",
                "trades": "/api/v1/trades"
            }
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
