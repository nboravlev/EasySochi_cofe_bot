from sqlalchemy import select, update, desc
from sqlalchemy.orm import joinedload

from datetime import datetime

from db.db_async import get_async_session

from db.models.users import User
from db.models.sessions import Session
from db.models.drinks import Drink
from db.models.orders import Order
from db.models.images import Image
from db.models.order_statuses import OrderStatus
from db.models.drink_sizes import  DrinkSize

EXCEPT_STATUSES = [6,7,8]

async def get_user_by_tg_id(tg_user_id: int):
    """Get user by Telegram ID"""
    async with get_async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_user_id == tg_user_id)
        )
        return result.scalars().first()


async def create_user(tg_user, first_name=None, phone_number=None):
    """Create new user in database"""
    async with get_async_session() as session:
        user = User(
            tg_user_id=tg_user.id,
            username=tg_user.username,
            firstname=first_name,
            phone_number=phone_number,
            is_bot=tg_user.is_bot,
            created_at=datetime.utcnow()
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def create_session(tg_user_id: int, role_id: int):
    """Create new session with role"""
    async with get_async_session() as session:
        new_session = Session(
            tg_user_id=tg_user_id,
            role_id=role_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)
        return new_session

async def get_last_order(tg_user_id: int) -> dict | None:
    """
    Получает последний активный заказ пользователя с расшифровкой напитка и размера.

    :param tg_user_id: Telegram ID пользователя
    :return: dict с полями заказа или None
    """
    async with get_async_session() as session:
        result = await session.execute(
            select(Order)
            .options(
                joinedload(Order.drink_size)
                .joinedload(DrinkSize.drink),   # связь с Drink
                joinedload(Order.drink_size)
                .joinedload(DrinkSize.sizes),   # связь с Size
                joinedload(Order.drink_size)
                .joinedload(DrinkSize.drink)
                .joinedload(Drink.images)

            )
            .where(
                Order.tg_user_id == tg_user_id,
                Order.is_active == True,
                ~Order.status_id.in_(EXCEPT_STATUSES)  # фильтр на исключаемые статусы
            )
            .order_by(desc(Order.created_at))
            .limit(1)
        )
        order = result.scalars().first()

        if not order:
            return None

        drink = order.drink_size.drink
        size = order.drink_size.sizes
        media = None
        if drink.images:
            media = drink.images[0].tg_file_id

        return {
            "id": order.id,
            "drink_size_id": order.drink_size_id,
            "created_at": order.created_at,
            "drink_name": drink.name if drink else "Неизвестно",
            "size": f"{size.name} ({size.volume_ml} мл)" if size else "Неизвестный размер",
            "drink_count": order.drink_count,
            "total_price": float(order.total_price),
            "status_id": order.status_id,
            "image_file_id": media
        }