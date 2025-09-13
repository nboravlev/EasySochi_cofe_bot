from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from db.models.drinks import Drink

def render_coffee_card(drink: Drink) -> tuple[str, list[InputMediaPhoto] | None, InlineKeyboardMarkup]:
    # Формируем текст с размерами и ценами
    if drink.drink_sizes:
        sizes_text = "\n".join(
            f"{ds.sizes.name}: {ds.price} ₽" if ds.price else f"{ds.sizes.name}: нет"
            for ds in drink.drink_sizes
        )
    else:
        sizes_text = "Нет данных по размерам"

    # Формируем список добавок
    if drink.drink_adds:
        adds_text = ", ".join(adds.add.name for adds in drink.drink_adds)
    else:
        adds_text = "Нет добавок"

    # Основной текст карточки
    text = (
        f"<b>{drink.name}</b>\n\n"
        f"💬 {drink.description or 'Без описания'}\n\n"
        f"🏷️ Тип: {drink.drink_type.name}\n"
        f"💰 Цены по размерам:\n{sizes_text}\n"
        f"🍭 Можно добавить: {adds_text}"
    )

    # Фото (берем только первое)
    photos = [InputMediaPhoto(img.tg_file_id) for img in drink.images[:1]] if drink.images else None

    # Кнопки
    buttons = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_coffee_{drink.id}")],
        [InlineKeyboardButton("🔄 Внести заново", callback_data=f"redo_coffee_{drink.id}")]
    ]
    markup = InlineKeyboardMarkup(buttons)

    return text, photos, markup
