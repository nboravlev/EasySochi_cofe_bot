from handlers.AddCoffeeConversation import *

add_coffee_conv = ConversationHandler(
    entry_points=[
        CommandHandler("create_card", start_add_object),
        CallbackQueryHandler(start_add_object, pattern="^create_card$")
    ],
    states={
        DRINK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_drink_name)],
        DRINK_TYPE: [CallbackQueryHandler(handle_drink_type, pattern=r'^\d+$')],
        DRINK_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_drink_size)],
        DRINK_ADDS: [CallbackQueryHandler(handle_adds_multiselection, pattern=r'^(type_|confirm_adds|skip)')], 
        DRINK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_description)],
        DRINK_PHOTO: [
            MessageHandler(filters.PHOTO, handle_photo),
            MessageHandler(filters.Regex("^(Готово|готово)$"), handle_photos_done)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        CallbackQueryHandler(cancel, pattern="cancel")
    ],
    allow_reentry=True,
)



