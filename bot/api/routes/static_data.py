# api/routes/static_data.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_async import get_async_session
from db.models.drink_types import DrinkType
from db.models.adds import Add
from schemas.drink_types import DrinkTypeOut
from schemas.adds import AddsOut
from typing import List
from sqlalchemy import select

router = APIRouter()

@router.get("/drink_types/", response_model=List[DrinkTypeOut])
async def get_drink_types(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(DrinkType))
    return result.scalars().all()

@router.get("/adds/", response_model=List[AddsOut])
async def get_adds(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Add))
    return result.scalars().all()