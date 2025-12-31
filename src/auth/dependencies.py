"""FastAPI authentication dependencies."""
from fastapi import Depends, HTTPException, status

from .jwt_handler import get_current_user
from ..models.user import User


async def require_auth(current_user: User = Depends(get_current_user)) -> User:
    """Требует аутентификации пользователя."""
    return current_user


async def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Требует права суперпользователя."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user
