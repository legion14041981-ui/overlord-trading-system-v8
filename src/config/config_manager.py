"""Configuration management for Overlord Trading System v9."""
import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import ValidationError

from ..core.models.config_schema import OverlordConfig
from ..core.logging.structured_logger import get_logger


logger = get_logger(__name__)


class ConfigManager:
    """Manages system configuration loading and validation."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/overlord.yaml")
        self._config: Optional[OverlordConfig] = None
    
    def load(self) -> OverlordConfig:
        """Load and validate configuration from file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Interpolate environment variables
            raw_config = self._interpolate_env_vars(raw_config)
            
            # Validate with Pydantic
            self._config = OverlordConfig(**raw_config)
            
            logger.info("Configuration loaded successfully", {
                "config_path": str(self.config_path),
                "mode": self._config.system.mode.value,
                "environment": self._config.system.environment,
                "data_sources": len(self._config.data_sources),
                "strategies": len(self._config.strategies)
            })
            
            return self._config
        
        except ValidationError as e:
            logger.error("Configuration validation failed", error=e)
            raise
        except Exception as e:
            logger.error("Failed to load configuration", error=e)
            raise
    
    def _interpolate_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Replace ${VAR_NAME} with environment variable values."""
        if isinstance(config, dict):
            return {
                key: self._interpolate_env_vars(value)
                for key, value in config.items()
            }
        elif isinstance(config, list):
            return [self._interpolate_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            env_var = config[2:-1]
            value = os.getenv(env_var)
            if value is None:
                logger.warning(f"Environment variable not found: {env_var}")
                return config
            return value
        else:
            return config
    
    def get_config(self) -> OverlordConfig:
        """Get current configuration (load if not loaded)."""
        if self._config is None:
            return self.load()
        return self._config
    
    def reload(self) -> OverlordConfig:
        """Reload configuration from file."""
        logger.info("Reloading configuration")
        return self.load()
    
    def validate_runtime(self) -> bool:
        """Validate configuration against runtime requirements."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded")
        
        checks = []
        
        # Check data sources have credentials
        for ds in self._config.data_sources:
            if ds.enabled and not (ds.api_key and ds.api_secret):
                checks.append(f"Data source '{ds.name}' missing credentials")
        
        # Check strategy allocations
        total_allocation = sum(
            s.capital_allocation for s in self._config.strategies if s.enabled
        )
        if total_allocation > 1:
            checks.append(f"Total capital allocation exceeds 100%: {total_allocation}")
        
        # Check risk limits are reasonable
        for strategy in self._config.strategies:
            if strategy.enabled:
                if strategy.risk_limits.max_drawdown > 0.5:
                    checks.append(
                        f"Strategy '{strategy.name}' has high max_drawdown: "
                        f"{strategy.risk_limits.max_drawdown}"
                    )
        
        if checks:
            logger.warning("Configuration validation warnings", {"checks": checks})
            return False
        
        logger.info("Configuration runtime validation passed")
        return True
    
    def export_template(self, output_path: Path):
        """Export a configuration template."""
        template = {
            "system": {
                "mode": "conservative",
                "environment": "production",
                "log_level": "INFO",
                "max_concurrent_orders": 100,
                "heartbeat_interval": 5
            },
            "data_sources": [
                {
                    "name": "example_exchange",
                    "enabled": True,
                    "venue_type": "spot",
                    "api_key": "${API_KEY}",
                    "api_secret": "${API_SECRET}",
                    "symbols": ["BTC/USDT", "ETH/USDT"]
                }
            ],
            "strategies": [
                {
                    "name": "example_strategy",
                    "strategy_type": "momentum",
                    "enabled": True,
                    "capital_allocation": 0.5,
                    "symbols": ["BTC/USDT"],
                    "venues": ["example_exchange"],
                    "risk_limits": {
                        "max_drawdown": 0.15,
                        "max_position_size": 0.1
                    }
                }
            ],
            "execution": {
                "mode": "smart_routing",
                "slippage_tolerance": 0.001,
                "timeout": 30
            }
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration template exported to {output_path}")
