# Fixed ConversationHandler configuration

from handlers.RegistrationConversation import *

registration_conversation = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        CallbackQueryHandler(start, pattern="back_menu")
    ],
    states={
        NAME_REQUEST: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_request)
        ],
        MAIN_MENU: [
            CallbackQueryHandler(show_customer_menu),  # <-- здесь будет обработка нажатий меню
            # или другой handler, если для менеджера отдельный
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CommandHandler("start", start)
    ]
)
