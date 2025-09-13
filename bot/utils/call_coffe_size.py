# сверху файла
from sqlalchemy import select, func
from db.models.sizes import Size
from db.db_async import get_async_session
from typing import Dict

from utils.logging_config import log_function_call, get_logger

logger = get_logger(__name__)

SIZE_MAP: Dict[str, int] = {}  # ключи — нормализованные строки, например "S","M","L","XL"

async def init_size_map():
    """Заполнить SIZE_MAP всеми размерами из таблицы Size.
       Нормализация: ключ = name.strip().upper()
    """
    global SIZE_MAP
    async with get_async_session() as session:
        result = await session.execute(select(Size))
        sizes = result.scalars().all()
        SIZE_MAP = {s.name.strip().upper(): s.id for s in sizes}
    # лог для отладки
    logger.info("SIZE_MAP initialized: %s", SIZE_MAP)


async def get_size_id_async(size_name: str) -> int:
    """
    Возвращает id размера по названию (например "S" -> 1).
    Стратегии поиска:
      1) Нормализованный кэш (upper + strip)
      2) Точное case-insensitive сравнение в DB
      3) LIKE 'X%' (например 'M' -> 'Medium')
    Если не найден — KeyError.
    """
    norm = (size_name or "").strip().upper()
    if not norm:
        raise KeyError("Empty size_name")

    # 1) Кэш
    if norm in SIZE_MAP:
        return SIZE_MAP[norm]

    # 2) Попробуем найти в БД (case-insensitive exact match)
    async with get_async_session() as session:
        q = select(Size).where(func.upper(Size.name) == norm)
        res = await session.execute(q)
        size = res.scalars().first()
        if size:
            SIZE_MAP[norm] = size.id
            logger.info("get_size_id_async: cached %s -> %s", norm, size.id)
            return size.id

        # 3) Попробуем LIKE (нужно для случаев 'M' -> 'Medium', 'XL' -> 'Extra Large')
        q2 = select(Size).where(func.upper(Size.name).like(f"{norm}%"))
        res2 = await session.execute(q2)
        size2 = res2.scalars().first()
        if size2:
            SIZE_MAP[norm] = size2.id
            logger.info("get_size_id_async (like): cached %s -> %s (%s)", norm, size2.id, size2.name)
            return size2.id

    # не нашли
    raise KeyError(f"Size '{size_name}' not found in Size table (normalized: '{norm}')")