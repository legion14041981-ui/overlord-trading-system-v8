"""
Audit Log Service
Tracks all important system events for compliance and debugging
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    TRADE_EXECUTED = "trade_executed"
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"
    CONFIG_CHANGED = "config_changed"
    RISK_LIMIT_BREACHED = "risk_limit_breached"
    SYSTEM_ERROR = "system_error"
    API_ACCESS = "api_access"


class AuditLogService:
    """Service for logging audit events."""
    
    def __init__(self):
        self.logs: List[Dict] = []  # In production, use database
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        description: str,
        metadata: Optional[Dict] = None,
        severity: str = "info"
    ) -> Dict:
        """Log an audit event.
        
        Args:
            event_type: Type of event
            user_id: User ID (if applicable)
            description: Event description
            metadata: Additional event data
            severity: Event severity (info, warning, error, critical)
        
        Returns:
            Created audit log entry
        """
        entry = {
            "id": f"audit-{len(self.logs) + 1}",
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "description": description,
            "metadata": metadata or {},
            "severity": severity
        }
        
        self.logs.append(entry)
        logger.info(f"Audit log: {event_type.value} - {description}", extra=entry)
        
        return entry
    
    async def log_trade(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        strategy_id: Optional[str] = None
    ) -> Dict:
        """Log a trade execution."""
        return await self.log_event(
            event_type=AuditEventType.TRADE_EXECUTED,
            user_id=user_id,
            description=f"Trade executed: {side} {quantity} {symbol} @ {price}",
            metadata={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "strategy_id": strategy_id
            }
        )
    
    async def log_strategy_action(
        self,
        user_id: str,
        strategy_id: str,
        action: str,
        reason: Optional[str] = None
    ) -> Dict:
        """Log a strategy action (start/stop/pause)."""
        event_type = {
            "start": AuditEventType.STRATEGY_STARTED,
            "stop": AuditEventType.STRATEGY_STOPPED
        }.get(action, AuditEventType.CONFIG_CHANGED)
        
        return await self.log_event(
            event_type=event_type,
            user_id=user_id,
            description=f"Strategy {action}: {strategy_id}",
            metadata={
                "strategy_id": strategy_id,
                "action": action,
                "reason": reason
            }
        )
    
    async def log_risk_breach(
        self,
        user_id: Optional[str],
        breach_type: str,
        details: Dict
    ) -> Dict:
        """Log a risk limit breach."""
        return await self.log_event(
            event_type=AuditEventType.RISK_LIMIT_BREACHED,
            user_id=user_id,
            description=f"Risk limit breached: {breach_type}",
            metadata=details,
            severity="warning"
        )
    
    async def get_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Retrieve audit logs with filters."""
        filtered_logs = self.logs[:]
        
        # Apply filters
        if event_type:
            filtered_logs = [log for log in filtered_logs if log["event_type"] == event_type.value]
        
        if user_id:
            filtered_logs = [log for log in filtered_logs if log["user_id"] == user_id]
        
        # Sort by timestamp descending
        filtered_logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return filtered_logs[:limit]


# Global audit log service instance
_audit_log_service = None


def get_audit_log_service() -> AuditLogService:
    """Get or create global audit log service instance."""
    global _audit_log_service
    if _audit_log_service is None:
        _audit_log_service = AuditLogService()
    return _audit_log_service
