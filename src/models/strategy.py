"""Strategy model for trading strategies."""
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class Strategy(Base):
    """Strategy model representing trading strategies.
    
    Attributes:
        id: Primary key
        name: Strategy name
        description: Detailed description
        parameters: JSONB field for flexible strategy parameters
        is_active: Whether the strategy is currently active
        created_by: Foreign key to User who created this strategy
        created_at: Timestamp of strategy creation
        updated_at: Timestamp of last update
        creator: Relationship to User model
        trades: Relationship to Trade model
    """
    
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    parameters = Column(JSONB, nullable=True, default=dict)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name={self.name}, is_active={self.is_active})>"
    
    def to_dict(self) -> dict:
        """Convert strategy to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
