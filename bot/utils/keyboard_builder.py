from decimal import Decimal
from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db.models import DrinkSize, Size, Image
from db.db_async import get_async_session

def build_types_keyboard(types, selected):
    """Формирует inline-клавиатуру с отметками выбранных типов."""
    keyboard = []
    for t in types:
        mark = "📍 " if t["id"] in selected else ""
        keyboard.append([InlineKeyboardButton(f"{mark}{t['name']}", callback_data=f"type_{t['id']}")])
    
    # Добавляем кнопку подтверждения
    keyboard.append([InlineKeyboardButton("✅ Подтвердить выбор", callback_data="confirm_types")])
    return keyboard

def build_price_filter_keyboard():
    return [
        [InlineKeyboardButton("0 – 3000 ₽", callback_data="price_0_3000")],
        [InlineKeyboardButton("3000 – 5900 ₽", callback_data="price_3000_5900")],
        [InlineKeyboardButton("6000+ ₽", callback_data="price_6000_plus")],
        [InlineKeyboardButton("💰 Без фильтра", callback_data="price_all")]
    ]

def build_add_keyboard(adds, selected):
    """Формирует inline-клавиатуру с отметками выбранных типов."""
    keyboard = []

    for a in adds:
        mark = "📌 " if a["id"] in selected else ""
        keyboard.append([InlineKeyboardButton(f"{mark}{a['name']}", callback_data=f"type_{a['id']}")])

    # Добавляем кнопки в зависимости от выбранных
    if selected:
        # Есть выбранные — только Подтвердить
        keyboard.append([InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_adds")])
    else:
        # Нет выбранных — Подтвердить и Пропустить
        keyboard.append([
            InlineKeyboardButton("➡️ Пропустить", callback_data="skip")
        ])

    return keyboard

async def get_drink_sizes_keyboard(drink_id: int) -> tuple[list[dict], InlineKeyboardMarkup]:
    """
    Возвращает:
    1. Список размеров (для логики) — list[dict]
    2. InlineKeyboardMarkup с кнопками выбора размера

    Кнопка: "<Размер> – <Цена>₽"
    callback_data: "select_size_<drink_size_id>"
    """
    async with get_async_session() as session:
        result = await session.execute(
            select(
                DrinkSize.id.label("drink_size_id"),
                Size.name.label("size_name"),
                DrinkSize.price
            )
            .join(Size, Size.id == DrinkSize.size_id)
            .where(
                DrinkSize.drink_id == drink_id,
                DrinkSize.is_active == True
            )
            .order_by(DrinkSize.price.asc())
        )
        sizes = result.mappings().all()

                # Получаем первое активное фото
        image_result = await session.execute(
            select(Image.tg_file_id)
            .where(Image.drink_id == drink_id, Image.is_active == True)
            .order_by(Image.created_at.asc())
            .limit(1)
        )
        image_row = image_result.first()
        image_file_id = image_row[0] if image_row else None

    # Формируем одну строку кнопок для размеров
    size_buttons = [
        InlineKeyboardButton(
            f"{s['size_name']} – {float(s['price']):.0f}₽",
            callback_data=f"select_size_{s['drink_size_id']}"
        )
        for s in sizes
    ]

    keyboard = [size_buttons]  # все размеры в одном ряду
    keyboard.append([InlineKeyboardButton("🔙 Начать сначала", callback_data="new_order")])

    return sizes, InlineKeyboardMarkup(keyboard), image_file_id

async def build_order_keyboard(order, adds, selected_adds, total_price):
    """Формируем клавиатуру заказа"""
    qty_buttons = [
        InlineKeyboardButton("➖", callback_data=f"update_qty_-_{order.id}"),
        InlineKeyboardButton(str(order.drink_count), callback_data="noop"),
        InlineKeyboardButton("➕", callback_data=f"update_qty_+_{order.id}")
    ]

    add_buttons = []
    row = []
    for idx, add in enumerate(adds, start=1):
        is_selected = add.id in selected_adds
        label = f"{'🔘 ' if is_selected else '⚪️ '}{add.name} - {int(add.price)}₽"
        row.append(InlineKeyboardButton(label, callback_data=f"toggle_add_{add.id}_{order.id}"))
        if idx % 2 == 0:
            add_buttons.append(row)
            row = []
    if row:
        add_buttons.append(row)

    pay_button = [InlineKeyboardButton(f"💳 Оплатить {int(total_price)} ₽", callback_data=f"pay_{order.id}")]

    return InlineKeyboardMarkup([qty_buttons] + add_buttons + [pay_button])