from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database.users import is_editor, get_user_days
from config import THANKS_BUTTON_DAYS, LANGUAGE_NAMES

# ============================================
# ГЛАВНОЕ МЕНЮ
# ============================================

async def get_main_menu_keyboard(user_id: int):
    """Получить клавиатуру главного меню"""
    is_editor_user = await is_editor(user_id)
    user_days = await get_user_days(user_id)

    keyboard = [
        [InlineKeyboardButton("📚 Начать изучение", callback_data="start_study")],
        [InlineKeyboardButton("📖 Словарь", callback_data="dictionary_main")],
        [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")],
    ]

    if is_editor_user:
        keyboard.append([InlineKeyboardButton("⚙️ Управление", callback_data="admin_panel")])
        keyboard.append([InlineKeyboardButton("📢 Сделать уведомление", callback_data="send_notification")])

    keyboard.append([InlineKeyboardButton("📞 Связаться с поддержкой", callback_data="contact_support")])
    
    if user_days >= THANKS_BUTTON_DAYS:
        keyboard.append([InlineKeyboardButton("❤️ Выразить благодарность", callback_data="show_thanks")])

    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ ВОЗВРАТА В МЕНЮ
# ============================================

def get_back_button(extra_buttons: list = None):
    """Клавиатура с кнопкой 'Вернуться в главное меню'"""
    keyboard = []
    if extra_buttons:
        keyboard.extend(extra_buttons)
    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_back_to_admin_button():
    """Клавиатура с кнопкой 'Назад в админ-панель'"""
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад в админ-панель", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ ИЗУЧЕНИЯ
# ============================================

def get_study_keyboard(card_id: int):
    """Клавиатура для карточки с подсказкой"""
    keyboard = [
        [InlineKeyboardButton("💡 Подсказка", callback_data=f"hint_{card_id}")],
        [InlineKeyboardButton("⏭️ Пропустить", callback_data=f"skip_{card_id}")],
        [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_study_without_hint_keyboard(card_id: int):
    """Клавиатура для карточки без подсказки"""
    keyboard = [
        [InlineKeyboardButton("⏭️ Пропустить", callback_data=f"skip_{card_id}")],
        [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ ВЫБОРА ТЕМАТИК
# ============================================

async def get_topics_keyboard(page: int = 0, per_page: int = 10):
    """Клавиатура для выбора тематики с пагинацией"""
    from database.cards import get_all_topics_with_counts
    
    topics_with_counts = await get_all_topics_with_counts()
    total = len(topics_with_counts)
    
    start = page * per_page
    end = start + per_page
    current_topics = topics_with_counts[start:end]

    keyboard = [
        [InlineKeyboardButton("📚 Изучать все слова", callback_data="topic_Все слова")]
    ]

    for topic, count in current_topics:
        keyboard.append([InlineKeyboardButton(f"📖 {topic} (Слов: {count})", callback_data=f"topic_{topic}")])

    # Навигация
    nav_buttons = []
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"topics_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"topics_page_{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ СЛОВАРЯ
# ============================================

def get_dictionary_main_keyboard():
    """Главное меню словаря"""
    keyboard = [
        [InlineKeyboardButton("Русско-мокшанский словарь", callback_data="dict_lang_ru")],
        [InlineKeyboardButton("Мокшень-рузонь валкс", callback_data="dict_lang_mdf")],
        [InlineKeyboardButton("🔍 Найти слово", callback_data="dict_search")],
        [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_letters_keyboard(language_from: str):
    """Клавиатура с буквами для словаря"""
    from database.cards import get_all_letters
    
    letters = await get_all_letters(language_from)
    language_name = LANGUAGE_NAMES.get(language_from, language_from)

    if not letters:
        keyboard = [
            [InlineKeyboardButton("🔍 Найти слово", callback_data="dict_search")],
            [InlineKeyboardButton("⬅️ Назад к выбору словаря", callback_data="dictionary_main")],
            [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
        ]
        return InlineKeyboardMarkup(keyboard), language_name, 0

    keyboard = []
    row = []
    for i, letter in enumerate(letters):
        row.append(InlineKeyboardButton(letter, callback_data=f"dict_letter_{letter}"))
        if len(row) == 8:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔍 Найти слово", callback_data="dict_search")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад к выбору словаря", callback_data="dictionary_main")])
    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])

    return InlineKeyboardMarkup(keyboard), language_name, len(letters)

async def get_words_by_letter_keyboard(words: list, letter: str, page: int, total: int, per_page: int, language_from: str):
    """Клавиатура со словами по букве"""
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    keyboard = []
    for word in words:
        lang_label = "мокш." if word['language_from'] == 'mdf' else "рус."
        button_text = f"{word['word']} ({lang_label})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"dict_word_{word['card_id']}")])

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"dict_letter_page_{letter}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"dict_letter_page_{letter}_{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("🔍 Найти слово", callback_data="dict_search")])
    keyboard.append([InlineKeyboardButton("⬅️ Вернуться к буквам", callback_data=f"dict_lang_{language_from}")])
    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])

    return InlineKeyboardMarkup(keyboard)

async def get_search_results_keyboard(results: list, query: str, page: int, total: int, per_page: int):
    """Клавиатура для результатов поиска в словаре"""
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    keyboard = []
    for word in results:
        lang_label = "мокш." if word['language_from'] == 'mdf' else "рус."
        button_text = f"{word['word']} ({lang_label})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"dict_word_{word['card_id']}")])

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"dict_search_page_{query}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"dict_search_page_{query}_{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="dict_search")])
    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])

    return InlineKeyboardMarkup(keyboard)

