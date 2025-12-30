"""Overlord v8.1 - Database Models

SQLAlchemy ORM models for trading system.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from src.database import Base


# Enums
class OrderSide(str, PyEnum):
    """Order side: BUY or SELL"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, PyEnum):
    """Order execution status"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionStatus(str, PyEnum):
    """Position status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


# Models
class TradingPair(Base):
    """Trading pair configuration (e.g., BTC/USDT)"""
    __tablename__ = "trading_pairs"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    base_asset = Column(String(10), nullable=False)
    quote_asset = Column(String(10), nullable=False)
    exchange = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    min_order_size = Column(Numeric(20, 8), nullable=True)
    tick_size = Column(Numeric(20, 8), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = relationship("Order", back_populates="trading_pair")
    positions = relationship("Position", back_populates="trading_pair")


class Order(Base):
    """Trading order"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(100), unique=True, nullable=False, index=True)
    trading_pair_id = Column(Integer, ForeignKey("trading_pairs.id"), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    price = Column(Numeric(20, 8), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    filled_quantity = Column(Numeric(20, 8), default=0)
    remaining_quantity = Column(Numeric(20, 8), nullable=False)
    average_fill_price = Column(Numeric(20, 8), nullable=True)
    commission = Column(Numeric(20, 8), default=0)
    commission_asset = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)

    # Relationships
    trading_pair = relationship("TradingPair", back_populates="orders")

    # Indexes
    __table_args__ = (
        Index("idx_orders_status_created", "status", "created_at"),
        Index("idx_orders_pair_status", "trading_pair_id", "status"),
    )


class Position(Base):
    """Trading position"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(String(100), unique=True, nullable=False, index=True)
    trading_pair_id = Column(Integer, ForeignKey("trading_pairs.id"), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    status = Column(Enum(PositionStatus), nullable=False, default=PositionStatus.OPEN)
    entry_price = Column(Numeric(20, 8), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    current_price = Column(Numeric(20, 8), nullable=True)
    unrealized_pnl = Column(Numeric(20, 8), default=0)
    realized_pnl = Column(Numeric(20, 8), default=0)
    exit_price = Column(Numeric(20, 8), nullable=True)
    opened_at = Column(DateTime, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    trading_pair = relationship("TradingPair", back_populates="positions")

    # Indexes
    __table_args__ = (
        Index("idx_positions_status_opened", "status", "opened_at"),
        Index("idx_positions_pair_status", "trading_pair_id", "status"),
    )


class MarketData(Base):
    """Market data snapshot"""
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open_price = Column(Numeric(20, 8), nullable=False)
    high_price = Column(Numeric(20, 8), nullable=False)
    low_price = Column(Numeric(20, 8), nullable=False)
    close_price = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    quote_volume = Column(Numeric(20, 8), nullable=True)
    number_of_trades = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_market_data_symbol_timestamp", "symbol", "timestamp"),
    )


# Export all models
__all__ = [
    "TradingPair",
    "Order",
    "Position",
    "MarketData",
    "OrderSide",
    "OrderStatus",
    "PositionStatus",
]
