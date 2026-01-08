"""
Unit tests for Monitoring Router
"""
import pytest


@pytest.mark.asyncio
async def test_get_detailed_health():
    """Test detailed health check endpoint."""
    from src.routers.monitoring import get_detailed_health
    
    result = await get_detailed_health()
    
    assert isinstance(result, dict)
    assert "status" in result
    assert "components" in result
    assert "system" in result
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_system_metrics():
    """Test system metrics endpoint."""
    from src.routers.monitoring import get_system_metrics
    
    result = await get_system_metrics()
    
    assert isinstance(result, dict)
    assert "api_metrics" in result
    assert "system_metrics" in result
    assert "process_metrics" in result


@pytest.mark.asyncio
async def test_get_prometheus_metrics():
    """Test Prometheus metrics endpoint."""
    from src.routers.monitoring import get_prometheus_metrics
    
    result = await get_prometheus_metrics()
    
    assert isinstance(result, str)
    assert "api_requests_total" in result
    assert "api_request_duration_ms" in result
