from handlers.SelectDrinkConversation import *

select_coffee_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_select_drink, pattern="^new_order$"),
                  CommandHandler("new_order", start_select_drink),
                  CallbackQueryHandler(handle_size_selection, pattern="^select_size_\\d+$")],
    states={
        DRINK_TYPES_SELECTION: [CallbackQueryHandler(handle_drinktype_selection, pattern="^drink_type_\\d+$")],
        SELECT_SIZE: [CallbackQueryHandler(handle_size_selection, pattern="^select_size_\\d+$"),
                      CallbackQueryHandler(start_select_drink, pattern="^new_order$")],
        SELECT_ADDS: [CallbackQueryHandler(handle_update_quantity, pattern="^update_qty_"),
                        CallbackQueryHandler(handle_toggle_add, pattern="^toggle_add_"),
                    ],
        CUSTOMER_COMMENT: [],
        CONFIRM_ORDER: []
                },
    fallbacks=[CommandHandler("cancel", cancel)],
)


