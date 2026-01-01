"""
SQLAlchemy Models for Overlord v8.1 Trading System

Exports all database models for ORM operations.
"""

from src.database.connection import Base
from src.database.models.user import User, UserRole
from src.database.models.strategy import Strategy, StrategyStatus
from src.database.models.trade import Trade, TradeStatus
from src.database.models.market_data import (
    MarketDataSource,
    OHLCData,
    MarketSnapshot,
    MarketEvent,
    MarketEventTypeEnum,
    PriceAlert,
    MarketStatistics,
    TimeframeEnum,
    ExchangeEnum,
)
from src.database.models.alert import (
    AlertRule,
    AlertLog,
    AlertTemplate,
    AlertPreference,
    NotificationLog,
    AlertStatistics,
    AlertTypeEnum,
    AlertSeverityEnum,
    AlertStatusEnum,
    AlertChannelEnum,
)

__all__ = [
    # Core
    "Base",
    # User models
    "User",
    "UserRole",
    # Trading models
    "Strategy",
    "StrategyStatus",
    "Trade",
    "TradeStatus",
    # Market data models
    "MarketDataSource",
    "OHLCData",
    "MarketSnapshot",
    "MarketEvent",
    "MarketEventTypeEnum",
    "PriceAlert",
    "MarketStatistics",
    "TimeframeEnum",
    "ExchangeEnum",
    # Alert models
    "AlertRule",
    "AlertLog",
    "AlertTemplate",
    "AlertPreference",
    "NotificationLog",
    "AlertStatistics",
    "AlertTypeEnum",
    "AlertSeverityEnum",
    "AlertStatusEnum",
    "AlertChannelEnum",
]
