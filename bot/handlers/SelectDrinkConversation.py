from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto,
    Update, ReplyKeyboardRemove
)
from telegram.ext import (
    ConversationHandler, CallbackQueryHandler, CommandHandler,
    MessageHandler, filters, ContextTypes
)
from sqlalchemy.orm import selectinload
from utils.logging_config import log_function_call, LogExecutionTime, get_logger
from db.db_async import get_async_session
from db.models import Drink, DrinkType, DrinkSize, DrinkAdd, Order, OrderAdd, Add, Session
from sqlalchemy import select
from datetime import datetime
from utils.keyboard_builder import get_drink_sizes_keyboard, build_order_keyboard

# Состояния
(
    DRINK_TYPES_SELECTION,
    SELECT_SIZE,
    SELECT_ADDS,
    CUSTOMER_COMMENT,
    CONFIRM_ORDER
) = range(5)

logger = get_logger(__name__)

ORDER_STATUS_CREATED = 1
ORDER_STATUS_PAYED = 2
ORDER_STATUS_PROCESSING = 3
ORDER_STATUS_READY = 4
ORDER_STATUS_RECEIVED = 5
ORDER_STATUS_DECLINED = 6
ORDER_STATUS_EXPIRED = 7
ORDER_STATUS_DRAFT = 8

