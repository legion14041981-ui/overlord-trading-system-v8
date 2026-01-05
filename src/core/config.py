"""
OVERLORD Configuration Manager
Управление конфигурацией системы
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class ConfigManager:
    """Менеджер конфигурации."""
    
    def __init__(self, config_path: str = None, environment: str = None):
        """
        Инициализация менеджера.
        
        Args:
            config_path: путь к YAML файлу
            environment: development, production, test
        """
        self.environment = environment or os.getenv('OVERLORD_ENV', 'development')
        self.config_path = config_path or self._resolve_config_path()
        self.config = self.load_config()
        
        logger.info(f"Config Manager initialized: {self.environment}")
        logger.info(f"Config file: {self.config_path}")
    
    def _resolve_config_path(self) -> str:
        """Определить путь к конфигурации."""
        env_paths = {
            'development': 'config/default.yaml',
            'production': 'config/production.yaml',
            'test': 'config/test.yaml'
        }
        return env_paths.get(self.environment, 'config/default.yaml')
    
    def load_config(self) -> Dict[str, Any]:
        """Загрузить конфигурацию."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                logger.info(f"✅ Config loaded from {self.config_path}")
                return config
            else:
                logger.warning(f"⚠️ Config file not found: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию."""
        return {
            'overlord': {
                'version': '8.0.0',
                'mode': 'standard',
                'environment': self.environment
            },
            'api': {
                'host': '0.0.0.0',
                'port': 8000
            },
            'trading': {
                'enabled': False
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение по ключу."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def reload(self) -> bool:
        """Перезагрузить конфигурацию."""
        try:
            self.config = self.load_config()
            logger.info("✅ Config reloaded")
            return True
        except Exception as e:
            logger.error(f"Failed to reload config: {e}", exc_info=True)
            return False
