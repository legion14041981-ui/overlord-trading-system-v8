from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..database import get_db
from ..schemas.trade import TradeCreate, TradeUpdate, TradeResponse
from ..models.trade import Trade

router = APIRouter(prefix="/trades", tags=["trades"])


@router.post("/", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
async def create_trade(
    trade_data: TradeCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание новой сделки"""
    db_trade = Trade(**trade_data.model_dump())
    db.add(db_trade)
    await db.commit()
    await db.refresh(db_trade)
    return db_trade


@router.get("/", response_model=List[TradeResponse])
async def get_trades(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка сделок"""
    from sqlalchemy import select
    result = await db.execute(select(Trade).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение сделки по ID"""
    from sqlalchemy import select
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.patch("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    trade_data: TradeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление сделки"""
    from sqlalchemy import select
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    for field, value in trade_data.model_dump(exclude_unset=True).items():
        setattr(trade, field, value)
    
    await db.commit()
    await db.refresh(trade)
    return trade


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление сделки"""
    from sqlalchemy import select, delete
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    await db.execute(delete(Trade).where(Trade.id == trade_id))
    await db.commit()
