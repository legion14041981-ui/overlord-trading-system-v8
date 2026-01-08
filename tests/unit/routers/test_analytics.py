"""
Unit tests for Analytics Router
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_get_portfolio_summary():
    """Test portfolio summary endpoint."""
    from src.routers.analytics import get_portfolio_summary
    
    result = await get_portfolio_summary()
    
    assert isinstance(result, dict)
    assert "total_value" in result
    assert "positions_count" in result
    assert "unrealized_pnl" in result


@pytest.mark.asyncio
async def test_get_portfolio_performance():
    """Test portfolio performance endpoint."""
    from src.routers.analytics import get_portfolio_performance
    
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    result = await get_portfolio_performance(start_date=start_date, end_date=end_date)
    
    assert isinstance(result, dict)
    assert "total_return" in result
    assert "sharpe_ratio" in result
    assert "max_drawdown" in result


@pytest.mark.asyncio
async def test_get_trade_statistics():
    """Test trade statistics endpoint."""
    from src.routers.analytics import get_trade_statistics
    
    result = await get_trade_statistics()
    
    assert isinstance(result, dict)
    assert "total_trades" in result
    assert "win_rate" in result
    assert "profit_factor" in result
