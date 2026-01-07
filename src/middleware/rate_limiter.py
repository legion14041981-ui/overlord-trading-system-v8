"""[SEC-001] Rate Limiting Middleware

Provides application-level rate limiting with Prometheus metrics.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request, HTTPException
from prometheus_client import Counter
import logging

logger = logging.getLogger(__name__)

# Prometheus metrics
rate_limit_exceeded = Counter(
    'overlord_api_rate_limit_exceeded_total',
    'Total rate limit violations',
    ['endpoint', 'client_ip']
)

# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/minute"]  # Global default
)

def setup_rate_limiting(app: FastAPI):
    """Attach rate limiting to FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit violations with metrics."""
    rate_limit_exceeded.labels(
        endpoint=request.url.path,
        client_ip=get_remote_address(request)
    ).inc()
    
    logger.warning(
        f"Rate limit exceeded: {request.client.host} -> {request.url.path}"
    )
    
    raise HTTPException(
        status_code=429,
        detail={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.headers.get("Retry-After")
        }
    )

# Example usage in API endpoints:
# from fastapi import APIRouter
# from src.middleware.rate_limiter import limiter
#
# router = APIRouter()
#
# @router.post("/api/v1/orders")
# @limiter.limit("10/minute")  # Per-endpoint override
# async def create_order(request: Request, order: OrderCreate):
#     ...
