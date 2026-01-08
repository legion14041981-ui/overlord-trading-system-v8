"""
Unit tests for Risk Management Router
"""
import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_get_current_exposure():
    """Test current exposure endpoint."""
    from src.routers.risk import get_current_exposure
    
    result = await get_current_exposure()
    
    assert isinstance(result, dict)
    assert "total_exposure" in result
    assert "leverage" in result
    assert "margin_usage" in result


@pytest.mark.asyncio
async def test_get_risk_limits():
    """Test risk limits endpoint."""
    from src.routers.risk import get_risk_limits
    
    result = await get_risk_limits()
    
    assert isinstance(result, dict)
    assert "position_size_limit" in result
    assert "loss_limits" in result
    assert "leverage_limits" in result


@pytest.mark.asyncio
async def test_calculate_var():
    """Test VaR calculation endpoint."""
    from src.routers.risk import calculate_var
    
    result = await calculate_var(confidence_level=0.95, horizon_days=1)
    
    assert isinstance(result, dict)
    assert "var" in result
    assert result["confidence_level"] == 0.95
    assert result["horizon_days"] == 1


@pytest.mark.asyncio
async def test_run_stress_test():
    """Test stress testing endpoint."""
    from src.routers.risk import run_stress_test
    
    result = await run_stress_test(scenario="market_crash")
    
    assert isinstance(result, dict)
    assert "scenario" in result
    assert "impact" in result
    assert result["scenario"] == "market_crash"
