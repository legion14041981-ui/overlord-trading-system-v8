"""Trade model for tracking trading operations."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Trade(Base):
    """Trade model representing individual trades.
    
    Attributes:
        id: Primary key
        strategy_id: Foreign key to Strategy
        symbol: Trading symbol/ticker (e.g., BTC/USD)
        side: Trade side (BUY or SELL)
        quantity: Trade quantity
        price: Execution price
        status: Trade status (PENDING, EXECUTED, CANCELLED)
        executed_at: Timestamp when trade was executed
        created_at: Timestamp of trade creation
        strategy: Relationship to Strategy model
    """
    
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Numeric(precision=18, scale=8), nullable=False)
    price = Column(Numeric(precision=18, scale=8), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)  # PENDING, EXECUTED, CANCELLED
    executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    strategy = relationship("Strategy", back_populates="trades")
    
    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side}, status={self.status})>"
    
    def to_dict(self) -> dict:
        """Convert trade to dictionary."""
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity) if self.quantity else None,
            "price": str(self.price) if self.price else None,
            "status": self.status,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def total_value(self) -> Decimal:
        """Calculate total trade value."""
        return self.quantity * self.price if self.quantity and self.price else Decimal("0")
