"""
Alert Management Models for Overlord v8.1

Defines SQLAlchemy models for managing trading and system alerts:
- Alert rules and conditions
- Alert execution logs
- Alert templates for reuse
- User alert preferences
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Index, ForeignKey, Enum, UniqueConstraint, Text, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
import json

from src.database.connection import Base


class AlertTypeEnum(str, enum.Enum):
    """Types of alerts"""
    PRICE = "price"
    TECHNICAL = "technical"  # RSI, MACD, Moving Averages
    VOLUME = "volume"
    VOLATILITY = "volatility"
    PORTFOLIO = "portfolio"  # Drawdown, unrealized P&L
    RISK = "risk"  # Risk limit violations
    EXECUTION = "execution"  # Trade execution status
    SYSTEM = "system"  # System health, errors
    NEWS = "news"  # News sentiment
    CUSTOM = "custom"


class AlertSeverityEnum(str, enum.Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    HALT = "halt"  # Requires immediate action (trading halt)


class AlertStatusEnum(str, enum.Enum):
    """Alert status tracking"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    ARCHIVED = "archived"


class AlertChannelEnum(str, enum.Enum):
    """Notification channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    IN_APP = "in_app"
    TELEGRAM = "telegram"


class AlertRule(Base):
    """Alert rule definition and configuration"""
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Alert type and severity
    alert_type = Column(Enum(AlertTypeEnum), nullable=False, index=True)
    severity = Column(Enum(AlertSeverityEnum), default=AlertSeverityEnum.WARNING, index=True)
    
    # Condition configuration
    # Stored as JSON for flexibility: {"symbol": "BTC/USDT", "field": "price", "operator": ">", "value": 50000}
    condition = Column(JSON, nullable=False)
    
    # Optional secondary condition (AND logic)
    secondary_condition = Column(JSON, nullable=True)
    
    # Optional time window (e.g., only alert during trading hours)
    time_window_start = Column(String(5), nullable=True)  # "09:00" format
    time_window_end = Column(String(5), nullable=True)    # "17:00" format
    
    # Throttling to prevent alert spam
    min_interval_seconds = Column(Integer, default=300)  # Minimum interval between alerts
    cooldown_seconds = Column(Integer, default=0)  # Cooldown after trigger
    max_alerts_per_day = Column(Integer, nullable=True)  # Limit daily alerts
    
    # Notification settings
    enabled_channels = Column(JSON, default=[])  # List of AlertChannelEnum values
    notify_webhook_url = Column(String(500), nullable=True)
    custom_message = Column(String(500), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_public = Column(Boolean, default=False)  # Can be shared/templated
    
    # Tracking
    last_triggered_at = Column(DateTime, nullable=True)
    triggered_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    alert_logs = relationship("AlertLog", back_populates="rule", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_alert_rule_user_active', 'user_id', 'is_active'),
        Index('ix_alert_rule_type_severity', 'alert_type', 'severity'),
    )


class AlertLog(Base):
    """Alert execution log - record of every alert trigger"""
    __tablename__ = "alert_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False, index=True)
    
    # Trigger details
    triggered_at = Column(DateTime, nullable=False, index=True)
    triggered_value = Column(Float, nullable=True)  # The actual value that triggered alert
    trigger_context = Column(JSON, nullable=True)  # Additional context about trigger
    
    # Alert status and acknowledgment
    status = Column(Enum(AlertStatusEnum), default=AlertStatusEnum.TRIGGERED, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    acknowledgment_message = Column(String(500), nullable=True)
    
    # Notification status
    notification_sent = Column(Boolean, default=False)
    notification_channels = Column(JSON, default=[])  # Channels used
    notification_errors = Column(JSON, nullable=True)  # Any errors during notification
    
    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(String(500), nullable=True)
    
    # Alert message
    alert_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    rule = relationship("AlertRule", back_populates="alert_logs")
    
    __table_args__ = (
        Index('ix_alert_log_rule_triggered', 'rule_id', 'triggered_at'),
        Index('ix_alert_log_status', 'status', 'triggered_at'),
    )


class AlertTemplate(Base):
    """Reusable alert templates"""
    __tablename__ = "alert_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    created_by_user = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Template metadata
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    
    # Template definition
    alert_type = Column(Enum(AlertTypeEnum), nullable=False)
    severity = Column(Enum(AlertSeverityEnum), default=AlertSeverityEnum.WARNING)
    
    # Condition template (with placeholders)
    condition_template = Column(JSON, nullable=False)  # {"symbol": "{symbol}", "field": "price", ...}
    secondary_condition_template = Column(JSON, nullable=True)
    
    # Default settings
    default_channels = Column(JSON, default=[])  # Default notification channels
    custom_message_template = Column(String(500), nullable=True)
    
    # Rating and popularity
    usage_count = Column(Integer, default=0)
    rating = Column(Float, nullable=True)  # 1-5 stars
    is_official = Column(Boolean, default=False)  # Official Overlord templates
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_alert_template_type', 'alert_type'),
        Index('ix_alert_template_official', 'is_official'),
    )


class AlertPreference(Base):
    """User alert notification preferences"""
    __tablename__ = "alert_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Global alert settings
    alerts_enabled = Column(Boolean, default=True)
    do_not_disturb_enabled = Column(Boolean, default=False)
    do_not_disturb_start = Column(String(5), nullable=True)  # "22:00"
    do_not_disturb_end = Column(String(5), nullable=True)    # "07:00"
    
    # Channel preferences
    preferred_channels = Column(JSON, default=[AlertChannelEnum.IN_APP.value])  # List of channels
    
    # Channel-specific settings
    email_address = Column(String(120), nullable=True)
    phone_number = Column(String(20), nullable=True)  # For SMS alerts
    webhook_url = Column(String(500), nullable=True)  # For webhook notifications
    slack_webhook_url = Column(String(500), nullable=True)
    discord_webhook_url = Column(String(500), nullable=True)
    telegram_chat_id = Column(String(50), nullable=True)
    
    # Severity-based alert settings
    critical_alert_enabled = Column(Boolean, default=True)
    warning_alert_enabled = Column(Boolean, default=True)
    info_alert_enabled = Column(Boolean, default=True)
    
    # Alert grouping
    group_similar_alerts = Column(Boolean, default=True)
    similar_alert_window_seconds = Column(Integer, default=300)  # Group within 5 min
    
    # Daily digest settings
    enable_daily_digest = Column(Boolean, default=False)
    digest_time = Column(String(5), default="09:00")  # "HH:MM" format
    
    # Frequency limits
    max_alerts_per_hour = Column(Integer, nullable=True)
    max_alerts_per_day = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class NotificationLog(Base):
    """Log of all notifications sent"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_log_id = Column(Integer, ForeignKey("alert_logs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Notification details
    channel = Column(Enum(AlertChannelEnum), nullable=False, index=True)
    recipient = Column(String(255), nullable=False)  # Email, phone, webhook URL, etc.
    subject = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    
    # Delivery status
    status = Column(String(20), default="pending")  # pending, sent, failed, bounced
    sent_at = Column(DateTime, nullable=True)
    delivery_time_ms = Column(Integer, nullable=True)  # Milliseconds to deliver
    error_message = Column(String(500), nullable=True)
    
    # Tracking
    read = Column(Boolean, default=False)  # For in-app notifications
    read_at = Column(DateTime, nullable=True)
    clicked = Column(Boolean, default=False)
    clicked_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('ix_notification_log_user', 'user_id', 'created_at'),
        Index('ix_notification_log_channel', 'channel', 'status'),
    )