@log_function_call(action="Start_order_session")
async def start_select_drink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Старт сценария выбора напитков — показать все активные типы.
    Поддержка как команды /new_order, так и кнопки CallbackQuery.
    """
    # Определяем объект для ответа
    if update.callback_query:
        await update.callback_query.answer()  # закрываем "часики"
        msg_target = update.callback_query.message
    else:
        msg_target = update.message
    #удаляет предыдущий вариант показа карточек выбранного типа, если гость нажал на Вернуться.
    chat_id = update.effective_chat.id
    msg_ids = context.user_data.get("drink_messages", [])
    print(f"DEBUG_delete_MESSAGE_list: {msg_ids}")
    if msg_ids:
        for msg_id in msg_ids:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                print(f"Не удалось удалить сообщение {msg_id}: {e}")
    context.user_data["drink_messages"] = []
        # удаляем сообщение с текстом "Отличный выбор! ..."
    last_menu_msg_id = context.user_data.get("last_menu_message_id")
    print(f"DEBUG_delete_GREETINGS: {last_menu_msg_id}")
    if last_menu_msg_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=last_menu_msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {last_menu_msg_id}: {e}")
        context.user_data["last_menu_message_id"] = None
    # Получаем все активные типы напитков
    async with get_async_session() as session:
        result = await session.execute(
            select(DrinkType)
        )
        types = result.scalars().all()

    if not types:
        await msg_target.reply_text("❌ В данный момент нет доступных категорий напитков.")
        return ConversationHandler.END

    # Формируем клавиатуру
    keyboard = [[InlineKeyboardButton(t.name, callback_data=f"drink_type_{t.id}")] for t in types]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение
    await msg_target.reply_text(
        "Что будете пить сегодня? Выберите категорию:",
        reply_markup=reply_markup
    )

    return DRINK_TYPES_SELECTION

@log_function_call(action="Drink_type_selection")
async def handle_drinktype_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    type_id = int(query.data.split("_")[-1])
    context.user_data["drink_type_id"] = type_id

    async with get_async_session() as session:
        result = await session.execute(
            select(DrinkType).where(DrinkType.id == type_id)
        )
        drink_type = result.scalar_one_or_none()

    type_name = drink_type.name if drink_type else "Неизвестная категория"

    edited_msg = await query.edit_message_text(
        f"Отличный выбор! Сейчас покажу все напитки в категории <b>{type_name}</b>",
        parse_mode="HTML"
    )
    context.user_data["last_menu_message_id"] = edited_msg.message_id

    return await show_filtered_drinks(update, context)

@log_function_call(action="show_filtered_drinks")
async def show_filtered_drinks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    type_id = context.user_data.get("drink_type_id")

    async with get_async_session() as session:
        result = await session.execute(
            select(Drink)
            .where(Drink.type_id == type_id, Drink.is_active == True, Drink.is_draft == False)
        )
        drinks = result.scalars().all()

    if not drinks:
        await update.effective_message.reply_text("❌ В этой категории пока нет напитков.")
        return ConversationHandler.END

    context.user_data["drink_messages"] = []  # сбрасываем перед показом

    for drink in drinks:
        # Получаем размеры и клавиатуру
        sizes, keyboard_markup, image_file_id = await get_drink_sizes_keyboard(drink.id)

        caption = f"<b>{drink.name}</b>\n{drink.description or 'Без описания'}"

        if image_file_id:
            sent = await update.effective_message.reply_photo(
                photo=image_file_id,
                caption=caption,
                reply_markup=keyboard_markup,
                parse_mode="HTML"
            )
        else:
            sent = await update.effective_message.reply_text(
                caption,
                reply_markup=keyboard_markup,
                parse_mode="HTML"
            )
            # сохраняем id отправленного сообщения
        context.user_data["drink_messages"].append(sent.message_id)
    return SELECT_SIZE

@log_function_call(action="size_selection")
async def handle_size_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data if query else None
    print(f"DEBUG_размер_имеем_{data}")
        # Парсим индекс из callback_data
    if data:
        try:
            drink_size_id = int(data.split("_")[-1])
        except (ValueError, IndexError):
            await query.message.reply_text("Ошибка выбора размера. Попробуйте снова.")
            return DRINK_TYPES_SELECTION

        context.user_data["selected_size_id"] = drink_size_id
        tg_user_id = update.effective_user.id

        async with get_async_session() as session:
            session_id = context.user_data.get("session_id")

            if not session_id:
                # создаём новую сессию
                new_session = Session(tg_user_id=tg_user_id, role_id = 1,last_action={"event": "order_started"})
                session.add(new_session)
                await session.flush()  # получаем id новой сессии
                session_id = new_session.id
                context.user_data["session_id"] = session_id  # кладём обратно в контекст
                # получаем размер напитка вместе с его Drink и Size
            result = await session.execute(
                select(DrinkSize)
                .options(
                    selectinload(DrinkSize.drink).selectinload(Drink.drink_adds).selectinload(DrinkAdd.add),  # грузим добавки сразу
                    selectinload(DrinkSize.sizes)
                )
                .where(DrinkSize.id == drink_size_id)
            )
            drink_size = result.scalar_one()

            # создаём заказ (draft)
            order = Order(
                tg_user_id=tg_user_id,
                drink_size_id=drink_size.id,
                status_id= ORDER_STATUS_DRAFT,
                drink_count=1,
                total_price=drink_size.price,
                session_id = session_id if session_id else 1
            )
            session.add(order)
            await session.flush()  # чтобы получить order.id

            adds = [drink_add.add for drink_add in drink_size.drink.drink_adds]

            selected_adds = []
            keyboard = await build_order_keyboard(order, adds, selected_adds, order.total_price)

            caption = f"<b>{drink_size.drink.name}</b>\n" \
                    f"☕🍦☕🐈☕🍦☕🐈☕🍦☕🐈☕🍦\n" \
                    f"{drink_size.sizes.name} ({drink_size.sizes.volume_ml} мл) – {int(drink_size.price)}₽\n" \
                    f"Количество: 1\n" \
                    f"Добавки: не выбрано"

            msg = await update.callback_query.message.reply_text(
                caption, reply_markup=keyboard, parse_mode="HTML"
            )
            # сохраняем id сообщения в сессию
            session_obj = await session.get(Session, session_id)
            if session_obj:
                session_obj.last_action = {
                    "event": "order_message",
                    "message_id": msg.message_id
                }

            await session.commit()

        chat_id = update.effective_chat.id

        for msg_id in context.user_data.get("drink_messages", []):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                print(f"Не удалось удалить сообщение {msg_id}: {e}")
        # очищаем список
        context.user_data["drink_messages"] = []

        last_menu_msg_id = context.user_data.get("last_menu_message_id")
        if last_menu_msg_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=last_menu_msg_id)
            except Exception as e:
                print(f"Не удалось удалить сообщение {last_menu_msg_id}: {e}")
        # очищаем список
        context.user_data["last_menu_message_id"] = None
        return SELECT_ADDS


@log_function_call(action="update_quantity")
async def handle_update_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    print(f"DEBUG_quantity_data: {query.data.split("_")}")
    try:
        _,_, action, order_id_str = query.data.split("_")
        order_id = int(order_id_str)
    except ValueError:
        await query.message.reply_text("Ошибка при изменении количества.")
        return SELECT_ADDS

    async with get_async_session() as session:
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.drink_size)
                    .selectinload(DrinkSize.drink)
                    .selectinload(Drink.drink_adds)
                    .selectinload(DrinkAdd.add),  # добавки сразу грузим
                selectinload(Order.order_adds).selectinload(OrderAdd.add),  # выбранные пользователем добавки
                selectinload(Order.drink_size).selectinload(DrinkSize.sizes),
                selectinload(Order.session)
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            await query.message.edit_text("Заказ не найден. Начните сначала.")
            return ConversationHandler.END


        # изменение, не допускать меньше 1
        if action == "+":
            order.drink_count += 1
        elif action == "-" and order.drink_count > 1:
            order.drink_count -= 1
        else:
            # если попытка уменьшить ниже 1 — просто игнорируем
            logger.debug("Attempt to decrease below 1 ignored for order %s", order_id)

        # пересчёт цены: напиток + добавки
        current_adds = [oa.add for oa in order.order_adds]
        order.total_price = order.drink_size.price * order.drink_count + sum(a.price for a in current_adds)

        await session.flush()

        # пересобираем клавиатуру
        adds = [oa.add for oa in order.order_adds]  # выбранные добавки
        available_adds = [da.add for da in order.drink_size.drink.drink_adds]
        selected_adds = [oa.add_id for oa in order.order_adds]
        keyboard = await build_order_keyboard(order, available_adds, selected_adds, order.total_price)

        caption = f"<b>{order.drink_size.drink.name}</b>\n" \
                  f"☕🍦☕🐈☕🍦☕🐈☕🍦☕🐈☕🍦\n" \
                  f"{order.drink_size.sizes.name} ({order.drink_size.sizes.volume_ml} мл) – {int(order.drink_size.price)}₽\n" \
                  f"Количество: {order.drink_count}\n" \
                  f"Добавки: {', '.join([a.name for a in adds]) if adds else 'не выбрано'}"

        await query.message.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
        
        session_obj = await session.get(Session, order.session_id)
        if session_obj:
            session_obj.last_action = {
                "event": "update_quantity",
                "message_id": query.message.message_id
            }
        await session.commit()
    return SELECT_ADDS

@log_function_call(action="toggle_add")
async def handle_toggle_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    print(f"DEBUG_toggle_add_data: {query.data.split("_")}")
    try:
        _,_, add_id_str, order_id_str = query.data.split("_")
        order_id = int(order_id_str)
        add_id = int(add_id_str)
    except ValueError:
        await query.message.reply_text("Ошибка выбора добавки.")
        return SELECT_ADDS

    async with get_async_session() as session:
    # получаем заказ и связанные объекты
        result = await session.execute(
            select(Order)
            .options(
                selectinload(Order.order_adds).selectinload(OrderAdd.add),
                selectinload(Order.drink_size).selectinload(DrinkSize.drink).selectinload(Drink.drink_adds).selectinload(DrinkAdd.add),
                selectinload(Order.drink_size).selectinload(DrinkSize.sizes),
                selectinload(Order.session)
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            await query.message.edit_text("Заказ не найден. Начните сначала.")
            return ConversationHandler.END

        # переключаем добавку
        existing = next((oa for oa in order.order_adds if oa.add_id == add_id), None)
        if existing:
            await session.delete(existing)
        else:
            order_add = OrderAdd(order_id=order.id, add_id=add_id)
            session.add(order_add)

        await session.flush()
        await session.refresh(order)  # гарантируем актуальность order.order_adds

        # пересчёт цены
        current_adds = [oa.add for oa in order.order_adds]
        order.total_price = order.drink_size.price * order.drink_count + sum(a.price for a in current_adds)

        await session.flush()

        selected_adds = [oa.add_id for oa in order.order_adds]
        available_adds = [da.add for da in order.drink_size.drink.drink_adds]
        keyboard = await build_order_keyboard(order, available_adds, selected_adds, order.total_price)

        caption = f"☕ <b>{order.drink_size.drink.name}</b>\n" \
                    f"☕🍦☕🐈☕🍦☕🐈☕🍦☕🐈☕🍦\n" \
                  f"{order.drink_size.sizes.name} ({order.drink_size.sizes.volume_ml} мл) – {int(order.drink_size.price)}₽\n" \
                  f"Количество: {order.drink_count}\n" \
                  f"Добавки: {', '.join([oa.add.name for oa in order.order_adds]) if order.order_adds else 'не выбрано'}"

        await query.message.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
        session_obj = await session.get(Session, order.session_id)
        if session_obj:
            session_obj.last_action = {
                "event": "update_toggle_adds",
                "message_id": query.message.message_id
            }
        await session.commit()
    return SELECT_ADDS



# === Отмена ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена поиска"""
    context.user_data.clear()
    await update.message.reply_text("❌ Выбор отменён",reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END
