from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StrategyBase(BaseModel):
    """Базовая схема торговой стратегии"""
    name: str = Field(..., min_length=3, max_length=100, description="Название стратегии")
    description: Optional[str] = Field(None, max_length=500, description="Описание стратегии")
    parameters: dict = Field(default_factory=dict, description="Параметры стратегии (JSON)")
    is_active: bool = Field(default=True, description="Активна ли стратегия")


class StrategyCreate(StrategyBase):
    """Схема создания стратегии"""
    user_id: int = Field(..., description="ID пользователя-владельца")


class StrategyUpdate(BaseModel):
    """Схема обновления стратегии"""
    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Название стратегии")
    description: Optional[str] = Field(None, max_length=500, description="Описание стратегии")
    parameters: Optional[dict] = Field(None, description="Параметры стратегии (JSON)")
    is_active: Optional[bool] = Field(None, description="Активна ли стратегия")


class StrategyResponse(StrategyBase):
    """Схема ответа стратегии"""
    id: int = Field(..., description="ID стратегии")
    user_id: int = Field(..., description="ID пользователя-владельца")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")

    class Config:
        from_attributes = True
