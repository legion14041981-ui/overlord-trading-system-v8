"""Configuration schemas using Pydantic for validation."""
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from .enums import SystemMode, VenueType, StrategyType


class SystemConfig(BaseModel):
    """System-level configuration."""
    mode: SystemMode = SystemMode.CONSERVATIVE
    environment: str = Field(default="production", pattern="^(development|staging|production)$")
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    max_concurrent_orders: int = Field(default=100, ge=1, le=1000)
    heartbeat_interval: int = Field(default=5, ge=1, le=60)  # seconds
    enable_telemetry: bool = True


class DataSourceConfig(BaseModel):
    """Data source (exchange/API) configuration."""
    name: str
    enabled: bool = True
    venue_type: VenueType
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    websocket_url: Optional[str] = None
    max_requests_per_minute: int = Field(default=1200, ge=1)
    timeout: int = Field(default=30, ge=1, le=300)  # seconds
    retry_attempts: int = Field(default=3, ge=0, le=10)
    symbols: List[str] = Field(default_factory=list)
    
    @validator('api_key', 'api_secret')
    def validate_credentials(cls, v, values):
        if values.get('enabled') and not v:
            raise ValueError("API credentials required when data source is enabled")
        return v


class RiskLimitsConfig(BaseModel):
    """Risk management limits."""
    max_drawdown: Decimal = Field(default=Decimal('0.15'), ge=0, le=1)
    max_position_size: Decimal = Field(default=Decimal('0.1'), ge=0, le=1)
    max_leverage: Decimal = Field(default=Decimal('1'), ge=1, le=100)
    var_threshold_95: Decimal = Field(default=Decimal('0.05'), ge=0, le=1)
    liquidity_ratio_min: Decimal = Field(default=Decimal('1.5'), ge=0)
    correlation_threshold: Decimal = Field(default=Decimal('0.9'), ge=-1, le=1)
    daily_loss_limit: Optional[Decimal] = Field(default=None, ge=0)
    position_concentration_limit: Decimal = Field(default=Decimal('0.25'), ge=0, le=1)


class StrategyConfig(BaseModel):
    """Trading strategy configuration."""
    name: str
    strategy_type: StrategyType
    enabled: bool = True
    capital_allocation: Decimal = Field(ge=0, le=1)
    symbols: List[str] = Field(min_items=1)
    venues: List[str] = Field(min_items=1)
    risk_limits: RiskLimitsConfig
    parameters: Dict[str, Any] = Field(default_factory=dict)
    entry_conditions: Dict[str, Any] = Field(default_factory=dict)
    exit_conditions: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('capital_allocation')
    def validate_allocation(cls, v):
        if v <= 0:
            raise ValueError("Capital allocation must be positive")
        return v


class ExecutionConfig(BaseModel):
    """Order execution configuration."""
    mode: str = Field(default="smart_routing", pattern="^(smart_routing|direct|best_execution)$")
    slippage_tolerance: Decimal = Field(default=Decimal('0.001'), ge=0, le=0.1)
    timeout: int = Field(default=30, ge=1, le=300)  # seconds
    enable_partial_fills: bool = True
    min_fill_percentage: Decimal = Field(default=Decimal('0.5'), ge=0, le=1)
    max_order_age: int = Field(default=3600, ge=1)  # seconds
    

class OverlordConfig(BaseModel):
    """Main Overlord Trading System configuration."""
    system: SystemConfig
    data_sources: List[DataSourceConfig]
    strategies: List[StrategyConfig]
    execution: ExecutionConfig
    
    @validator('strategies')
    def validate_strategy_allocation(cls, v):
        total_allocation = sum(s.capital_allocation for s in v if s.enabled)
        if total_allocation > Decimal('1'):
            raise ValueError(f"Total capital allocation ({total_allocation}) exceeds 1.0")
        return v
    
    class Config:
        arbitrary_types_allowed = True
