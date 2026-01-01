"""
Alert Service for Overlord v8.1

Handles alert creation, management, triggering, and notifications.
Integrates with:
- Alert rules engine
- Notification system (email, SMS, webhooks)
- Event publishing (Redis/WebSocket)
- User preferences
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import json

from src.database.models import (
    AlertRule, AlertLog, AlertTemplate, AlertPreference,
    NotificationLog, AlertStatistics,
    AlertTypeEnum, AlertStatusEnum, AlertSeverityEnum, AlertChannelEnum,
    User
)

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing trading alerts"""
    
    def __init__(self, db_session: Session):
        """Initialize alert service
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    # ==================== Alert Rule Management ====================
    
    async def create_alert_rule(
        self,
        user_id: int,
        name: str,
        alert_type: AlertTypeEnum,
        condition: Dict,
        severity: AlertSeverityEnum = AlertSeverityEnum.WARNING,
        **kwargs
    ) -> AlertRule:
        """Create a new alert rule
        
        Args:
            user_id: User ID
            name: Alert rule name
            alert_type: Type of alert
            condition: Alert condition as dictionary
                Example: {"symbol": "BTC/USDT", "field": "price", "operator": ">", "value": 50000}
            severity: Alert severity level
            **kwargs: Additional fields (secondary_condition, enabled_channels, etc.)
            
        Returns:
            Created AlertRule
        """
        rule = AlertRule(
            user_id=user_id,
            name=name,
            alert_type=alert_type,
            condition=condition,
            severity=severity,
            **kwargs
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        logger.info(f"Created alert rule '{name}' for user {user_id}")
        return rule
    
    async def update_alert_rule(
        self,
        rule_id: int,
        **updates
    ) -> AlertRule:
        """Update an alert rule
        
        Args:
            rule_id: Alert rule ID
            **updates: Fields to update
            
        Returns:
            Updated AlertRule
        """
        rule = self.db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            raise ValueError(f"Alert rule {rule_id} not found")
        
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        self.db.commit()
        self.db.refresh(rule)
        return rule
    
    async def delete_alert_rule(
        self,
        rule_id: int
    ) -> None:
        """Delete an alert rule
        
        Args:
            rule_id: Alert rule ID
        """
        rule = self.db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if rule:
            self.db.delete(rule)
            self.db.commit()
            logger.info(f"Deleted alert rule {rule_id}")
    
    async def get_user_alert_rules(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[AlertRule]:
        """Get all alert rules for a user
        
        Args:
            user_id: User ID
            active_only: Only return active rules
            
        Returns:
            List of AlertRule objects
        """
        query = self.db.query(AlertRule).filter(AlertRule.user_id == user_id)
        if active_only:
            query = query.filter(AlertRule.is_active == True)
        return query.all()
    
    async def get_active_rules_by_type(
        self,
        alert_type: AlertTypeEnum
    ) -> List[AlertRule]:
        """Get all active rules of a specific type
        
        Args:
            alert_type: Type of alert to filter by
            
        Returns:
            List of AlertRule objects
        """
        return self.db.query(AlertRule).filter(
            and_(
                AlertRule.alert_type == alert_type,
                AlertRule.is_active == True
            )
        ).all()
    
    # ==================== Alert Triggering ====================
    
    async def trigger_alert(
        self,
        rule_id: int,
        triggered_value: float,
        trigger_context: Optional[Dict] = None
    ) -> AlertLog:
        """Trigger an alert rule
        
        Args:
            rule_id: Alert rule ID
            triggered_value: The value that triggered the alert
            trigger_context: Additional context about the trigger
            
        Returns:
            Created AlertLog
        """
        rule = self.db.query(AlertRule).filter(AlertRule.id == rule_id).first()
        if not rule:
            raise ValueError(f"Alert rule {rule_id} not found")
        
        # Check if rule is in cooldown
        if rule.last_triggered_at:
            cooldown_end = rule.last_triggered_at + timedelta(seconds=rule.cooldown_seconds)
            if datetime.utcnow() < cooldown_end:
                logger.debug(f"Alert rule {rule_id} is in cooldown")
                return None
        
        # Check daily limit
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = self.db.query(AlertLog).filter(
            and_(
                AlertLog.rule_id == rule_id,
                AlertLog.triggered_at >= today_start
            )
        ).count()
        
        if rule.max_alerts_per_day and today_count >= rule.max_alerts_per_day:
            logger.warning(f"Alert rule {rule_id} daily limit reached")
            return None
        
        # Create alert log
        alert_log = AlertLog(
            rule_id=rule_id,
            triggered_at=datetime.utcnow(),
            triggered_value=triggered_value,
            trigger_context=trigger_context or {}
        )
        self.db.add(alert_log)
        
        # Update rule metadata
        rule.last_triggered_at = datetime.utcnow()
        rule.triggered_count += 1
        
        self.db.commit()
        self.db.refresh(alert_log)
        
        logger.info(
            f"Triggered alert rule {rule_id} (type: {rule.alert_type.value}, "
            f"severity: {rule.severity.value})"
        )
        
        return alert_log
    
    async def check_and_trigger_alerts(
        self,
        alert_type: AlertTypeEnum,
        trigger_data: Dict
    ) -> List[AlertLog]:
        """Check and trigger all rules of a type that match conditions
        
        Args:
            alert_type: Type of alert to check
            trigger_data: Data to match against conditions
                Example: {"symbol": "BTC/USDT", "price": 50100, "volume": 1000000}
                
        Returns:
            List of triggered AlertLog objects
        """
        rules = await self.get_active_rules_by_type(alert_type)
        triggered_logs = []
        
        for rule in rules:
            # Simple condition matching logic
            if self._match_condition(rule.condition, trigger_data):
                # Additional secondary condition check if exists
                if rule.secondary_condition:
                    if not self._match_condition(rule.secondary_condition, trigger_data):
                        continue
                
                # Check time window
                if not self._is_in_time_window(rule):
                    continue
                
                alert_log = await self.trigger_alert(
                    rule_id=rule.id,
                    triggered_value=trigger_data.get(rule.condition.get("field"), 0),
                    trigger_context=trigger_data
                )
                if alert_log:
                    triggered_logs.append(alert_log)
        
        return triggered_logs
    
    def _match_condition(self, condition: Dict, data: Dict) -> bool:
        """Check if condition matches data
        
        Args:
            condition: Condition dictionary
            data: Data to check
            
        Returns:
            True if condition matches
        """
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if field not in data:
            return False
        
        field_value = data[field]
        
        if operator == ">":
            return field_value > value
        elif operator == "<":
            return field_value < value
        elif operator == ">=":
            return field_value >= value
        elif operator == "<=":
            return field_value <= value
        elif operator == "==":
            return field_value == value
        elif operator == "!=":
            return field_value != value
        
        return False
    
    def _is_in_time_window(self, rule: AlertRule) -> bool:
        """Check if current time is within rule's time window
        
        Args:
            rule: Alert rule
            
        Returns:
            True if within window (or no window specified)
        """
        if not rule.time_window_start or not rule.time_window_end:
            return True
        
        current_time = datetime.utcnow().strftime("%H:%M")
        start = rule.time_window_start
        end = rule.time_window_end
        
        if start < end:
            # Normal case: e.g., 09:00 to 17:00
            return start <= current_time <= end
        else:
            # Overnight case: e.g., 22:00 to 07:00
            return current_time >= start or current_time <= end
    
    # ==================== Alert Log Management ====================
    
    async def acknowledge_alert(
        self,
        alert_log_id: int,
        user_id: int,
        message: Optional[str] = None
    ) -> AlertLog:
        """Acknowledge an alert
        
        Args:
            alert_log_id: Alert log ID
            user_id: User ID of acknowledger
            message: Acknowledgment message
            
        Returns:
            Updated AlertLog
        """
        alert = self.db.query(AlertLog).filter(AlertLog.id == alert_log_id).first()
        if not alert:
            raise ValueError(f"Alert log {alert_log_id} not found")
        
        alert.status = AlertStatusEnum.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user_id
        alert.acknowledgment_message = message
        
        self.db.commit()
        self.db.refresh(alert)
        
        logger.info(f"Alert {alert_log_id} acknowledged by user {user_id}")
        return alert
    
    async def resolve_alert(
        self,
        alert_log_id: int,
        resolution_notes: Optional[str] = None
    ) -> AlertLog:
        """Resolve an alert
        
        Args:
            alert_log_id: Alert log ID
            resolution_notes: Notes about resolution
            
        Returns:
            Updated AlertLog
        """
        alert = self.db.query(AlertLog).filter(AlertLog.id == alert_log_id).first()
        if not alert:
            raise ValueError(f"Alert log {alert_log_id} not found")
        
        alert.status = AlertStatusEnum.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolution_notes = resolution_notes
        
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    async def get_alert_history(
        self,
        user_id: int,
        limit: int = 100,
        status_filter: Optional[AlertStatusEnum] = None,
        days: int = 30
    ) -> List[AlertLog]:
        """Get alert history for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of alerts
            status_filter: Filter by status
            days: Number of days to look back
            
        Returns:
            List of AlertLog objects
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(AlertLog).join(AlertRule).filter(
            and_(
                AlertRule.user_id == user_id,
                AlertLog.triggered_at >= cutoff_date
            )
        )
        
        if status_filter:
            query = query.filter(AlertLog.status == status_filter)
        
        return query.order_by(desc(AlertLog.triggered_at)).limit(limit).all()
    
    # ==================== Alert Templates ====================
    
    async def create_alert_template(
        self,
        created_by_user: int,
        name: str,
        alert_type: AlertTypeEnum,
        condition_template: Dict,
        **kwargs
    ) -> AlertTemplate:
        """Create an alert template
        
        Args:
            created_by_user: User ID of creator
            name: Template name
            alert_type: Alert type
            condition_template: Template with placeholders (e.g., "{symbol}", "{threshold}")
            **kwargs: Additional fields
            
        Returns:
            Created AlertTemplate
        """
        template = AlertTemplate(
            created_by_user=created_by_user,
            name=name,
            alert_type=alert_type,
            condition_template=condition_template,
            **kwargs
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template
    
    async def get_alert_templates(
        self,
        alert_type: Optional[AlertTypeEnum] = None,
        official_only: bool = False
    ) -> List[AlertTemplate]:
        """Get alert templates
        
        Args:
            alert_type: Filter by alert type
            official_only: Only official Overlord templates
            
        Returns:
            List of AlertTemplate objects
        """
        query = self.db.query(AlertTemplate)
        
        if alert_type:
            query = query.filter(AlertTemplate.alert_type == alert_type)
        
        if official_only:
            query = query.filter(AlertTemplate.is_official == True)
        
        return query.order_by(desc(AlertTemplate.usage_count)).all()
    
    # ==================== Alert Preferences ====================
    
    async def get_or_create_preferences(
        self,
        user_id: int
    ) -> AlertPreference:
        """Get or create alert preferences for user
        
        Args:
            user_id: User ID
            
        Returns:
            AlertPreference
        """
        prefs = self.db.query(AlertPreference).filter(
            AlertPreference.user_id == user_id
        ).first()
        
        if not prefs:
            prefs = AlertPreference(user_id=user_id)
            self.db.add(prefs)
            self.db.commit()
            self.db.refresh(prefs)
        
        return prefs
    
    async def update_preferences(
        self,
        user_id: int,
        **updates
    ) -> AlertPreference:
        """Update alert preferences
        
        Args:
            user_id: User ID
            **updates: Fields to update
            
        Returns:
            Updated AlertPreference
        """
        prefs = await self.get_or_create_preferences(user_id)
        
        for key, value in updates.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        
        self.db.commit()
        self.db.refresh(prefs)
        return prefs
    
    # ==================== Alert Statistics ====================
    
    async def record_notification(
        self,
        alert_log_id: int,
        user_id: int,
        channel: AlertChannelEnum,
        recipient: str,
        message: str,
        status: str = "pending"
    ) -> NotificationLog:
        """Record a notification
        
        Args:
            alert_log_id: Alert log ID
            user_id: User ID
            channel: Notification channel
            recipient: Recipient (email, phone, etc.)
            message: Notification message
            status: Notification status (pending, sent, failed)
            
        Returns:
            Created NotificationLog
        """
        log = NotificationLog(
            alert_log_id=alert_log_id,
            user_id=user_id,
            channel=channel,
            recipient=recipient,
            message=message,
            status=status
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
    
    async def update_notification_status(
        self,
        notification_log_id: int,
        status: str,
        delivery_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> NotificationLog:
        """Update notification delivery status
        
        Args:
            notification_log_id: Notification log ID
            status: New status (sent, failed, bounced)
            delivery_time_ms: Time to deliver in milliseconds
            error_message: Error message if failed
            
        Returns:
            Updated NotificationLog
        """
        log = self.db.query(NotificationLog).filter(
            NotificationLog.id == notification_log_id
        ).first()
        
        if log:
            log.status = status
            if status == "sent":
                log.sent_at = datetime.utcnow()
            log.delivery_time_ms = delivery_time_ms
            log.error_message = error_message
            self.db.commit()
            self.db.refresh(log)
        
        return log
    
    async def get_user_stats(
        self,
        user_id: int,
        period_days: int = 7
    ) -> Dict:
        """Get alert statistics for a user
        
        Args:
            user_id: User ID
            period_days: Number of days to analyze
            
        Returns:
            Dictionary with alert statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Count various alert statuses
        alerts = self.db.query(AlertLog).join(AlertRule).filter(
            and_(
                AlertRule.user_id == user_id,
                AlertLog.triggered_at >= cutoff_date
            )
        ).all()
        
        stats = {
            "total_alerts": len(alerts),
            "triggered": sum(1 for a in alerts if a.status == AlertStatusEnum.TRIGGERED),
            "acknowledged": sum(1 for a in alerts if a.status == AlertStatusEnum.ACKNOWLEDGED),
            "resolved": sum(1 for a in alerts if a.status == AlertStatusEnum.RESOLVED),
            "avg_response_time": self._calculate_avg_response_time(alerts),
        }
        
        return stats
    
    def _calculate_avg_response_time(self, alerts: List[AlertLog]) -> Optional[float]:
        """Calculate average response time to alerts
        
        Args:
            alerts: List of AlertLog objects
            
        Returns:
            Average response time in seconds
        """
        acknowledged = [a for a in alerts if a.acknowledged_at]
        if not acknowledged:
            return None
        
        total_time = sum(
            (a.acknowledged_at - a.triggered_at).total_seconds()
            for a in acknowledged
        )
        return total_time / len(acknowledged)
