from handlers.OrderOutConversation import *

manager_processins_order = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(take_order_handler, pattern="^take_\d+")
    ],
    states={
        ORDER_READY: [CallbackQueryHandler(order_ready_handler, pattern=r"^order_ready_\d+")],
    },
    fallbacks=[

    ],
)