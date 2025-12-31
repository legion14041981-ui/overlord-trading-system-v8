from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..database import get_db
from ..schemas.strategy import StrategyCreate, StrategyUpdate, StrategyResponse
from ..models.strategy import Strategy

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создание новой стратегии"""
    db_strategy = Strategy(**strategy_data.model_dump())
    db.add(db_strategy)
    await db.commit()
    await db.refresh(db_strategy)
    return db_strategy


@router.get("/", response_model=List[StrategyResponse])
async def get_strategies(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получение списка стратегий"""
    from sqlalchemy import select
    result = await db.execute(select(Strategy).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получение стратегии по ID"""
    from sqlalchemy import select
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    strategy_data: StrategyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновление стратегии"""
    from sqlalchemy import select
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    for field, value in strategy_data.model_dump(exclude_unset=True).items():
        setattr(strategy, field, value)
    
    await db.commit()
    await db.refresh(strategy)
    return strategy


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удаление стратегии"""
    from sqlalchemy import select, delete
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    await db.execute(delete(Strategy).where(Strategy.id == strategy_id))
    await db.commit()
