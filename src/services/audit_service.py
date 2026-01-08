"""Audit logging service for compliance and tracking."""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum
from decimal import Decimal

from src.core.structured_logger import get_logger

logger = get_logger(__name__)


class AuditEventType(str, Enum):
    """Types of auditable events."""
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    RISK_LIMIT_BREACHED = "risk_limit_breached"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    CONFIG_CHANGED = "config_changed"
    EMERGENCY_STOP = "emergency_stop"
    API_KEY_USED = "api_key_used"
    WITHDRAWAL = "withdrawal"


class AuditService:
    """Service for auditing system events and actions."""

    def __init__(self, enable_persistent_storage: bool = False):
        """Initialize audit service.
        
        Args:
            enable_persistent_storage: Whether to persist audit logs to database
        """
        self.enable_persistent_storage = enable_persistent_storage
        self._lock = asyncio.Lock()
        self._audit_buffer: list = []
        self._max_buffer_size = 1000

    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an auditable event.
        
        Args:
            event_type: Type of event
            user_id: ID of user who triggered event
            details: Event-specific details
            metadata: Additional metadata
        """
        async with self._lock:
            try:
                audit_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "event_type": event_type.value,
                    "user_id": user_id,
                    "details": self._sanitize_details(details or {}),
                    "metadata": metadata or {},
                }
                
                logger.info(
                    f"Audit event: {event_type.value}",
                    extra=audit_entry
                )
                
                # Add to buffer
                self._audit_buffer.append(audit_entry)
                
                # Flush buffer if needed
                if len(self._audit_buffer) >= self._max_buffer_size:
                    await self._flush_buffer()
                    
            except Exception as e:
                logger.error(
                    f"Failed to log audit event: {event_type.value}",
                    extra={"error": str(e)}
                )

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive information from audit details.
        
        Args:
            details: Raw details dictionary
            
        Returns:
            Sanitized details
        """
        sanitized = {}
        sensitive_keys = {"api_key", "secret", "password", "private_key"}
        
        for key, value in details.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, Decimal):
                sanitized[key] = str(value)
            elif isinstance(value, datetime):
                sanitized[key] = value.isoformat()
            else:
                sanitized[key] = value
        
        return sanitized

    async def _flush_buffer(self) -> None:
        """Flush audit buffer to persistent storage."""
        if not self.enable_persistent_storage:
            self._audit_buffer.clear()
            return
        
        try:
            # Implementation for persisting to database would go here
            logger.info(f"Flushing {len(self._audit_buffer)} audit entries")
            self._audit_buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush audit buffer: {e}")

    async def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[AuditEventType] = None,
    ) -> list:
        """Get recent audit events.
        
        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type
            
        Returns:
            List of audit events
        """
        async with self._lock:
            events = self._audit_buffer.copy()
            
            if event_type:
                events = [
                    e for e in events
                    if e["event_type"] == event_type.value
                ]
            
            return events[-limit:]
