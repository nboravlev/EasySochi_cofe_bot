import os
import re
from datetime import timedelta
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update
)
from telegram.ext import (
    ConversationHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from sqlalchemy import select, update as sa_update
from sqlalchemy.orm import joinedload, selectinload
from db.db_async import get_async_session
from db.models import Order, Drink, DrinkSize, DrinkAdd, User, OrderAdd
from utils.logging_config import log_function_call, LogExecutionTime, get_logger

logger = get_logger(__name__)

ORDER_STATUS_RECEIVED = 5

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not (ADMIN_CHAT_ID):
    raise RuntimeError("Admin chat id did not set in environment variables")



# Клиент нажал "Заказ получен"
@log_function_call(action="OrderReceived")
async def order_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, _, order_id_str = query.data.split("_")
        order_id = int(order_id_str)
    except ValueError:
        await query.message.reply_text("❌ Ошибка в callback data")
        return ConversationHandler.END

    async with get_async_session() as session:
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.user),       # клиент
                selectinload(Order.manager),    # менеджер
                selectinload(Order.session)     # для last_action
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            await query.message.edit_text("❌ Заказ не найден.")
            return ConversationHandler.END

        # обновляем статус
        order.status_id = ORDER_STATUS_RECEIVED
        await session.flush()

        # редактируем сообщение клиента (убираем кнопку)
        await query.message.edit_text("🙏 Спасибо! Заказ получен.")

        # уведомляем менеджеров через session.last_action
        session_obj = order.session
        if session_obj and session_obj.last_action:
            manager_msg_id = session_obj.last_action.get("message_id")
            if manager_msg_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=ADMIN_CHAT_ID,
                        message_id=manager_msg_id,
                        text=f"🎉 Заказ №{order.id} получен клиентом ✅"
                    )
                except Exception as e:
                    logger.warning("Не удалось отредактировать сообщение менеджера: %s", e)

        await session.commit()

    return ConversationHandler.END
