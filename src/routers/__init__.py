"""
API Routers package for Overlord Trading System v8.1
"""
from .auth import router as auth_router
from .users import router as users_router
from .strategies import router as strategies_router
from .trades import router as trades_router
from .analytics import router as analytics_router
from .risk import router as risk_router
from .monitoring import router as monitoring_router
from .market_data import router as market_data_router
from .system import router as system_router

__all__ = [
    "auth_router",
    "users_router",
    "strategies_router",
    "trades_router",
    "analytics_router",
    "risk_router",
    "monitoring_router",
    "market_data_router",
    "system_router",
]
