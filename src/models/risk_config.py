# src/models/risk_config.py
"""
Risk Management Configuration Models
Модели для управления рисками и лимитами
"""

from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.database import Base


class RiskLevel(str, Enum):
    """Уровень риска"""
    CONSERVATIVE = "conservative"  # консервативный
    MODERATE = "moderate"  # умеренный
    AGGRESSIVE = "aggressive"  # агрессивный
    EXTREME = "extreme"  # экстримальный


class RiskManagementConfig(Base):
    """
    Глобальная конфигурация для управления риском
    """
    __tablename__ = "risk_management_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, unique=True, index=True)
    
    # Risk level
    risk_level = Column(String, default="moderate", nullable=False)  # RiskLevel
    
    # Portfolio-wide limits
    max_portfolio_loss_percent = Column(Float, default=0.05)  # 5% макс. потери
    max_position_size_percent = Column(Float, default=0.10)  # 10% макс. позиция
    max_positions_count = Column(Integer, default=10)  # макс. кол-во позиций
    
    # Correlation and concentration limits
    max_correlation_factor = Column(Float, default=0.80)  # макс. корреляция
    max_sector_exposure_percent = Column(Float, default=0.30)  # 30% макс. для сектора
    
    # Leverage limits
    max_leverage = Column(Float, default=1.0)  # макс. леверидж
    allow_margin_trading = Column(Boolean, default=False)  # маржин
    allow_short_selling = Column(Boolean, default=False)  # скороселлинг
    
    # Daily trading limits
    max_daily_trades = Column(Integer, default=50)  # макс. торгов
    max_daily_loss_percent = Column(Float, default=0.02)  # 2% макс. дневных потерь
    stop_trading_on_max_loss = Column(Boolean, default=True)  # остановка
    
    # Time-based limits
    max_position_hold_time_hours = Column(Integer, default=720)  # 30 дней
    min_time_between_trades_seconds = Column(Integer, default=0)  # мин. время
    
    # Alert thresholds
    alert_on_position_loss_percent = Column(Float, default=0.05)  # 5% алерт
    alert_on_portfolio_loss_percent = Column(Float, default=0.03)  # 3% алерт
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class Config:
        from_attributes = True


class ExposureLimit(Base):
    """
    Лимит экспозиции для сектора или актива
    """
    __tablename__ = "exposure_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Exposure target
    target_type = Column(String, nullable=False)  # sector, asset_class, strategy
    target_name = Column(String, index=True, nullable=False)  # название
    
    # Limits
    max_exposure_percent = Column(Float, nullable=False)  # макс. доля
    min_exposure_percent = Column(Float, default=0.0)  # мин. доля
    
    # Alert thresholds
    alert_level_percent = Column(Float, nullable=True)  # уровень алерта
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_portfolio_target', 'portfolio_id', 'target_type', 'target_name'),
    )
    
    class Config:
        from_attributes = True


class StopLossConfig(Base):
    """
    Конфигурация стоп-лосса
    """
    __tablename__ = "stop_loss_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Stop loss type
    stop_loss_type = Column(String, nullable=False)  # fixed, trailing, time_based
    
    # Fixed stop loss
    fixed_sl_percent = Column(Float, nullable=True)  # 5% допустимые потери
    
    # Trailing stop loss
    trailing_sl_percent = Column(Float, nullable=True)  # трейлинг-стоп
    trailing_activation_percent = Column(Float, nullable=True)  # активация
    
    # Time-based stop loss
    time_based_sl_hours = Column(Integer, nullable=True)  # кол-во часов
    
    # Execution
    execution_type = Column(String, default="market", nullable=False)  # market, limit
    limit_price_offset_percent = Column(Float, nullable=True)  # отступ для limit
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class Config:
        from_attributes = True


class TakeProfitConfig(Base):
    """
    Конфигурация тек профита
    """
    __tablename__ = "take_profit_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Take profit target
    target_profit_percent = Column(Float, nullable=False)  # таргет
    
    # Partial take profit
    use_partial_tp = Column(Boolean, default=False)  # ступенчатый
    tp_levels = Column(JSON, nullable=True)  # [{"percent": 50, "price_percent": 5}, ...]
    
    # Execution
    execution_type = Column(String, default="market", nullable=False)  # market, limit
    limit_price_offset_percent = Column(Float, nullable=True)  # отступ
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class Config:
        from_attributes = True