class AlertStatistics(Base):
    """Alert statistics for analytics and monitoring"""
    __tablename__ = "alert_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Time period
    period_date = Column(DateTime, nullable=False, index=True)  # Start of period (day/week/month)
    period_type = Column(String(10), nullable=False)  # "daily", "weekly", "monthly"
    
    # Alert counts
    total_alerts = Column(Integer, default=0)
    triggered_alerts = Column(Integer, default=0)
    acknowledged_alerts = Column(Integer, default=0)
    resolved_alerts = Column(Integer, default=0)
    
    # By type
    price_alerts = Column(Integer, default=0)
    technical_alerts = Column(Integer, default=0)
    volume_alerts = Column(Integer, default=0)
    risk_alerts = Column(Integer, default=0)
    
    # By severity
    critical_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    
    # Notification stats
    total_notifications = Column(Integer, default=0)
    successful_notifications = Column(Integer, default=0)
    failed_notifications = Column(Integer, default=0)
    
    # Response time
    avg_acknowledgment_time_seconds = Column(Float, nullable=True)
    avg_resolution_time_seconds = Column(Float, nullable=True)
    
    # Channel usage
    email_sent = Column(Integer, default=0)
    sms_sent = Column(Integer, default=0)
    push_sent = Column(Integer, default=0)
    webhook_sent = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('user_id', 'period_date', 'period_type', name='uq_alert_stats'),
        Index('ix_alert_stats_user_date', 'user_id', 'period_date'),
    )
