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
from db.models import Order, Drink, DrinkSize, DrinkAdd, User, OrderAdd,Session
from utils.logging_config import log_function_call, LogExecutionTime, get_logger

ORDER_STATUS_PROCESSING = 3
ORDER_STATUS_READY = 4
ORDER_STATUS_RECEIVED = 5

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not (ADMIN_CHAT_ID):
    raise RuntimeError("Admin chat id did not set in environment variables")

# Состояния
ORDER_READY = 1

logger = get_logger(__name__)

@log_function_call(action="TakeOrder")
async def take_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Менеджер берёт заказ в работу через кнопку времени"""
    query = update.callback_query
    await query.answer()

    try:
        _, order_id_str, processing_time_str = query.data.split("_")
        order_id = int(order_id_str)
        processing_time = "Более 10" if processing_time_str == "10plus" else int(processing_time_str)
    except (ValueError, IndexError):
        await query.message.reply_text("Ошибка при обработке данных заказа.")
        return ConversationHandler.END


    async with get_async_session() as session:
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.drink_size)
                    .selectinload(DrinkSize.drink)
                    .selectinload(Drink.drink_type),
                selectinload(Order.drink_size).selectinload(DrinkSize.sizes),
                selectinload(Order.user)    # клиент
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            await query.message.edit_text("❌ Заказ не найден.")
            return ConversationHandler.END

        # Определяем менеджера из callback.from_user
        tg_manager = query.from_user.id
        manager_result = await session.execute(
            select(User).where(User.tg_user_id == tg_manager)
        )
        manager = manager_result.scalar_one_or_none()

        if not manager:
            await query.message.reply_text("❌ Менеджер не найден в базе.")
            return ConversationHandler.END
        
        # Привязываем заказ к менеджеру
        order.status_id = ORDER_STATUS_PROCESSING
        order.manager_id = manager.tg_user_id
        order.manager_comment = f"Время ожидания вашего заказа - {processing_time} мин."
        await session.flush()


        # уведомляем клиента
        await context.bot.send_message(
            chat_id=order.tg_user_id,
            text=f"⏳ {order.manager_comment}"
        )

        # пересобираем сообщение в чате менеджеров
        manager_text = (
            f"🧡 Заказ #{order.id} в работе\n\n"
            f"🔠 Группа: <i>{order.drink_size.drink.drink_type.name}</i>\n"
            f"☕️: <b>{order.drink_size.drink.name}</b>\n"
            f"📏 Размер: {order.drink_size.sizes.name}\n"
            f"🔢 Количество: {order.drink_count}\n"
            f"💰 Оплачено: {order.total_price} ₽\n"
            f"💬 Комментарий клиента: {order.customer_comment or '—'}\n"
            f"👤 Клиент: {order.user.first_name or order.user.username}\n"
            f"🧑‍💼 Менеджер: {manager.first_name or manager.username}\n"
        )

        # новая клавиатура: только "Готов к выдаче"
        new_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Заказ готов к выдаче", callback_data=f"order_ready_{order.id}")]
        ])

        await query.message.edit_text(
            text=manager_text,
            reply_markup=new_keyboard,
            parse_mode="HTML"
        )
    
        await session.commit()
    return ORDER_READY

# Менеджер нажал "Заказ готов к выдаче"
@log_function_call(action="OrderReady")
async def order_ready_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                selectinload(Order.drink_size)
                    .selectinload(DrinkSize.drink)
                    .selectinload(Drink.drink_type),
                selectinload(Order.drink_size).selectinload(DrinkSize.sizes),
                selectinload(Order.user),     # клиент
                selectinload(Order.manager),  # менеджер
                selectinload(Order.session)
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            await query.message.edit_text("❌ Заказ не найден.")
            return ConversationHandler.END

        # обновляем статус
        order.status_id = ORDER_STATUS_READY
        

        # сообщение клиенту
        drink_name = order.drink_size.drink.name
        size_name = order.drink_size.sizes.name
        client_text = f"✅ Ваш заказ {drink_name} версии {size_name} готов! 🍹"

        client_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Заказ получен", callback_data=f"order_received_{order.id}")]
        ])

        await context.bot.send_message(
            chat_id=order.tg_user_id,
            text=client_text,
            reply_markup=client_keyboard
        )

        # сообщение менеджеру (редактируем предыдущее)
        msg = await query.message.edit_text(
            text=f"✅ Заказ #{order.id} готов к выдаче",
            parse_mode="HTML"
        )
        session_obj = await session.get(Session, order.session_id)
        if session_obj:
                session_obj.last_action = {
                    "event": "Manager notification order out",
                    "message_id": msg.message_id
                }
        await session.commit()
    return ConversationHandler.END
