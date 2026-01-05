"""
FastAPI application entry point for Overlord Trading System v8.1
Integrated with Overlord Bootstrap & Grail Agent
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.database import engine, Base
from src.routers import users_router, strategies_router, trades_router, auth_router
from src.core.bootstrap import create_overlord
from src.auth import get_grail_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
overlord = None
grail = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    global overlord, grail
    
    # Startup
    logger.info("="*60)
    logger.info("Starting Overlord Trading System v8.1...")
    logger.info("="*60)
    
    try:
        # Initialize Overlord Bootstrap
        mode = os.getenv('OVERLORD_MODE', 'standard')
        config_path = os.getenv('OVERLORD_CONFIG', 'config/default.yaml')
        
        overlord = create_overlord(config_path=config_path, mode=mode)
        if not overlord.start():
            raise RuntimeError("Overlord initialization failed")
        
        logger.info("✅ Overlord Bootstrap initialized")
        
        # Initialize Grail Agent
        grail = get_grail_agent()
        logger.info(f"✅ Grail Agent v{grail.VERSION} initialized")
        
        # Initialize database
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables initialized successfully")
        
        # Health check
        health = overlord.health_check()
        logger.info(f"System Status: {health['status']}")
        logger.info(f"Modules Loaded: {len(health.get('modules', {}))}")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("="*60)
    logger.info("Shutting down Overlord Trading System v8.1...")
    logger.info("="*60)
    
    if overlord:
        overlord.stop()
    
    await engine.dispose()
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


# Security middleware using Grail Agent
@app.middleware("http")
async def grail_security_middleware(request: Request, call_next):
    """Grail Agent security middleware for token validation."""
    # Skip auth for public endpoints
    public_paths = ["/", "/health", "/api/docs", "/api/redoc", "/api/openapi.json"]
    if request.url.path in public_paths:
        return await call_next(request)
    
    # Check for authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
        # Validate session token using Grail Agent
        if grail:
            is_valid, user_id = grail.verify_session_token(token)
            if is_valid:
                request.state.user_id = user_id
                return await call_next(request)
    
    # Token validation failed for protected routes
    # For now, just log and continue (implement strict auth in production)
    logger.warning(f"Unauthenticated access to {request.url.path}")
    return await call_next(request)


# Register API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(strategies_router, prefix="/api/v1")
app.include_router(trades_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check."""
    return JSONResponse(
        content={
            "status": "online",
            "service": "Overlord Trading System",
            "version": "8.1.0",
            "docs": "/api/docs",
            "grail_agent": "active" if grail else "inactive",
            "overlord": "active" if overlord else "inactive"
        }
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    health_data = {
        "status": "healthy",
        "database": "connected",
    }
    
    if overlord:
        overlord_health = overlord.health_check()
        health_data["overlord"] = overlord_health
    
    if grail:
        grail_health = grail.get_health_status()
        health_data["grail"] = grail_health
    
    return JSONResponse(content=health_data)


@app.get("/api/v1/status", tags=["Status"])
async def api_status():
    """API status endpoint with detailed information."""
    return JSONResponse(
        content={
            "api_version": "v1",
            "status": "operational",
            "mode": overlord.mode if overlord else "unknown",
            "endpoints": {
                "users": "/api/v1/users",
                "strategies": "/api/v1/strategies",
                "trades": "/api/v1/trades"
            }
        }
    )


@app.get("/api/v1/grail/token/validate", tags=["Security"])
async def validate_github_token(request: Request):
    """Validate GitHub PAT token using Grail Agent."""
    if not grail:
        raise HTTPException(status_code=503, detail="Grail Agent not available")
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    is_valid, metadata = grail.validate_github_token(token)
    
    return JSONResponse(
        content={
            "valid": is_valid,
            "metadata": metadata
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
