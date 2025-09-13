from handlers.RegistrationHandler import registration_conversation
from handlers.AddCoffeeHandler import add_coffee_conv
from handlers.CoffeeCommitHandler import confirm_coffee_handler
from handlers.CoffeeRedoHandler import redo_coffee_handler
from handlers.SelectDrinkHandler import select_coffee_conv
#from handlers.CommitDeclineCancelBookingHandler import conv_commit_decline_cancel
#from handlers.BookingChatHandler import booking_chat
from handlers.UserSendProblemHandler import problem_handler
from handlers.AdminReplayUserProblemHandler import admin_replay_handler
#from handlers.UnknownComandHandler import unknown_command_handler
from handlers.GlobalCommands import cancel_command
from handlers.OrderOutHandler import manager_processins_order
from handlers.ShowInfoHandler import info_callback_handler, info_command
from handlers.PaymentConversationHandler import PreCheckoutQueryHandler, pay_order, precheckout_handler, successful_payment_handler
from handlers.GetOrderConversationHandler import order_received_handler

from db_monitor import check_db
from check_expired_orders import check_expired_order

import os
from pathlib import Path
from datetime import time

from utils.logging_config import setup_logging, log_function_call, get_logger
from utils.call_coffe_size import init_size_map

import os

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    BotCommand,
    BotCommandScopeChat
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ApplicationBuilder,
    JobQueue
)
# Initialize comprehensive logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir=os.getenv("LOG_DIR", "/app/logs"),
    enable_console=True,
    enable_file=True
)

logger = get_logger(__name__)

async def post_init(application: Application) -> None:
    # Настройка меню команд (синяя плашка)
    commands = [
        BotCommand("start", "🔄 Перезапустить бот"),
        BotCommand("help", "⚠️ Помощь"),
        BotCommand('info', "📌 Инструкция"),
        BotCommand("cancel", "⛔ Отмена")

    ]
    await application.bot.set_my_commands(commands)

    # Инициализация SIZE_MAP
    await init_size_map()

    logger.info("SIZE_MAP успешно инициализирован")

    application.job_queue.run_repeating(
        check_db,
        interval=30 * 60,
        first=10
    )
    application.job_queue.run_repeating(
    check_expired_order,
    interval=30 * 60,
    first=6
    )

def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env")


    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    #глобальные обработчики
    app.add_handler(CommandHandler("info",info_command), group=0)
    app.add_handler(problem_handler, group=0)
    app.add_handler(admin_replay_handler,group=0)

    #админские обработки
    app.add_handler(
        CallbackQueryHandler(info_callback_handler, pattern=r"^info_"),
        group=1
    )
    #app.add_handler(unknown_command_handler,group=0) #обработчик незнакомых команд
    
    # Регистрируем хендлеры
    
    app.add_handler(registration_conversation, group=1) #процесс регистрации (users, sessions), выбор роли
    app.add_handler(add_coffee_conv, group=1)  #создание карточки товара
    app.add_handler(confirm_coffee_handler, group=1) #сохранение карточки товара
    app.add_handler(redo_coffee_handler, group=1)  #отмена карточки
    app.add_handler(select_coffee_conv, group=1)  #показ карточек кофе
 
    app.add_handler(CallbackQueryHandler(pay_order, pattern=r"^pay_"),group=1)
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler),group=1)
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler),group=1)

    app.add_handler(manager_processins_order, group=1) #меняем статус заказа по мере готовности
   
    app.add_handler(CallbackQueryHandler(order_received_handler, pattern=r"^order_received_\d+"),group=1)  #обработка нажатия гостем кнопки получения заказа


    # Без asyncio
    app.run_polling()

if __name__ == "__main__":

    main()
