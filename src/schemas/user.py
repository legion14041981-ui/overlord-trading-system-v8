from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Базовая схема пользователя"""
    email: EmailStr = Field(..., description="Email пользователя")
    username: str = Field(..., min_length=3, max_length=50, description="Имя пользователя")
    is_active: bool = Field(default=True, description="Активен ли пользователь")
    is_superuser: bool = Field(default=False, description="Является ли суперпользователем")


class UserCreate(UserBase):
    """Схема создания пользователя"""
    password: str = Field(..., min_length=8, description="Пароль пользователя")


class UserUpdate(BaseModel):
    """Схема обновления пользователя"""
    email: Optional[EmailStr] = Field(None, description="Email пользователя")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Имя пользователя")
    password: Optional[str] = Field(None, min_length=8, description="Новый пароль")
    is_active: Optional[bool] = Field(None, description="Активен ли пользователь")
    is_superuser: Optional[bool] = Field(None, description="Является ли суперпользователем")


class UserResponse(UserBase):
    """Схема ответа пользователя"""
    id: int = Field(..., description="ID пользователя")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")

    class Config:
        from_attributes = True
