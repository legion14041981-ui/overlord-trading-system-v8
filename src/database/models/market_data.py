"""
Market Data Models for Overlord v8.1

Defines SQLAlchemy models for storing and managing market data:
- OHLC (Open, High, Low, Close) candlestick data
- Real-time market snapshots
- Market events (price updates, volume spikes)
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    Index, ForeignKey, Enum, UniqueConstraint, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from src.database.connection import Base


class TimeframeEnum(str, enum.Enum):
    """Market data timeframe enumeration"""
    TICK = "tick"
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


class ExchangeEnum(str, enum.Enum):
    """Supported exchanges"""
    WALBI = "walbi"
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    BYBIT = "bybit"


class MarketDataSource(Base):
    """Market data source configuration"""
    __tablename__ = "market_data_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(Enum(ExchangeEnum), nullable=False, index=True)
    base_asset = Column(String(10), nullable=False)
    quote_asset = Column(String(10), nullable=False)
    min_price_increment = Column(Float, default=0.00000001)
    min_quantity = Column(Float, default=0.00000001)
    max_quantity = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    ohlc_data = relationship("OHLCData", back_populates="source", cascade="all, delete-orphan")
    market_snapshots = relationship("MarketSnapshot", back_populates="source", cascade="all, delete-orphan")
    market_events = relationship("MarketEvent", back_populates="source", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('symbol', 'exchange', name='uq_symbol_exchange'),
        Index('ix_market_data_sources_active', 'is_active'),
    )


class OHLCData(Base):
    """OHLC candlestick data for market analysis"""
    __tablename__ = "ohlc_data"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("market_data_sources.id"), nullable=False, index=True)
    timeframe = Column(Enum(TimeframeEnum), nullable=False, index=True)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    quote_volume = Column(Float, nullable=True)  # Volume in quote asset
    trades_count = Column(Integer, nullable=True)
    taker_buy_volume = Column(Float, nullable=True)  # For crypto exchanges
    taker_buy_quote_volume = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    source = relationship("MarketDataSource", back_populates="ohlc_data")
    
    __table_args__ = (
        UniqueConstraint('source_id', 'timeframe', 'timestamp', name='uq_ohlc_timestamp'),
        Index('ix_ohlc_source_timeframe_timestamp', 'source_id', 'timeframe', 'timestamp'),
    )


class MarketSnapshot(Base):
    """Real-time market snapshot at specific timestamp"""
    __tablename__ = "market_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("market_data_sources.id"), nullable=False, index=True)
    bid_price = Column(Float, nullable=False)
    ask_price = Column(Float, nullable=False)
    bid_volume = Column(Float, nullable=False)
    ask_volume = Column(Float, nullable=False)
    last_price = Column(Float, nullable=False)
    last_quantity = Column(Float, nullable=False)
    last_trade_time = Column(DateTime, nullable=True)
    
    # Market statistics
    twenty_four_high = Column(Float, nullable=True)
    twenty_four_low = Column(Float, nullable=True)
    twenty_four_volume = Column(Float, nullable=True)
    twenty_four_quote_volume = Column(Float, nullable=True)
    open_interest = Column(Float, nullable=True)  # For futures
    
    # Technical indicators (calculated)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    bollinger_middle = Column(Float, nullable=True)
    
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    source = relationship("MarketDataSource", back_populates="market_snapshots")
    
    __table_args__ = (
        UniqueConstraint('source_id', 'timestamp', name='uq_snapshot_timestamp'),
        Index('ix_market_snapshot_source_timestamp', 'source_id', 'timestamp'),
        Index('ix_market_snapshot_prices', 'bid_price', 'ask_price', 'last_price'),
    )


class MarketEventTypeEnum(str, enum.Enum):
    """Types of market events"""
    PRICE_SPIKE = "price_spike"
    VOLUME_SPIKE = "volume_spike"
    VOLATILITY_HIGH = "volatility_high"
    SUPPORT_BREAK = "support_break"
    RESISTANCE_BREAK = "resistance_break"
    TREND_CHANGE = "trend_change"
    MOVING_AVERAGE_CROSS = "ma_cross"
    RSI_EXTREME = "rsi_extreme"
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"
    DIVERGENCE = "divergence"
    PUMP_AND_DUMP = "pump_and_dump"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    EXCHANGE_NEWS = "exchange_news"
    CUSTOM = "custom"


class MarketEvent(Base):
    """Market events detected by analysis engine"""
    __tablename__ = "market_events"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("market_data_sources.id"), nullable=False, index=True)
    event_type = Column(Enum(MarketEventTypeEnum), nullable=False, index=True)
    
    # Event details
    description = Column(String(500), nullable=True)
    price = Column(Float, nullable=False)
    price_change_pct = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    confidence = Column(Float, default=0.5)  # 0.0 to 1.0
    
    # Additional context
    previous_price = Column(Float, nullable=True)
    support_level = Column(Float, nullable=True)
    resistance_level = Column(Float, nullable=True)
    
    # Event severity for alerting
    severity = Column(String(10), default="info")  # info, warning, critical
    
    # Status tracking
    is_processed = Column(Boolean, default=False, index=True)
    is_archived = Column(Boolean, default=False, index=True)
    
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    source = relationship("MarketDataSource", back_populates="market_events")
    
    __table_args__ = (
        Index('ix_market_event_type_timestamp', 'event_type', 'timestamp'),
        Index('ix_market_event_source_processed', 'source_id', 'is_processed', 'timestamp'),
    )


class PriceAlert(Base):
    """Price-based alerts for monitoring"""
    __tablename__ = "price_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("market_data_sources.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Alert conditions
    trigger_condition = Column(String(20), nullable=False)  # "above", "below", "crosses"
    target_price = Column(Float, nullable=False)
    
    # Optional: Secondary condition for cross alerts
    secondary_condition = Column(String(20), nullable=True)
    secondary_price = Column(Float, nullable=True)
    
    # Alert status
    is_active = Column(Boolean, default=True, index=True)
    triggered_at = Column(DateTime, nullable=True)
    triggered_price = Column(Float, nullable=True)
    
    # Notification preferences
    notify_email = Column(Boolean, default=True)
    notify_sms = Column(Boolean, default=False)
    notify_push = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_price_alert_user_active', 'user_id', 'is_active'),
        Index('ix_price_alert_source_active', 'source_id', 'is_active'),
    )


# Summary statistics for market analysis
class MarketStatistics(Base):
    """Market statistics for analysis and reporting"""
    __tablename__ = "market_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("market_data_sources.id"), nullable=False, index=True)
    
    # Daily statistics
    daily_high = Column(Float, nullable=False)
    daily_low = Column(Float, nullable=False)
    daily_open = Column(Float, nullable=False)
    daily_close = Column(Float, nullable=False)
    daily_volume = Column(Float, nullable=False)
    daily_trades = Column(Integer, nullable=True)
    
    # Weekly statistics
    weekly_volume = Column(Float, nullable=True)
    weekly_high = Column(Float, nullable=True)
    weekly_low = Column(Float, nullable=True)
    
    # Volatility metrics
    volatility_daily = Column(Float, nullable=True)
    volatility_weekly = Column(Float, nullable=True)
    volatility_monthly = Column(Float, nullable=True)
    
    # Correlation metrics
    correlation_btc = Column(Float, nullable=True)  # Crypto correlation to BTC
    
    # Market regime
    market_regime = Column(String(20), nullable=True)  # "bullish", "bearish", "sideways"
    strength = Column(Float, nullable=True)  # 0-100
    
    date = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('source_id', 'date', name='uq_market_stats_date'),
        Index('ix_market_stats_source_date', 'source_id', 'date'),
    )
