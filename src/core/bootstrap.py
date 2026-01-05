"""
OVERLORD Bootstrap Module
Инициализация главной системы Overlord Trading System v8
"""

import logging
import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class OverlordBootstrap:
    """Главный класс инициализации системы Overlord."""
    
    VERSION = "8.0.0"
    
    def __init__(self, config_path: str = None, mode: str = "standard"):
        """
        Инициализация Overlord.
        
        Args:
            config_path: путь к YAML файлу конфигурации
            mode: режим работы (dry-run, conservative, standard, aggressive)
        """
        self.config_path = config_path or os.getenv(
            'OVERLORD_CONFIG',
            'config/default.yaml'
        )
        self.mode = mode
        self.config = self._load_config()
        self.state = {'initialized': False, 'mode': mode}
        self.modules = {}
        self.startup_time = None
        
        logger.info(f"Overlord v{self.VERSION} initializing in {mode} mode...")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузить конфигурацию из YAML файла."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Config loaded from {self.config_path}")
                return config
            else:
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                return self._default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Конфигурация по умолчанию."""
        return {
            'overlord': {
                'version': self.VERSION,
                'mode': self.mode,
                'environment': 'development'
            },
            'trading': {
                'enabled': True,
                'max_positions': 10,
                'risk_limit': 0.02,
                'engine': 'binance'
            },
            'api': {
                'host': '0.0.0.0',
                'port': 8000,
                'workers': 4
            },
            'auth': {
                'token_ttl': 3600,
                'require_mfa': False
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
    
    def initialize_modules(self) -> bool:
        """Инициализировать все основные модули."""
        try:
            logger.info("Initializing Overlord modules...")
            
            # Инициализация Grail Agent
            try:
                from ..auth.grail_agent import get_grail_agent
                self.modules['grail'] = get_grail_agent()
                logger.info("✅ Grail Agent initialized")
            except Exception as e:
                logger.warning(f"⚠️ Grail Agent initialization failed: {e}")
            
            # Инициализация State Machine
            try:
                from . import state_machine
                self.modules['state'] = state_machine.StateMachine()
                logger.info("✅ State Machine initialized")
            except Exception as e:
                logger.warning(f"⚠️ State Machine initialization failed: {e}")
            
            # Инициализация Trading Engine
            try:
                from . import engine
                self.modules['engine'] = engine.TradingEngine(self.config)
                logger.info("✅ Trading Engine initialized")
            except Exception as e:
                logger.warning(f"⚠️ Trading Engine initialization failed: {e}")
            
            self.state['initialized'] = True
            logger.info(f"All modules initialized successfully ({len(self.modules)} loaded)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize modules: {e}", exc_info=True)
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Проверить здоровье системы."""
        health = {
            'version': self.VERSION,
            'mode': self.mode,
            'config_loaded': bool(self.config),
            'modules_initialized': len(self.modules) > 0,
            'modules': {},
            'status': 'unknown'
        }
        
        # Проверка каждого модуля
        for name, module in self.modules.items():
            try:
                if hasattr(module, 'get_health_status'):
                    health['modules'][name] = module.get_health_status()
                elif hasattr(module, 'is_ready'):
                    health['modules'][name] = {'ready': module.is_ready()}
                else:
                    health['modules'][name] = {'loaded': True}
            except Exception as e:
                health['modules'][name] = {'error': str(e)}
        
        # Общий статус
        if len(self.modules) > 0 and self.state['initialized']:
            health['status'] = 'healthy'
        elif len(self.modules) > 0:
            health['status'] = 'degraded'
        else:
            health['status'] = 'unhealthy'
        
        return health
    
    def start(self) -> bool:
        """Запустить систему."""
        try:
            from datetime import datetime
            self.startup_time = datetime.now()
            
            logger.info("="*60)
            logger.info(f"OVERLORD Trading System v{self.VERSION}")
            logger.info(f"Mode: {self.mode}")
            logger.info(f"Startup: {self.startup_time.isoformat()}")
            logger.info("="*60)
            
            if not self.initialize_modules():
                logger.error("Module initialization failed")
                return False
            
            health = self.health_check()
            logger.info(f"System Status: {health['status']}")
            logger.info(f"Modules Loaded: {len(self.modules)}")
            
            return health['status'] in ['healthy', 'degraded']
            
        except Exception as e:
            logger.error(f"Failed to start Overlord: {e}", exc_info=True)
            return False
    
    def stop(self) -> bool:
        """Остановить систему."""
        try:
            logger.info("Shutting down Overlord...")
            
            for name, module in self.modules.items():
                try:
                    if hasattr(module, 'shutdown'):
                        module.shutdown()
                        logger.info(f"✅ {name} shut down")
                except Exception as e:
                    logger.error(f"❌ Failed to shutdown {name}: {e}")
            
            self.state['initialized'] = False
            logger.info("Overlord shut down complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Overlord: {e}", exc_info=True)
            return False


def create_overlord(
    config_path: str = None,
    mode: str = "standard"
) -> OverlordBootstrap:
    """
    Factory функция для создания Overlord.
    
    Args:
        config_path: путь к конфигурации
        mode: режим работы
    
    Returns:
        OverlordBootstrap instance
    """
    return OverlordBootstrap(config_path, mode)


if __name__ == '__main__':
    # Локальное тестирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    overlord = create_overlord(mode="dry-run")
    
    if overlord.start():
        print("\n" + "="*60)
        print("HEALTH CHECK REPORT")
        print("="*60)
        health = overlord.health_check()
        import json
        print(json.dumps(health, indent=2, ensure_ascii=False))
        print("="*60)
        
        overlord.stop()
    else:
        print("❌ Failed to start Overlord")
        sys.exit(1)
