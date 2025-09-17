from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ContextTypes, ConversationHandler, ApplicationHandlerStop, CallbackQueryHandler

from utils.logging_config import log_function_call, LogExecutionTime, get_logger

import os

logger = get_logger(__name__)


    
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⛔ Вы остановили бота. Чтобы возобновить работу нажмите /start")
    context.user_data.clear()
    return ConversationHandler.END