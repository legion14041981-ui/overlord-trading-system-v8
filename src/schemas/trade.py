from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class TradeBase(BaseModel):
    """Базовая схема сделки"""
    symbol: str = Field(..., min_length=1, max_length=20, description="Торговый символ (BTC/USDT)")
    side: str = Field(..., description="Направление сделки (buy/sell)")
    quantity: Decimal = Field(..., gt=0, description="Объем сделки")
    price: Decimal = Field(..., gt=0, description="Цена сделки")
    status: str = Field(default="pending", description="Статус сделки (pending/executed/cancelled)")


class TradeCreate(TradeBase):
    """Схема создания сделки"""
    strategy_id: int = Field(..., description="ID стратегии")


class TradeUpdate(BaseModel):
    """Схема обновления сделки"""
    symbol: Optional[str] = Field(None, min_length=1, max_length=20, description="Торговый символ")
    side: Optional[str] = Field(None, description="Направление сделки")
    quantity: Optional[Decimal] = Field(None, gt=0, description="Объем сделки")
    price: Optional[Decimal] = Field(None, gt=0, description="Цена сделки")
    status: Optional[str] = Field(None, description="Статус сделки")
    executed_at: Optional[datetime] = Field(None, description="Время выполнения")


class TradeResponse(TradeBase):
    """Схема ответа сделки"""
    id: int = Field(..., description="ID сделки")
    strategy_id: int = Field(..., description="ID стратегии")
    executed_at: Optional[datetime] = Field(None, description="Время выполнения")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")

    class Config:
        from_attributes = True
