"""Structured JSON logging for Overlord Trading System v9."""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class StructuredLogger:
    """JSON structured logger compatible with ELK stack."""
    
    def __init__(self, name: str, level: str = "INFO", 
                 log_file: Optional[Path] = None,
                 include_console: bool = True):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers.clear()
        
        # JSON formatter
        formatter = logging.Formatter(
            fmt='%(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
        
        # Console handler
        if include_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _format_log(self, level: str, message: str, 
                    context: Optional[Dict[str, Any]] = None,
                    error: Optional[Exception] = None) -> str:
        """Format log entry as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
            "logger": self.logger.name
        }
        
        if context:
            log_entry["context"] = context
        
        if error:
            log_entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": None  # Add traceback if needed
            }
        
        return json.dumps(log_entry, default=str)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        self.logger.debug(self._format_log("DEBUG", message, context))
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self.logger.info(self._format_log("INFO", message, context))
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self.logger.warning(self._format_log("WARNING", message, context))
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None,
              error: Optional[Exception] = None):
        """Log error message."""
        self.logger.error(self._format_log("ERROR", message, context, error))
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None,
                 error: Optional[Exception] = None):
        """Log critical message."""
        self.logger.critical(self._format_log("CRITICAL", message, context, error))
    
    # Trading-specific convenience methods
    def log_order(self, action: str, order_id: str, symbol: str, 
                  side: str, quantity: Any, price: Any = None):
        """Log order-related event."""
        context = {
            "action": action,
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": str(quantity),
            "price": str(price) if price else None
        }
        self.info(f"Order {action}", context)
    
    def log_trade(self, trade_id: str, symbol: str, side: str, 
                  quantity: Any, price: Any):
        """Log trade execution."""
        context = {
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side,
            "quantity": str(quantity),
            "price": str(price)
        }
        self.info("Trade executed", context)
    
    def log_position_change(self, symbol: str, action: str, 
                           quantity: Any, pnl: Any = None):
        """Log position change."""
        context = {
            "symbol": symbol,
            "action": action,
            "quantity": str(quantity),
            "pnl": str(pnl) if pnl else None
        }
        self.info(f"Position {action}", context)
    
    def log_risk_alert(self, alert_type: str, severity: str, 
                       details: Dict[str, Any]):
        """Log risk management alert."""
        context = {
            "alert_type": alert_type,
            "severity": severity,
            **details
        }
        
        if severity in ["HIGH", "CRITICAL", "EMERGENCY"]:
            self.error(f"Risk alert: {alert_type}", context)
        else:
            self.warning(f"Risk alert: {alert_type}", context)
    
    def log_strategy_signal(self, strategy_id: str, signal_type: str,
                           symbol: str, confidence: Any):
        """Log strategy signal generation."""
        context = {
            "strategy_id": strategy_id,
            "signal_type": signal_type,
            "symbol": symbol,
            "confidence": str(confidence)
        }
        self.info("Strategy signal", context)


# Global logger factory
def get_logger(name: str, level: str = "INFO", 
               log_file: Optional[Path] = None) -> StructuredLogger:
    """Get or create a structured logger."""
    return StructuredLogger(name, level, log_file)