# ============================================
# АДМИН-ПАНЕЛЬ
# ============================================

def get_admin_panel_keyboard():
    """Клавиатура админ-панели"""
    keyboard = [
        [InlineKeyboardButton("📥 Импорт из Excel", callback_data="admin_import")],
        [InlineKeyboardButton("➕ Добавить слово", callback_data="admin_add_word")],
        [InlineKeyboardButton("🔍 Найти слово", callback_data="admin_search")],
        [InlineKeyboardButton("📋 Список всех слов", callback_data="admin_list")],
        [InlineKeyboardButton("🗑️ Удалить слово", callback_data="admin_delete_word")],
        [InlineKeyboardButton("👥 Управление редакторами", callback_data="admin_editors")],
        [InlineKeyboardButton("📩 Обращения в поддержку", callback_data="admin_support")],
        [InlineKeyboardButton("📊 Статистика пользователя", callback_data="admin_user_stats")],
        [InlineKeyboardButton("🗑️ Очистить статистику", callback_data="admin_clear_stats")],
        [InlineKeyboardButton("📊 Просмотр таблиц БД", callback_data="admin_tables")],
        [InlineKeyboardButton("📋 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_edit_card_keyboard(card_id: int):
    """Клавиатура для редактирования карточки"""
    keyboard = [
        [InlineKeyboardButton("✏️ Редактировать слово", callback_data=f"edit_field_word_{card_id}")],
        [InlineKeyboardButton("✏️ Редактировать перевод", callback_data=f"edit_field_translation_{card_id}")],
        [InlineKeyboardButton("✏️ Редактировать тип", callback_data=f"edit_field_type_{card_id}")],
        [InlineKeyboardButton("✏️ Редактировать картинку", callback_data=f"edit_field_image_{card_id}")],
        [InlineKeyboardButton("✏️ Редактировать неправильные варианты", callback_data=f"edit_field_hints_{card_id}")],
        [InlineKeyboardButton("✏️ Редактировать тематики", callback_data=f"edit_field_topics_{card_id}")],
        [InlineKeyboardButton("✏️ Редактировать альтернативные переводы", callback_data=f"edit_field_alt_trans_{card_id}")],
        [InlineKeyboardButton("🗑️ Удалить слово", callback_data=f"edit_delete_{card_id}")],
        [InlineKeyboardButton("⬅️ Назад к списку", callback_data="admin_list_0")],
        [InlineKeyboardButton("⬅️ Назад в админ-панель", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirm_delete_keyboard(card_id: int):
    """Клавиатура для подтверждения удаления"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{card_id}"),
            InlineKeyboardButton("❌ Нет, отменить", callback_data=f"edit_select_{card_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirm_clear_stats_keyboard(user_id: int):
    """Клавиатура для подтверждения очистки статистики"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, очистить", callback_data=f"confirm_clear_{user_id}"),
            InlineKeyboardButton("❌ Нет, отменить", callback_data="admin_panel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ СТАТИСТИКИ
# ============================================

def get_stats_keyboard():
    """Клавиатура для статистики"""
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="show_stats")],
        [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ БЛАГОДАРНОСТИ
# ============================================

async def get_thanks_keyboard(is_admin: bool):
    """Клавиатура для благодарности"""
    keyboard = [
        [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("✏️ Редактировать текст", callback_data="edit_thanks")])
    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ ПОДДЕРЖКИ
# ============================================

def get_support_reply_keyboard(message_id: int):
    """Клавиатура для ответа на обращение"""
    keyboard = [[
        InlineKeyboardButton("✉️ Ответить", callback_data=f"reply_to_{message_id}")
    ]]
    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ ТАБЛИЦ БД
# ============================================

async def get_tables_keyboard():
    """Клавиатура со списком таблиц БД"""
    import sqlite3
    from config import DB_NAME
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    conn.close()
    
    keyboard = []
    for table in tables:
        table_name = table[0]
        if table_name.startswith('sqlite_'):
            continue
        keyboard.append([InlineKeyboardButton(f"📋 {table_name}", callback_data=f"view_table_{table_name}_0")])
    
    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_table_navigation_keyboard(table_name: str, page: int, total_pages: int):
    """Клавиатура для навигации по таблице"""
    keyboard = []
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"view_table_{table_name}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"view_table_{table_name}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_table_{table_name}_{page}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад к списку", callback_data="show_tables")])
    keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ СПИСКА ПОЛЬЗОВАТЕЛЕЙ
# ============================================

def get_users_pagination_keyboard(page: int, total_pages: int):
    """Клавиатура для пагинации списка пользователей"""
    keyboard = []
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"users_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages if total_pages > 0 else 1}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"users_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад в админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

# ============================================
# КЛАВИАТУРА ДЛЯ СПИСКА КАРТОЧЕК (АДМИН)
# ============================================

def get_admin_cards_pagination_keyboard(cards: list, page: int, limit: int, show_back: bool = True):
    """Клавиатура для списка карточек в админ-панели"""
    keyboard = []
    for card in cards:
        keyboard.append([
            InlineKeyboardButton(
                f"✏️ {card['word']}",
                callback_data=f"edit_select_{card['card_id']}"
            )
        ])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"admin_list_{page-1}"))
    if len(cards) == limit:
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"admin_list_{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    if show_back:
        keyboard.append([InlineKeyboardButton("⬅️ Назад в админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)