"""
Подпакет обработчиков. Все функции, которые реагируют на команды и кнопки.
"""

# Основные обработчики
from .start import start
from .study import study, handle_hint, handle_skip, choice_callback, reset_topic_callback, handle_answer
from .dictionary import (
    dictionary_main, dictionary_language, dictionary_letter, 
    dictionary_word, dictionary_search_start, dictionary_search,
    dict_search_page_callback, topic_callback
)
from .admin import (
    show_admin_panel, list_users, list_cards, users_page_callback,
    show_tables_callback, view_table_callback, refresh_table_callback,
    handle_edit_actions, confirm_delete_card, confirm_clear_stats,
    send_notification, backup_command,
    handle_add_word, handle_delete_word, handle_search,
    handle_edit_field, handle_user_stats, handle_clear_stats,
    handle_notification, add_editor_command, remove_editor_command,
    tables_command, handle_admin_actions,
    restore_command, confirm_restore
)
from .stats import stats_command
from .support import (
    contact_support, check_support_command,
    handle_admin_reply, handle_admin_response_text,
    handle_support_message
)
from .thanks import show_thanks, edit_thanks_start
from .button_callback import button_callback
from .text_handler import handle_text_input, handle_document

# Все функции, которые можно импортировать из bot.handlers
__all__ = [
    # start
    'start',
    # study
    'study', 'handle_hint', 'handle_skip', 'choice_callback', 
    'reset_topic_callback', 'handle_answer',
    # dictionary
    'dictionary_main', 'dictionary_language', 'dictionary_letter', 
    'dictionary_word', 'dictionary_search_start', 'dictionary_search',
    'dict_search_page_callback', 'topic_callback',
    # admin
    'show_admin_panel', 'list_users', 'list_cards', 'users_page_callback',
    'show_tables_callback', 'view_table_callback', 'refresh_table_callback',
    'handle_edit_actions', 'confirm_delete_card', 'confirm_clear_stats',
    'send_notification', 'backup_command',
    'handle_add_word', 'handle_delete_word', 'handle_search',
    'handle_edit_field', 'handle_user_stats', 'handle_clear_stats',
    'handle_notification', 'add_editor_command', 'remove_editor_command',
    'tables_command', 'restore_command', 'confirm_restore',
    # stats
    'stats_command',
    # support
    'contact_support', 'check_support_command',
    'handle_admin_reply', 'handle_admin_response_text',
    'handle_support_message',
    # thanks
    'show_thanks', 'edit_thanks_start',
    # button_callback
    'button_callback',
    # text_handler
    'handle_text_input', 'handle_document',
]