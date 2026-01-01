# src/models/exchange.py
"""
Exchange Configuration and Data Models
Модели для управления параметрами бирж и обработки рыночных данных
"""

from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.database import Base


class ExchangeType(str, Enum):
    """Поддерживаемые биржи"""
    BINANCE = "binance"
    KRAKEN = "kraken"
    COINBASE = "coinbase"
    BYBIT = "bybit"
    DYDX = "dydx"


class OrderSide(str, Enum):
    """Сторона ордера"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Тип ордера"""
    LIMIT = "limit"
    MARKET = "market"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(str, Enum):
    """Статус ордера"""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExchangeConfig(Base):
    """
    Конфигурация подключения к бирже
    """
    __tablename__ = "exchange_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    exchange_type = Column(String, nullable=False)  # ExchangeType
    name = Column(String, unique=True, index=True, nullable=False)
    
    # API credentials (encrypted in production)
    api_key = Column(String, nullable=False)
    api_secret = Column(String, nullable=False)
    passphrase = Column(String, nullable=True)  # для Kraken и Coinbase
    
    # Connection settings
    sandbox_mode = Column(Boolean, default=False)
    rate_limit = Column(Integer, default=1200)  # requests per minute
    
    # Features enabled
    trading_enabled = Column(Boolean, default=True)
    margin_trading_enabled = Column(Boolean, default=False)
    futures_trading_enabled = Column(Boolean, default=False)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync = Column(DateTime, nullable=True)
    
    # Relationships
    orders = relationship("Order", back_populates="exchange_config")
    balances = relationship("Balance", back_populates="exchange_config")
    tickers = relationship("Ticker", back_populates="exchange_config")
    orderbooks = relationship("OrderBook", back_populates="exchange_config")
    
    __table_args__ = (
        Index('ix_user_exchange', 'user_id', 'exchange_type'),
    )
    
    class Config:
        from_attributes = True


class Ticker(Base):
    """
    Текущая информация по паре (bid, ask, last price)
    """
    __tablename__ = "tickers"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange_config_id = Column(Integer, ForeignKey("exchange_configs.id"), nullable=False, index=True)
    
    symbol = Column(String, index=True, nullable=False)  # BTC/USDT
    
    # Price data
    bid = Column(Float, nullable=False)
    ask = Column(Float, nullable=False)
    last = Column(Float, nullable=False)
    
    # Volume
    volume_24h = Column(Float, default=0.0)
    volume_quote_24h = Column(Float, default=0.0)
    
    # Change percentage
    change_24h_percent = Column(Float, default=0.0)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    exchange_config = relationship("ExchangeConfig", back_populates="tickers")
    
    __table_args__ = (
        Index('ix_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    class Config:
        from_attributes = True


class OrderBook(Base):
    """
    Снимок стакана ордеров (bids, asks)
    """
    __tablename__ = "orderbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange_config_id = Column(Integer, ForeignKey("exchange_configs.id"), nullable=False, index=True)
    
    symbol = Column(String, index=True, nullable=False)
    
    # JSON arrays: [[price, size], ...]
    bids = Column(JSON, nullable=False)  # [[price, quantity], ...]
    asks = Column(JSON, nullable=False)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    sequence = Column(Integer, nullable=True)  # для отслеживания обновлений
    
    # Relationships
    exchange_config = relationship("ExchangeConfig", back_populates="orderbooks")
    
    __table_args__ = (
        Index('ix_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    class Config:
        from_attributes = True


class Balance(Base):
    """
    Баланс кошелька на бирже
    """
    __tablename__ = "balances"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange_config_id = Column(Integer, ForeignKey("exchange_configs.id"), nullable=False, index=True)
    
    currency = Column(String, index=True, nullable=False)  # BTC, ETH, USDT
    
    # Balance breakdown
    free = Column(Float, default=0.0)  # доступно для торговли
    used = Column(Float, default=0.0)  # заморожено в ордерах
    total = Column(Float, default=0.0)  # free + used
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    exchange_config = relationship("ExchangeConfig", back_populates="balances")
    
    __table_args__ = (
        Index('ix_exchange_currency', 'exchange_config_id', 'currency'),
    )
    
    class Config:
        from_attributes = True


class Order(Base):
    """
    История ордеров на бирже
    """
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange_config_id = Column(Integer, ForeignKey("exchange_configs.id"), nullable=False, index=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True, index=True)
    
    # Order identification
    exchange_order_id = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    
    # Order details
    side = Column(String, nullable=False)  # OrderSide
    order_type = Column(String, nullable=False)  # OrderType
    status = Column(String, default="pending", nullable=False, index=True)  # OrderStatus
    
    # Price and quantity
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    filled = Column(Float, default=0.0)
    remaining = Column(Float, nullable=False)
    
    # Cost and fees
    cost = Column(Float, default=0.0)
    fee_amount = Column(Float, default=0.0)
    fee_currency = Column(String, nullable=True)
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    exchange_config = relationship("ExchangeConfig", back_populates="orders")
    
    __table_args__ = (
        Index('ix_symbol_status_timestamp', 'symbol', 'status', 'timestamp'),
    )
    
    class Config:
        from_attributes = True
