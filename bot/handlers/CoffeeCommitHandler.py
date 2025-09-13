from db.db_async import get_async_session
from db.models.drinks import Drink
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler
from sqlalchemy import select
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
    )
from utils.logging_config import log_function_call, get_logger

logger = get_logger(__name__)

@log_function_call(action="Coffee_commit_done")
async def confirm_coffee_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message

    # DEBUG
    logger.debug(
        f"[CONFIRM DEBUG] message_id={message.message_id}, "
        f"text={repr(message.text)}, caption={repr(message.caption)}, "
        f"has_photo={bool(message.photo)}, "
        f"reply_markup={bool(message.reply_markup)}"
    )

    try:
        drink_id = int(query.data.split("_")[-1])
        logger.info(f"Пользователь {query.from_user.id} подтверждает карточку напитка ID={drink_id}")

        async with get_async_session() as session:
            result = await session.execute(select(Drink).where(Drink.id == drink_id))
            drink = result.scalar_one_or_none()

            if not drink:
                await query.answer("Объект не найден.")
                logger.warning(f"Попытка подтвердить несуществующий напиток ID={drink_id}")
                return ConversationHandler.END

            drink.is_draft = False
            await session.commit()

        confirmation_text = "🏆 Карточка напитка сохранена. Желаю хороших продаж!"

        keyboard = [[
        InlineKeyboardButton("✍🏻 Создать ещё карточку", callback_data="create_card"),
        InlineKeyboardButton("🚪 Выйти", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправка / редактирование сообщения
        if message.text:
            logger.debug("[CONFIRM DEBUG] Редактируем текстовое сообщение")
            await query.edit_message_text(confirmation_text, reply_markup=reply_markup)
        elif message.caption:
            logger.debug("[CONFIRM DEBUG] Редактируем подпись к фото")
            await query.edit_message_caption(caption=confirmation_text, reply_markup=reply_markup)
        else:
            logger.debug("[CONFIRM DEBUG] Нет текста и подписи — отправляем новое сообщение")
            await message.reply_text(confirmation_text, reply_markup=reply_markup)

        logger.info(f"Карточка напитка ID={drink_id} успешно подтверждена")

    except Exception as exc:
        logger.exception(f"Ошибка при подтверждении карточки: {exc}")
        await message.reply_text("❌ Ошибка при подтверждении карточки. Попробуйте ещё раз.")

    return ConversationHandler.END

confirm_coffee_handler = CallbackQueryHandler(
    confirm_coffee_callback,
    pattern=r"^confirm_coffee_\d+$"
)
