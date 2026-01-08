"""
Unit tests for Metrics Middleware
"""
import pytest
import asyncio
from src.middleware.metrics import MetricsCollector


def test_metrics_collector_init():
    """Test metrics collector initialization."""
    collector = MetricsCollector()
    
    assert collector.requests_total == 0
    assert len(collector.requests_by_method) == 0
    assert len(collector.requests_by_status) == 0


def test_metrics_collector_record_request():
    """Test recording a request metric."""
    collector = MetricsCollector()
    
    collector.record_request("GET", 200, 0.1)
    
    assert collector.requests_total == 1
    assert collector.requests_by_method["GET"] == 1
    assert collector.requests_by_status[200] == 1


def test_metrics_collector_get_metrics():
    """Test getting metrics summary."""
    collector = MetricsCollector()
    
    collector.record_request("GET", 200, 0.1)
    collector.record_request("POST", 201, 0.2)
    collector.record_request("GET", 404, 0.05)
    
    metrics = collector.get_metrics()
    
    assert metrics["requests_total"] == 3
    assert metrics["requests_by_method"]["GET"] == 2
    assert metrics["requests_by_method"]["POST"] == 1
    assert metrics["requests_by_status"][200] == 1
    assert metrics["requests_by_status"][404] == 1
    assert "average_duration_ms" in metrics
