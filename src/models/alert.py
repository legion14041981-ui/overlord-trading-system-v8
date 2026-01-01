# src/models/alert.py
"""
Alert and Notification Models
Модели для системы уведомлений и алертов
"""

from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Integer, ForeignKey, Index, Text
from sqlalchemy.orm import relationship

from src.database import Base


class AlertType(str, Enum):
    """Тип алерта"""
    PRICE_ALERT = "price_alert"  # приснеждение цены
    VOLUME_ALERT = "volume_alert"  # выброс объема
    POSITION_ALERT = "position_alert"  # алерт по позиции
    RISK_ALERT = "risk_alert"  # алерт риска
    STRATEGY_ALERT = "strategy_alert"  # алерт стратегии
    TECHNICAL_ALERT = "technical_alert"  # технический алерт
    SYSTEM_ALERT = "system_alert"  # системный алерт
    PORTFOLIO_ALERT = "portfolio_alert"  # алерт портфеля


class AlertSeverity(str, Enum):
    """Уровень важности алерта"""
    LOW = "low"  # низкая
    MEDIUM = "medium"  # средняя
    HIGH = "high"  # высокая
    CRITICAL = "critical"  # критичная


class AlertStatus(str, Enum):
    """Статус алерта"""
    TRIGGERED = "triggered"  # вызван
    ACKNOWLEDGED = "acknowledged"  # принят
    RESOLVED = "resolved"  # решён
    DISMISSED = "dismissed"  # отклонен
    ESCALATED = "escalated"  # эскалирован


class AlertChannelType(str, Enum):
    """Канал доставки алерта"""
    IN_APP = "in_app"  # в приложению
    EMAIL = "email"  # электронная почта
    SMS = "sms"  # СМС
    TELEGRAM = "telegram"  # телеграм
    SLACK = "slack"  # Slack
    WEBHOOK = "webhook"  # webhook
    PUSH = "push"  # push уведомление


class AlertRule(Base):
    """
    Правило для генерирования алертов
    """
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Rule identification
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    alert_type = Column(String, nullable=False)  # AlertType
    severity = Column(String, default="medium", nullable=False)  # AlertSeverity
    
    # Trigger condition
    condition_type = Column(String, nullable=False)  # price_above, price_below, volume_spike, etc.
    target_symbol = Column(String, nullable=True)  # может быть null для всех
    
    # Condition parameters (JSON for flexibility)
    condition_params = Column(JSON, nullable=False)  # {"price_threshold": 50000, "operator": ">"}
    
    # Notification channels
    enabled_channels = Column(JSON, default=["in_app"])  # ["in_app", "email", "telegram"]
    
    # Throttling
    throttle_enabled = Column(Boolean, default=True)  # включить ограничение
    throttle_minutes = Column(Integer, default=5)  # не считать алерты чаще чем
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered = Column(DateTime, nullable=True)  # Последнее выполнение
    
    # Relationships
    alerts = relationship("Alert", back_populates="rule")
    
    __table_args__ = (
        Index('ix_portfolio_alert_type', 'portfolio_id', 'alert_type'),
    )
    
    class Config:
        from_attributes = True


class Alert(Base):
    """
    Генерированный алерт
    """
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # Alert identification
    alert_type = Column(String, nullable=False, index=True)  # AlertType
    severity = Column(String, nullable=False)  # AlertSeverity
    status = Column(String, default="triggered", nullable=False, index=True)  # AlertStatus
    
    # Content
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Alert context
    symbol = Column(String, nullable=True, index=True)
    current_value = Column(Float, nullable=True)  # текущее значение
    threshold_value = Column(Float, nullable=True)  # порог
    
    # Additional data
    metadata = Column(JSON, nullable=True)  # дополнительная информация
    
    # Timestamps
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    rule = relationship("AlertRule", back_populates="alerts")
    responses = relationship("AlertResponse", back_populates="alert")
    
    __table_args__ = (
        Index('ix_portfolio_status_triggered', 'portfolio_id', 'status', 'triggered_at'),
    )
    
    class Config:
        from_attributes = True


class AlertResponse(Base):
    """
    Ответ или действие на алерт
    """
    __tablename__ = "alert_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False, index=True)
    
    # Response information
    action_type = Column(String, nullable=False)  # acknowledge, dismiss, escalate, auto_action
    action_description = Column(String, nullable=True)  # ност действия
    
    # Notification delivery
    delivery_channels = Column(JSON, nullable=False)  # ["{channel}", "{status}"]
    delivery_successful = Column(Boolean, default=False)
    delivery_details = Column(JSON, nullable=True)  # детали доставки
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    delivered_at = Column(DateTime, nullable=True)
    
    # Relationships
    alert = relationship("Alert", back_populates="responses")
    
    class Config:
        from_attributes = True


class AlertHistory(Base):
    """
    Остория алертов для аналитики и отчетов
    """
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    
    # History entry
    alert_type = Column(String, nullable=False)  # AlertType
    alert_count = Column(Integer, default=1)  # кол-во алертов типа
    
    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Statistics
    total_triggered = Column(Integer, default=0)
    total_acknowledged = Column(Integer, default=0)
    total_resolved = Column(Integer, default=0)
    
    # Performance
    avg_response_time_seconds = Column(Float, nullable=True)
    
    __table_args__ = (
        Index('ix_portfolio_period', 'portfolio_id', 'period_start', 'period_end'),
    )
    
    class Config:
        from_attributes = True
