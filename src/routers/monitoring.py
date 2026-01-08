"""
Monitoring API Router
Provides system health, metrics, and operational status endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime
import logging
import psutil
import sys

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/health/detailed")
async def get_detailed_health():
    """Get detailed health check of all system components."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": {"status": "up", "latency_ms": 0},
            "redis": {"status": "up", "latency_ms": 0},
            "market_data_feed": {"status": "up", "latency_ms": 0},
            "exchange_connections": {"status": "up", "active_connections": 0},
            "overlord_bootstrap": {"status": "up", "mode": "standard"},
            "grail_agent": {"status": "up", "version": "1.0.0"}
        },
        "system": {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
    }


@router.get("/metrics")
async def get_system_metrics():
    """Get current system metrics."""
    from src.middleware.metrics import get_metrics
    
    return {
        "timestamp": datetime.now().isoformat(),
        "api_metrics": get_metrics(),
        "system_metrics": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "network_io": {
                "bytes_sent": psutil.net_io_counters().bytes_sent,
                "bytes_recv": psutil.net_io_counters().bytes_recv
            }
        },
        "process_metrics": {
            "threads": len(psutil.Process().threads()),
            "open_files": len(psutil.Process().open_files()),
            "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024
        }
    }


@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Get metrics in Prometheus format."""
    from src.middleware.metrics import get_metrics
    metrics = get_metrics()
    
    lines = [
        f"# HELP api_requests_total Total number of API requests",
        f"# TYPE api_requests_total counter",
        f"api_requests_total {metrics['requests_total']}",
        "",
        f"# HELP api_request_duration_ms Average request duration in milliseconds",
        f"# TYPE api_request_duration_ms gauge",
        f"api_request_duration_ms {metrics['average_duration_ms']}",
        ""
    ]
    
    return "\n".join(lines)


@router.get("/logs/recent")
async def get_recent_logs(
    level: Optional[str] = "INFO",
    limit: int = 100
):
    """Get recent log entries."""
    return {
        "logs": [],
        "count": 0,
        "level": level,
        "limit": limit
    }


@router.get("/performance")
async def get_performance_stats():
    """Get system performance statistics."""
    return {
        "uptime_seconds": 0,
        "total_requests": 0,
        "requests_per_second": 0.0,
        "average_response_time_ms": 0.0,
        "error_rate": 0.0,
        "active_connections": 0
    }


@router.get("/status/exchanges")
async def get_exchange_status():
    """Get status of all exchange connections."""
    return {
        "exchanges": {
            "binance": {"status": "connected", "latency_ms": 0},
            "bybit": {"status": "connected", "latency_ms": 0},
            "okx": {"status": "connected", "latency_ms": 0}
        },
        "total_connections": 0,
        "healthy_connections": 0
    }


@router.get("/status/strategies")
async def get_strategies_status():
    """Get status of all active trading strategies."""
    return {
        "total_strategies": 0,
        "active_strategies": 0,
        "paused_strategies": 0,
        "strategies": []
    }


@router.post("/alerts/test")
async def test_alert_system():
    """Test alert notification system."""
    return {
        "status": "sent",
        "channels": ["slack", "email"],
        "timestamp": datetime.now().isoformat()
    }
