import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.users import update_activity

logger = logging.getLogger(__name__)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главный обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"🔘 Нажата кнопка: {query.data}")
    
    user_id = query.from_user.id
    await update_activity(user_id)
    
    data = query.data
    
    # ===== ПАГИНАЦИЯ =====
    if data.startswith("users_page_"):
        from .admin import users_page_callback
        await users_page_callback(update, context)
        return
    
    if data.startswith("topics_page_"):
        from .study import show_topic_selection
        page = int(data.split("_")[2])
        await show_topic_selection(update, context, page)
        return
    
    if data.startswith("admin_list_"):
        from .admin import list_cards
        try:
            page = int(data.split("_")[2])
            await list_cards(update, context, page)
        except (IndexError, ValueError):
            await list_cards(update, context, 0)
        return
    
    # ===== СБРОС ТЕМАТИКИ =====
    if data.startswith("reset_topic_"):
        from .study import reset_topic_callback
        await reset_topic_callback(update, context)
        return
    
    # ===== СЛОВАРЬ =====
    if data == "dictionary_main":
        from .dictionary import dictionary_main
        await dictionary_main(update, context)
        return
    
    if data.startswith("dict_lang_"):
        from .dictionary import dictionary_language
        await dictionary_language(update, context)
        return
    
    if data.startswith("dict_letter_"):
        from .dictionary import dictionary_letter
        await dictionary_letter(update, context)
        return
    
    if data.startswith("dict_letter_page_"):
        from .dictionary import dictionary_letter
        await dictionary_letter(update, context)
        return
    
    if data.startswith("dict_word_"):
        from .dictionary import dictionary_word
        await dictionary_word(update, context)
        return
    
    if data == "dict_search":
        from .dictionary import dictionary_search_start
        await dictionary_search_start(update, context)
        return
    
    if data.startswith("dict_search_page_"):
        from .dictionary import dict_search_page_callback
        await dict_search_page_callback(update, context)
        return
    
    # ===== ВЫБОР ТЕМАТИКИ =====
    if data.startswith("topic_"):
        from .dictionary import topic_callback
        await topic_callback(update, context)
        return
    
    # ===== ИЗУЧЕНИЕ =====
    if data.startswith("hint_"):
        from .study import handle_hint
        await handle_hint(update, context)
        return
    
    if data.startswith("skip_"):
        from .study import handle_skip
        await handle_skip(update, context)
        return
    
    if data.startswith("choice_"):
        from .study import choice_callback
        await choice_callback(update, context)
        return
    
    # ===== БЛАГОДАРНОСТЬ =====
    if data == "show_thanks":
        from .thanks import show_thanks
        await show_thanks(update, context)
        return
    
    if data == "edit_thanks":
        from .thanks import edit_thanks_start
        await edit_thanks_start(update, context)
        return
    
    # ===== ТАБЛИЦЫ БД =====
    if data == "show_tables":
        from .admin import show_tables_callback
        await show_tables_callback(update, context)
        return
    
    if data.startswith("view_table_"):
        from .admin import view_table_callback
        await view_table_callback(update, context)
        return
    
    if data.startswith("refresh_table_"):
        from .admin import refresh_table_callback
        await refresh_table_callback(update, context)
        return
    
    # ===== ГЛАВНОЕ МЕНЮ =====
    if data == "start_study":
        from .study import study
        await study(update, context)
        return
    
    if data == "show_stats":
        from .stats import stats_command
        await stats_command(update, context)
        return
    
    if data == "contact_support":
        from .support import contact_support
        await contact_support(update, context)
        return
    
    if data == "admin_panel":
        from .admin import show_admin_panel
        await show_admin_panel(update, context)
        return
    
    if data == "back_to_menu":
        from .start import start
        await start(update, context)
        return
    
    if data == "send_notification":
        from .admin import send_notification
        await send_notification(update, context)
        return
    
    # ===== АДМИН-ПАНЕЛЬ (все кнопки admin_*) =====
    if data.startswith("admin_"):
        from .admin import handle_admin_actions
        await handle_admin_actions(update, context)
        return
    
    # ===== РЕДАКТИРОВАНИЕ =====
    if data.startswith("edit_"):
        from .admin import handle_edit_actions
        await handle_edit_actions(update, context)
        return
    
    # ===== ПОДТВЕРЖДЕНИЯ =====
    if data.startswith("confirm_delete_"):
        from .admin import confirm_delete_card
        await confirm_delete_card(update, context)
        return
    
    if data.startswith("confirm_clear_"):
        from .admin import confirm_clear_stats
        await confirm_clear_stats(update, context)
        return

    if data.startswith("confirm_restore_"):
        from .admin import confirm_restore
        await confirm_restore(update, context)
        return
    
    # ===== ОТВЕТ НА ОБРАЩЕНИЕ =====
    if data.startswith("reply_to_"):
        from .support import handle_admin_reply
        await handle_admin_reply(update, context)
        return
    
    # ===== НЕИЗВЕСТНАЯ КОМАНДА =====
    logger.warning(f"❌ Неизвестный callback: {data}")
    await query.edit_message_text("❌ Неизвестная команда. Попробуй /start")