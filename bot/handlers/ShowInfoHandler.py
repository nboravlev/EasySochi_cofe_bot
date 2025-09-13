from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, ConversationHandler, ApplicationHandlerStop, CallbackQueryHandler

from utils.logging_config import log_function_call, LogExecutionTime, get_logger

import os

logger = get_logger(__name__)

INFO_TEXTS = {
    "info_booking": {
        "title": "🐱 *Инструкция для гостя:*",
        "body": (
            "1. Нажмите Старт и пройдите короткую регистрацию;\n"
            "2. \n"
            "3. \n"
            "4. \n"
            "5. \n"
            "6. \n"
            "7. \n"
            "8. \n"
            "9. \n"
            "10. Если возникнут трудности, напишите в раздел 'Помощь'."
        )
    },
    "info_object": {
        "title": "🐼 *Инструкция для менеджера*",
        "body": (
            "1. Нажмите 'Start' и пройдите короткую регистрацию;\n"
            "2. Если ваш ИД с списке админов, вы попадете в раздел администрирования;\n"
            "3. Чтобы создать напиток в меню передите в раздел 'Создать карточку';\n"
            "4. Создание карточки происходит в формате диалога. Следуйте подсказкам робота;\n"
            "5. Введите название и отправьте сообщение;\n"
            "6. Выберите тип;\n"
            "7. Робот поочередно запрашивает стоимость напитка для размера S,M,L,XL;\n"
            "8. Если размера для данной позиции не существует, то просто нажать Нет;\n"
            "9. Если нажать Нет на все запросы, то будет ошибка и работ начнет блок цены с начала;\n"
            "10. Далее робот покажет список доступных добавок к напиткам;\n"
            "11. Отмечайте актуальные для данной позиции;\n"
            "12. Фото добавляется одно на позицию. Для всех размеров;\n"
            "13. При добавлении фото дождетесь пока появится сообщение и кнопка 'Готово';\n"
            "14. После внесения всех данных робот демонстрирует карточку;\n"
            "15. Проверьте информацию и если все в порядке жмите 'Подтвердить';\n"
            "16. Если есть ошибки жмите 'Отменить' и начните ввод заново."
        )
    }
}


def _get_effective_message(update: Update):
    """
    Возвращает message-объект, независимо от того, пришло ли это update.message
    или это callback_query (update.callback_query.message).
    """
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню справки. Работает как при прямом вызове /info, так и при callback.
    """
    message = _get_effective_message(update)
    if not message:
        return

    keyboard = [
        [InlineKeyboardButton("🐱 Инструкция для гостя", callback_data="info_booking")],
        [InlineKeyboardButton("🐼 Инструкция для менеджера", callback_data="info_object")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("ℹ️ Выберите инструкцию:", reply_markup=reply_markup)


async def show_info_text(update_or_query: Update, key: str):
    """
    Выводит справочный текст по ключу. Работает и для обычных сообщений, и для callback.
    Кнопка 'Назад в инфо' имеет callback_data='help_menu'.
    """
    data = INFO_TEXTS.get(key)
    if not data:
        return

    text = f"{data['title']}\n\n{data['body']}"
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Назад в инфо", callback_data="info_menu")]]
    )

    message = _get_effective_message(update_or_query)
    if not message:
        return

    # Можно использовать edit_message_text если вы хотите заменить предыдущую карточку,
    # но reply_text достаточно универсален.
    await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def info_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик callback'ов для help_*
    - отвечает на query (query.answer())
    - вызывает show_help_text или возвращает в меню вызовом help_command
    """
    query = update.callback_query
    if not query:
        return

    await query.answer()  # убираем "крутилку" в UI

    data = query.data or ""
    if data == "info_booking":
        await show_info_text(update, "info_booking")
    elif data == "info_object":
        await show_info_text(update, "info_object")
    elif data == "info_menu":
        await info_command(update, context)
    else:
        return