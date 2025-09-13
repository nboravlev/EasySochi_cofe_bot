from db.db_async import get_async_session
from db.models import Drink, DrinkSize, DrinkAdd
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from sqlalchemy import update as sa_update
from telegram import Update
from utils.logging_config import log_function_call, get_logger

logger = get_logger(__name__)

@log_function_call(action="redo_coffee")
async def redo_coffee_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message

    try:
        drink_id = int(query.data.split("_")[-1])
        logger.info(f"Пользователь {query.from_user.id} инициировал пересоздание напитка ID={drink_id}")

        async with get_async_session() as session:
            # Сбрасываем флаги напитка
            await session.execute(
                sa_update(Drink)
                .where(Drink.id == drink_id)
                .values(is_draft=True, is_active=False)
            )
            # Сбрасываем размеры
            await session.execute(
                sa_update(DrinkSize)
                .where(DrinkSize.drink_id == drink_id)
                .values(is_active=False)
            )
            # Сбрасываем добавки
            await session.execute(
                sa_update(DrinkAdd)
                .where(DrinkAdd.drink_id == drink_id)
                .values(is_active=False)
            )
            await session.commit()

        # Определяем тип сообщения (текст или фото)
        if message.text:
            await query.edit_message_text(
                "🚫 Данные удалены. Начните сначала /create_card"
            )
        elif message.caption:
            await query.edit_message_caption(
                caption="🚫 Данные удалены. Начните сначала /create_card"
            )
        else:
            # Фолбэк — если нет текста и подписи
            await message.reply_text(
                "🚫 Данные удалены. Начните сначала /create_card"
            )

        logger.info(f"Напиток ID={drink_id} успешно помечен для пересоздания")

    except Exception as exc:
        logger.exception(f"Ошибка при пересоздании напитка: {exc}")
        await message.reply_text(
            "❌ Произошла ошибка при удалении данных. Попробуйте ещё раз."
        )

    return ConversationHandler.END


redo_coffee_handler = CallbackQueryHandler(
    redo_coffee_callback,
    pattern=r"^redo_coffee_\d+$"
)
