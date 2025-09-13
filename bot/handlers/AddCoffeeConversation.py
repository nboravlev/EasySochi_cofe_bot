from db.db_async import get_async_session
from db.models.drink_types import DrinkType
from db.models.drinks import Drink
from db.models.images import Image
from db.models.adds import Add
from db.models.drink_sizes import DrinkSize
from db.models.drink_adds import DrinkAdd
from db.models.sizes import Size

from sqlalchemy.orm import selectinload

from sqlalchemy import select

from telegram import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    Update, 
    ReplyKeyboardRemove, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
    )
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    CallbackQueryHandler
)

from utils.escape import safe_html
from utils.keyboard_builder import build_add_keyboard
from utils.full_view_manager import render_coffee_card
from utils.logging_config import log_function_call, get_logger
from utils.call_coffe_size import init_size_map, get_size_id_async
from utils.preprocess_foto import preprocess_photo_crop_center

logger = get_logger(__name__)

# Состояния
(
    DRINK_NAME,
    DRINK_TYPE,
    DRINK_SIZE,
    DRINK_ADDS,
    DRINK_DESCRIPTION,
    DRINK_PHOTO
) = range(6)

SIZES = ["S","M","L","XL"]


# ====== START ADD DRINK ======
@log_function_call(action="Adding_drink_start")
async def start_add_object(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления напитка"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
        send_to = query.message
    else:
        send_to = update.message

    keyboard = [[KeyboardButton("Сохранить название")]]
    await send_to.reply_text(
        "Введите название напитка:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return DRINK_NAME

@log_function_call(action="Adding_drink_name")
async def handle_drink_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.message.text or "").strip()
    if not name or name.lower() == "сохранить название":
        name = "Просто кофе"
    else:
        name = safe_html(name)[:155]

    context.user_data["name"] = name

    async with get_async_session() as session:
        types = (await session.execute(DrinkType.__table__.select())).fetchall()
        keyboard = [[InlineKeyboardButton(t.name, callback_data=str(t.id))] for t in types]
        reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Хорошее название <b>{name}</b>\nВыберите тип напитка:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return DRINK_TYPE

@log_function_call(action="Adding_drink_type")
async def handle_drink_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    type_id = int(query.data)
    print(f"DEBUG drink_TYPE_ID: {type_id}")
    context.user_data["drink_type_id"] = type_id

    # Переходим к размерам
    context.user_data["current_size_index"] = 0
    context.user_data["drink_sizes"] = []
    return await ask_drink_size(update, context)

@log_function_call(action="Adding_drink_size")
async def ask_drink_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос цены для текущего размера"""
    if update.callback_query:
        target = update.callback_query.message
        await update.callback_query.answer()
    else:
        target = update.message

    idx = context.user_data.get("current_size_index", 0)

    # Если все размеры пройдены
    if idx >= len(SIZES):
        # Проверка: есть ли хотя бы один размер с ценой
        if not context.user_data.get("drink_sizes"):
            # Начинаем ввод заново
            context.user_data["drink_sizes"] = []  # сброс старых данных
            context.user_data["current_size_index"] = 0
            await target.reply_text(
                "⚠️ Вы должны указать хотя бы один размер с ценой. "
                "Начнем ввод размеров заново."
            )
            # Перезапускаем функцию для размера S
            return await ask_drink_size(update, context)
        else:
            # Все размеры пройдены и хотя бы один есть
            return await ask_drink_adds(update, context)

    size = SIZES[idx]
    keyboard = ReplyKeyboardMarkup([["Да", "Нет"]], resize_keyboard=True, one_time_keyboard=True)
    await target.reply_text(
        f"Добавляем размер {size}? Введите цену или 'Нет', если этого размера нет.",
        reply_markup=keyboard
    )
    return DRINK_SIZE



async def handle_drink_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_size_index"]
    size = SIZES[idx]
    raw_text = (update.message.text or "").strip().lower()

    if raw_text == "нет":
        context.user_data["current_size_index"] += 1
        return await ask_drink_size(update, context)

    try:
        price = float(raw_text.replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        logger.error(f"Некорректная цена для {size}: {raw_text}")
        await update.message.reply_text(
            f"Некорректная цена для размера {size}. "
            f"Введите число (например: 120) или «Нет», если размер не нужен:"
        )
        return DRINK_SIZE

    context.user_data["drink_sizes"].append({"size": size, "price": price})
    context.user_data["current_size_index"] += 1
    return await ask_drink_size(update, context)


# ====== ADD ADDS ======
@log_function_call(action="Adding_drink_adds")
async def ask_drink_adds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with get_async_session() as session:
        result = await session.execute(Add.__table__.select())
        adds = [{"id": t.id, "name": t.name} for t in result.fetchall()]
        context.user_data["adds"] = adds
        context.user_data["selected_adds"] = []

        keyboard = build_add_keyboard(adds, [])
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                f"Выберите добавки для {context.user_data.get('name')}:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                f"Выберите добавки для {context.user_data.get('name')}:",
                reply_markup=reply_markup
            )
        return DRINK_ADDS


async def handle_adds_multiselection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    selected = context.user_data.get("selected_adds", [])

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
        send_to = query.message  # для reply_text
    else:
        send_to = update.message  # для reply_text


    if data == "skip":
        keyboard = [[KeyboardButton("Пропустить описание")]]
        await send_to.reply_text(
        "Создайте привлекательное описание или нажмите Пропустить:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
        return DRINK_DESCRIPTION
    if data == "confirm_adds":
        selected_names = [a["name"] for a in context.user_data["adds"] if a["id"] in selected]
        keyboard = [[KeyboardButton("Пропустить описание")]]
        await query.edit_message_text(
            text="✅ Вы выбрали добавки: " + ", ".join(selected_names) + ""
        )
        await send_to.reply_text(
        "Создайте привлекательное описание или нажмите Пропустить:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
        return DRINK_DESCRIPTION

    # Выбор/снятие добавки
    try:
        add_id = int(data.replace("type_", ""))
    except ValueError:
        await query.edit_message_text("Ошибка выбора. Попробуйте снова.")
        return DRINK_ADDS

    if add_id in selected:
        selected.remove(add_id)
    else:
        selected.append(add_id)

    context.user_data["selected_adds"] = selected
    keyboard = build_add_keyboard(context.user_data["adds"], selected)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Выберите добавки для {context.user_data.get('name')}:",
        reply_markup=reply_markup
    )
    return DRINK_ADDS


# ====== DESCRIPTION ======
@log_function_call(action="Adding_drink_description")
async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_desc = (update.message.text or "").strip()
    if raw_desc.lower() in ("", "пропустить описание"):
        description = "Просто хороший напиток без специального описания. 👍"
    else:
        description = safe_html(raw_desc)[:255]

    context.user_data["description"] = description
    context.user_data["photos"] = []
    await update.message.reply_text(
        "Загрузите одно фото для карточки напитка. После загрузки фото нажмите «Готово».",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Готово")]], resize_keyboard=True,one_time_keyboard=True)
    )

    return DRINK_PHOTO


# ====== PHOTO ======
@log_function_call(action="Adding_drink_photo")
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    original_file_id = photo.file_id

    # Применяем кроп и получаем новый file_id
    new_file_id = await preprocess_photo_crop_center(original_file_id, context.bot, update.effective_chat.id)
    context.user_data.setdefault("photos", []).append(new_file_id)

    print(f"DEBUG: photos in user_data: {context.user_data['photos']}")

    await update.message.reply_text(
        f"Фото добавлено ({len(context.user_data['photos'])} шт.)."
        f"нажмите «Готово».",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Готово")]], resize_keyboard=True,one_time_keyboard=True)
    )
    return DRINK_PHOTO


async def handle_photos_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photos = context.user_data.get("photos", [])
    if not photos:
        logger.warning(f"Пользователь {update.effective_user.id} не загрузил ни одного фото")
        await update.message.reply_text("Вы не загрузили ни одного фото. Напиток не будет сохранён.")
        return DRINK_PHOTO

    tg_user_id = context.user_data.get("tg_user_id") or update.effective_user.id
    async with get_async_session() as session:
        drink = Drink(
            name=context.user_data['name'],
            type_id=context.user_data['drink_type_id'],
            created_by=tg_user_id,
            description=context.user_data['description']
        )
        session.add(drink)
        await session.flush()

        for file_id in photos:
            session.add(Image(drink_id=drink.id, tg_file_id=file_id))

        try:
            for item in context.user_data.get("drink_sizes", []):
                size_name = item.get("size")
                price = item.get("price")
                try:
                    size_id = await get_size_id_async(size_name)
                except KeyError:
                    logger.error(f"Размер '{size_name}' не найден в справочнике размеров")
                    await update.message.reply_text(
                        f"Размер '{size_name}' не найден. Проверьте справочник размеров."
                    )
                    await session.rollback()
                    return ConversationHandler.END

                session.add(DrinkSize(
                    drink_id=drink.id,
                    size_id=size_id,
                    price=price
                ))
        except Exception as exc:
            logger.exception("Ошибка при сохранении размеров", exc_info=exc)
            await session.rollback()
            await update.message.reply_text("Произошла ошибка при сохранении размеров.")
            return ConversationHandler.END

        for add_id in context.user_data.get("selected_adds", []):
            session.add(DrinkAdd(drink_id=drink.id, add_id=add_id))

        await session.flush()
        #await session.refresh(drink, attribute_names=["drink_sizes", "drink_adds", "images", "drink_type"])

        # Предварительно загружаем все связи через select + options
        stmt = (
            select(Drink)
            .where(Drink.id == drink.id)
            .options(
                selectinload(Drink.drink_sizes).selectinload(DrinkSize.sizes),
                selectinload(Drink.drink_adds).selectinload(DrinkAdd.add),
                selectinload(Drink.images),
                selectinload(Drink.drink_type),
            )
        )
        result = await session.execute(stmt)
        drink = result.scalars().first()

        text, _, markup = render_coffee_card(drink)

        if drink.images:
            await update.message.reply_photo(
                photo=str(drink.images[0].tg_file_id),
                caption=text,
                parse_mode="HTML",
                reply_markup=markup
            )
        else:
            await update.message.reply_text(
                text=text,
                parse_mode="HTML",
                reply_markup=markup
            )

        await session.commit()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Вы вышли из диалога.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END
