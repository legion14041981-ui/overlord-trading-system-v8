"""
Permissions Management
Управление разрешениями
"""

import logging
from enum import Enum
from typing import List, Set, Dict

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Базовые разрешения."""
    # Trading
    TRADE_READ = "trade:read"
    TRADE_WRITE = "trade:write"
    TRADE_EXECUTE = "trade:execute"
    
    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_WRITE = "analytics:write"
    
    # Admin
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_FULL = "admin:full"
    
    # System
    SYSTEM_READ = "system:read"
    SYSTEM_CONTROL = "system:control"


class Role(str, Enum):
    """Роли пользователей."""
    GUEST = "guest"
    TRADER = "trader"
    ANALYST = "analyst"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class PermissionManager:
    """Менеджер разрешений."""
    
    def __init__(self):
        # Карта разрешений для ролей
        self.role_permissions: Dict[Role, Set[Permission]] = {
            Role.GUEST: {
                Permission.TRADE_READ,
                Permission.ANALYTICS_READ
            },
            Role.TRADER: {
                Permission.TRADE_READ,
                Permission.TRADE_WRITE,
                Permission.TRADE_EXECUTE,
                Permission.ANALYTICS_READ
            },
            Role.ANALYST: {
                Permission.TRADE_READ,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_WRITE
            },
            Role.ADMIN: {
                Permission.TRADE_READ,
                Permission.TRADE_WRITE,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_WRITE,
                Permission.ADMIN_READ,
                Permission.ADMIN_WRITE,
                Permission.SYSTEM_READ
            },
            Role.SUPERADMIN: set(Permission)  # все разрешения
        }
        
        logger.info("PermissionManager initialized")
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """
        Проверить, есть ли у роли разрешение.
        
        Args:
            role: роль пользователя
            permission: необходимое разрешение
        
        Returns:
            True если разрешение есть
        """
        return permission in self.role_permissions.get(role, set())
    
    def has_any_permission(self, role: Role, permissions: List[Permission]) -> bool:
        """Проверить, есть ли хотя бы одно разрешение."""
        role_perms = self.role_permissions.get(role, set())
        return any(perm in role_perms for perm in permissions)
    
    def has_all_permissions(self, role: Role, permissions: List[Permission]) -> bool:
        """Проверить, есть ли все разрешения."""
        role_perms = self.role_permissions.get(role, set())
        return all(perm in role_perms for perm in permissions)
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """Получить все разрешения роли."""
        return self.role_permissions.get(role, set())
