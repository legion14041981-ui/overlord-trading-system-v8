# src/models/market_data.py
"""
Market Data Models
Модели для управления рыночными данными
"""

from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey, Index, BigInteger
from sqlalchemy.orm import relationship

from src.database import Base


class TimeFrame(str, Enum):
    """Временные фреймы"""
    M1 = "1m"  # 1 минута
    M5 = "5m"  # 5 минут
    M15 = "15m"  # 15 минут
    M30 = "30m"  # 30 минут
    H1 = "1h"  # 1 час
    H4 = "4h"  # 4 часа
    D1 = "1d"  # 1 день
    W1 = "1w"  # 1 неделя
    MN1 = "1mo"  # 1 месяц


class Candle(Base):
    """
    Свеча OHLCV (открытие, высоко, низко, закрытие, объём)
    """
    __tablename__ = "candles"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange_config_id = Column(Integer, ForeignKey("exchange_configs.id"), nullable=False, index=True)
    
    # Identification
    symbol = Column(String, index=True, nullable=False)  # BTC/USDT
    timeframe = Column(String, nullable=False)  # TimeFrame (1m, 5m, 1h, 1d)
    
    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)  # объём в базовом активе
    quote_volume = Column(Float, nullable=False)  # объём в котируюмом активе
    
    # Trade statistics
    trades_count = Column(Integer, default=0)  # кол-во трейдов
    buy_volume = Column(Float, default=0.0)  # объём покупок
    sell_volume = Column(Float, default=0.0)  # объём покрытий
    
    # Metadata
    open_time = Column(DateTime, nullable=False, index=True)  # время открытия
    close_time = Column(DateTime, nullable=False)  # время закрытия
    is_closed = Column(Boolean, default=False)  # закрыта ли
    timestamp = Column(DateTime, default=datetime.utcnow)  # время сохранения
    
    # Technical indicators (optional, cached)
    indicators_cache = Column(JSON, nullable=True)  # {"rsi": 65.2, "macd": 0.15, ...}
    
    __table_args__ = (
        Index('ix_symbol_timeframe_opentime', 'symbol', 'timeframe', 'open_time'),
    )
    
    class Config:
        from_attributes = True


class TickData(Base):
    """
    Тиковые данные (каждый трейд)
    """
    __tablename__ = "tick_data"
    
    id = Column(BigInteger, primary_key=True, index=True)
    exchange_config_id = Column(Integer, ForeignKey("exchange_configs.id"), nullable=False, index=True)
    
    # Identification
    symbol = Column(String, index=True, nullable=False)
    exchange_trade_id = Column(BigInteger, unique=True, nullable=False)  # трейд ID на бирже
    
    # Trade data
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    
    # Trade statistics
    is_buyer_maker = Column(Boolean, nullable=False)  # кто инициировал
    commission = Column(Float, default=0.0)
    commission_asset = Column(String, nullable=True)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    class Config:
        from_attributes = True


class MarketData(Base):
    """
    Агрегированные рыночные данные для аналитики
    """
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange_config_id = Column(Integer, ForeignKey("exchange_configs.id"), nullable=False, index=True)
    
    # Identification
    symbol = Column(String, index=True, nullable=False)
    period_type = Column(String, nullable=False)  # day, week, month
    
    # Period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    
    # OHLCV aggregation
    price_open = Column(Float, nullable=False)
    price_high = Column(Float, nullable=False)
    price_low = Column(Float, nullable=False)
    price_close = Column(Float, nullable=False)
    volume_total = Column(Float, nullable=False)
    
    # Volume analysis
    volume_buy = Column(Float, default=0.0)
    volume_sell = Column(Float, default=0.0)
    volume_buy_percent = Column(Float, default=0.0)
    
    # Price changes
    price_change = Column(Float, default=0.0)  # close - open
    price_change_percent = Column(Float, default=0.0)
    
    # Volatility
    volatility_high_low = Column(Float, default=0.0)  # (high - low) / open
    volatility_open_close = Column(Float, default=0.0)  # (close - open) / open
    
    # Statistics
    trades_count = Column(Integer, default=0)
    unique_buyers = Column(Integer, default=0)
    unique_sellers = Column(Integer, default=0)
    
    # Large trades
    large_trades_count = Column(Integer, default=0)
    large_trades_volume = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_symbol_period', 'symbol', 'period_type', 'period_start'),
    )
    
    class Config:
        from_attributes = True


class MarketCorrelation(Base):
    """
    Корреляция между торговыми парами
    """
    __tablename__ = "market_correlations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Pair identification
    symbol_1 = Column(String, index=True, nullable=False)
    symbol_2 = Column(String, index=True, nullable=False)
    
    # Timeframe
    timeframe = Column(String, nullable=False)  # 1h, 4h, 1d, 1w
    
    # Correlation metrics
    correlation_coefficient = Column(Float, nullable=False)  # -1.0 to 1.0
    lookback_period = Column(Integer, nullable=False)  # кол-во периодов
    
    # Metadata
    calculated_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False)  # когда становится актуальной
    
    __table_args__ = (
        Index('ix_symbols_timeframe', 'symbol_1', 'symbol_2', 'timeframe'),
    )
    
    class Config:
        from_attributes = True
