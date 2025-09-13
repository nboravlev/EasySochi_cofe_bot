from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler
)

from sqlalchemy import update as sa_update, select, desc
from datetime import datetime
from sqlalchemy.orm import selectinload

from db.db_async import get_async_session

from db.models.users import User
from db.models.sessions import Session
from db.models.roles import Role
from db.models.drinks import Drink
from db.models.orders import Order


from utils.user_session_lastorder import get_user_by_tg_id, create_user, create_session, get_last_order
from utils.escape import safe_html

from utils.logging_config import log_function_call, LogExecutionTime, get_logger

from dotenv import load_dotenv
import os

logger = get_logger(__name__)

MANAGER_LIST = [
    int(m.strip(" []")) for m in os.getenv("MANAGER_ID_LIST", "").split(",") if m.strip(" []")
]

MENU_URL = ["/bot/static/images/menu_1.png", "/bot/static/images/menu_2.png"]
WELCOME_PHOTO = "/bot/static/images/pelmeshek_avatar.png"

WELCOME_TEXT = "Рады видеть вас в нашем уютном MEOW_CAFE!"

NAME_REQUEST, MAIN_MENU = range(2)



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Точка входа - проверка существующего пользователя"""
    user_id = update.effective_user.id
    tg_user = update.effective_user

    try:
        user = await get_user_by_tg_id(user_id)

        if user is None:
            return await begin_registration(update, context, tg_user)
        else:
            return await route_after_login(update, context, user)

    except Exception as e:
        logger.error(f"Ошибка в start: {e}", exc_info=True)
        await update.message.reply_text("Ошибка. Попробуйте позже.")
        return ConversationHandler.END


async def begin_registration(update: Update, context: ContextTypes.DEFAULT_TYPE, tg_user):
    """Начало регистрации"""
    context.user_data.update({"tg_user": tg_user})
    with open(WELCOME_PHOTO, "rb") as f:
        await update.message.reply_photo(
            photo=f,
            caption=f"{WELCOME_TEXT}\n\nДавайте познакомимся!"
        )

    keyboard = [[KeyboardButton("Использовать никнейм из ТГ")]]
    await update.message.reply_text(
        "Как вас зовут?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return NAME_REQUEST


async def handle_name_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем имя пользователя"""
    tg_user = context.user_data.get("tg_user")
    name = update.message.text.strip()
    if not name or name.lower() == "использовать никнейм из тг":
        name = tg_user.first_name.strip()

    context.user_data["first_name"] = name

    await update.message.reply_text(f"Приятно познакомиться, {name}!")
    return await handle_registration(update, context)


async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание пользователя в БД"""
    try:
        tg_user = context.user_data.get("tg_user")
        first_name = context.user_data.get("first_name")
        user = await create_user(tg_user, first_name, phone_number=None)

        await update.message.reply_text("✅ Регистрация завершена!", reply_markup=ReplyKeyboardRemove())
        return await route_after_login(update, context, user)

    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при регистрации.")
        return ConversationHandler.END

async def route_after_login(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Роутинг после регистрации или входа с созданием сессии"""
    print(f"DEBUG: user_id = {user.tg_user_id}\n"
          f"MANAGER_LIST = {MANAGER_LIST}")
    try:
        if user.tg_user_id in MANAGER_LIST:
            role_id = 2
        else:
            role_id = 1

        # Создаём сессию
        session = await create_session(user.tg_user_id, role_id)

        # Сохраняем данные сессии
        context.user_data.update({
            "user_id": user.id,
            "tg_user_id": user.tg_user_id,
            "session_id": session.id,
            "role_id": role_id
        })

        if role_id == 2:
            return await show_manager_menu(update, context, user)
        else:
            return await show_customer_menu(update, context, user)

    except Exception as e:
        logger.error(f"Ошибка в route_after_login: {e}", exc_info=True)
        await update.message.reply_text("Ошибка при входе. Попробуйте снова.")
        return ConversationHandler.END


async def show_manager_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    keyboard = [
        [InlineKeyboardButton("✍🏻Создать карточку", callback_data="create_card")],
        [InlineKeyboardButton("🔧 Редактировать карточку", callback_data="edit_card")],
        [InlineKeyboardButton("📨 Новые заказы", callback_data="fresh_orders")],
        [InlineKeyboardButton("🧚🏻‍♀️ Мои заказы", callback_data="my_orders")]
    ]
    await update.message.reply_text(
        f"👋 Привет, {user.firstname}! Вы вошли как менеджер.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return #здесь должен быть переход в логику менеджера


async def show_customer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user):

    last_order = await get_last_order(user.tg_user_id)

    if last_order:
        keyboard = [
            [InlineKeyboardButton("Повторить", callback_data=f"select_size_{last_order['drink_size_id']}"),
             InlineKeyboardButton("Новый заказ", callback_data="new_order")],
            [InlineKeyboardButton("Показать меню", callback_data="show_menu")]
        ]
        caption = (
            f"Ваш предыдущий заказ:\n\n"
            f"• <b>{last_order['drink_name']}</b>\n"
            f"• Версия: {last_order['size']}\n"
            f"• Количество: {last_order['drink_count']}\n"
            f"• Цена: {last_order['total_price']}₽\n"
            f"• Дата: {last_order['created_at'].strftime('%d.%m.%Y')}\n\n"
            f"Что будем делать?"
        )
        if last_order["image_file_id"]:
            await update.effective_message.reply_photo(
                photo=last_order["image_file_id"],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        else:
            await update.effective_message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

    else:
        # Меню для новых клиентов
        media_group = [InputMediaPhoto(open(path, "rb")) for path in MENU_URL]
        await update.message.reply_media_group(media_group)
        keyboard = [[InlineKeyboardButton("🍮 Сделать заказ", callback_data="new_order")]]
        await update.message.reply_text(
            "Ознакомьтесь с напитками в меню 😻, чтобы",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    return #здесь будет переход в логику клиента

# === Отмена ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Действие отменено. Для продолжения работы отправьте команду /start",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END
