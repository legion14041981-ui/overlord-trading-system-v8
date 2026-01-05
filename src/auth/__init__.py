"""
Authentication and security module.

Exports:
- grail_agent: главный агент безопасности
- token_validator: валидация токенов
- permissions: управление разрешениями
"""

from .grail_agent import GrailAgent, get_grail_agent
from .token_validator import TokenValidator
from .permissions import PermissionManager

__all__ = [
    "GrailAgent",
    "get_grail_agent",
    "TokenValidator",
    "PermissionManager",
]

__version__ = "1.0.0"
