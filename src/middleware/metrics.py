"""
Metrics Collection Middleware
Collects request metrics for Prometheus/monitoring
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Simple in-memory metrics collector."""
    
    def __init__(self):
        self.requests_total = 0
        self.requests_by_method: Dict[str, int] = {}
        self.requests_by_status: Dict[int, int] = {}
        self.request_duration_sum = 0.0
        self.request_duration_count = 0
    
    def record_request(self, method: str, status_code: int, duration: float):
        """Record a request metric."""
        self.requests_total += 1
        self.requests_by_method[method] = self.requests_by_method.get(method, 0) + 1
        self.requests_by_status[status_code] = self.requests_by_status.get(status_code, 0) + 1
        self.request_duration_sum += duration
        self.request_duration_count += 1
    
    def get_metrics(self) -> dict:
        """Get current metrics."""
        avg_duration = (
            self.request_duration_sum / self.request_duration_count
            if self.request_duration_count > 0
            else 0
        )
        
        return {
            "requests_total": self.requests_total,
            "requests_by_method": self.requests_by_method,
            "requests_by_status": self.requests_by_status,
            "average_duration_ms": round(avg_duration * 1000, 2),
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics."""
    
    def __init__(self, app, collector: Optional[MetricsCollector] = None):
        super().__init__(app)
        self.collector = collector or metrics_collector
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Record metrics
            self.collector.record_request(
                method=request.method,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            # Record error metric (500)
            self.collector.record_request(
                method=request.method,
                status_code=500,
                duration=duration
            )
            raise


def get_metrics() -> dict:
    """Get current metrics from global collector."""
    return metrics_collector.get_metrics()
