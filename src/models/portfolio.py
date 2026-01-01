# src/models/portfolio.py
"""
Portfolio and Position Management Models
Модели для управления портфелем и позициями
"""

from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.database import Base


class PositionType(str, Enum):
    """Тип позиции"""
    SPOT = "spot"  # спот
    LONG = "long"  # длинная
    SHORT = "short"  # короткая
    LEVERAGE = "leverage"  # с левериджом


class PositionStatus(str, Enum):
    """Статус позиции"""
    OPEN = "open"
    PARTIALLY_CLOSED = "partially_closed"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"


class Portfolio(Base):
    """
    Основной портфель пользователя
    """
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Portfolio metadata
    name = Column(String, default="Default Portfolio", nullable=False)
    description = Column(String, nullable=True)
    
    # Financial metrics
    total_value = Column(Float, default=0.0)  # текущая стоимость
    cash_balance = Column(Float, default=0.0)  # наличные средства
    invested_value = Column(Float, default=0.0)  # выручка в активах
    
    # Performance metrics
    total_gain_loss = Column(Float, default=0.0)  # общий P&L
    total_gain_loss_percent = Column(Float, default=0.0)  # проценты
    today_gain_loss = Column(Float, default=0.0)  # прибыль сегодня
    today_gain_loss_percent = Column(Float, default=0.0)
    
    # Risk metrics
    total_risk_exposure = Column(Float, default=0.0)  # общая риск экспозиция
    max_drawdown = Column(Float, default=0.0)  # максимум сад (нижаю)
    correlation_factor = Column(Float, default=0.0)  # корреляция активов
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    positions = relationship("Position", back_populates="portfolio")
    cash_balances = relationship("CashBalance", back_populates="portfolio")
    
    class Config:
        from_attributes = True


class Position(Base):
    """
    Открытая позиция по торговой паре
    """
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    exchange_config_id = Column(Integer, ForeignKey("exchange_configs.id"), nullable=False, index=True)
    
    # Position identification
    symbol = Column(String, index=True, nullable=False)  # BTC/USDT
    position_type = Column(String, nullable=False)  # PositionType
    status = Column(String, default="open", nullable=False, index=True)  # PositionStatus
    
    # Position sizing
    quantity = Column(Float, nullable=False)  # количество
    entry_price = Column(Float, nullable=False)  # цена входа
    current_price = Column(Float, nullable=False)  # текущая цена
    
    # Cost and value
    entry_cost = Column(Float, nullable=False)  # стоимость входа
    current_value = Column(Float, nullable=False)  # текущая стоимость
    unrealized_pnl = Column(Float, default=0.0)  # нереализованные P&L
    unrealized_pnl_percent = Column(Float, default=0.0)
    
    # Commission and fees
    commission_paid = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)  # реализованные P&L
    
    # Risk management
    stop_loss_price = Column(Float, nullable=True)  # стоп-лосс
    take_profit_price = Column(Float, nullable=True)  # тек профит
    leverage = Column(Float, default=1.0)  # леверидж
    
    # Metadata
    opened_at = Column(DateTime, default=datetime.utcnow, index=True)
    closed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")
    
    __table_args__ = (
        Index('ix_portfolio_symbol_status', 'portfolio_id', 'symbol', 'status'),
    )
    
    class Config:
        from_attributes = True


class CashBalance(Base):
    """
    Кассовые средства в портфеле
    """
    __tablename__ = "cash_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Currency information
    currency = Column(String, index=True, nullable=False)  # USDT, USD, EUR
    balance = Column(Float, default=0.0)  # количество
    
    # Reserved for open orders
    reserved = Column(Float, default=0.0)  # зарезервировано
    available = Column(Float, default=0.0)  # доступно
    
    # Exchange rate (for multi-currency portfolios)
    exchange_rate = Column(Float, default=1.0)  # к принципальной валюте
    
    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="cash_balances")
    
    __table_args__ = (
        Index('ix_portfolio_currency', 'portfolio_id', 'currency'),
    )
    
    class Config:
        from_attributes = True
