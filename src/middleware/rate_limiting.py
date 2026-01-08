"""
Rate Limiting Middleware
Implements token bucket rate limiting per client
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import Dict, Tuple
import asyncio
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket.
        
        Returns:
            True if tokens were consumed, False if rate limited
        """
        async with self._lock:
            # Refill tokens
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Try to consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests per client."""
    
    def __init__(
        self,
        app,
        requests_per_second: float = 10.0,
        burst: int = 20,
        exempt_paths: list = None
    ):
        super().__init__(app)
        self.requests_per_second = requests_per_second
        self.burst = burst
        self.exempt_paths = exempt_paths or ["/health", "/metrics", "/api/docs"]
        self.buckets: Dict[str, TokenBucket] = {}
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique key for client (IP address)."""
        if request.client:
            return request.client.host
        return "unknown"
    
    def _get_bucket(self, client_key: str) -> TokenBucket:
        """Get or create token bucket for client."""
        if client_key not in self.buckets:
            self.buckets[client_key] = TokenBucket(
                capacity=self.burst,
                refill_rate=self.requests_per_second
            )
        return self.buckets[client_key]
    
    async def dispatch(self, request: Request, call_next):
        # Check if path is exempt
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get client bucket
        client_key = self._get_client_key(request)
        bucket = self._get_bucket(client_key)
        
        # Try to consume token
        if not await bucket.consume():
            logger.warning(
                f"Rate limit exceeded",
                extra={
                    "client": client_key,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_second} requests per second allowed"
                },
                headers={"Retry-After": "1"}
            )
        
        return await call_next(request)
