"""
Core module — сердце Overlord Trading System.

Exports:
- bootstrap: главный инициализатор системы
- state_machine: управление состояниями
- engine: торговый движок
- config: менеджер конфигураций
"""

from .bootstrap import OverlordBootstrap, create_overlord
from .state_machine import StateMachine
from .engine import TradingEngine
from .config import ConfigManager

__all__ = [
    "OverlordBootstrap",
    "create_overlord",
    "StateMachine",
    "TradingEngine",
    "ConfigManager",
]

__version__ = "8.0.0"
