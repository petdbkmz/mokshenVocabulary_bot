from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.cards import (
    get_card_by_id, get_words_by_letter, get_all_letters,
    search_words_by_pattern
)
from bot.keyboards import (
    get_dictionary_main_keyboard, get_letters_keyboard,
    get_words_by_letter_keyboard, get_search_results_keyboard,
    get_back_button
)
from bot.utils import delete_previous, format_card_info, get_language_name

# ============================================
# ГЛАВНОЕ МЕНЮ СЛОВАРЯ
# ============================================

async def dictionary_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню словаря"""
    query = update.callback_query
    await query.answer()
    
    reply_markup = get_dictionary_main_keyboard()
    
    await delete_previous(update)
    await query.message.reply_text(
        "📖 <b>Словарь</b>\n\nВыбери словарь:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ============================================
# ВЫБОР ЯЗЫКА
# ============================================

async def dictionary_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор языка для словаря"""
    query = update.callback_query
    await query.answer()
    
    language_from = query.data.replace('dict_lang_', '')
    context.user_data['dict_language'] = language_from
    
    reply_markup, language_name, letters_count = await get_letters_keyboard(language_from)
    
    # Дополнительная информация для мокшанского словаря
    moksha_info = ""
    if language_from == 'mdf':
        moksha_info = (
            "\n\n<i>Полный словарь — @MokshaWordBot\n"
            "Группа ВК (чтобы начать пользоваться, надо написать сообщение в группу): https://vk.ru/club237187875</i>"
        )
    
    await delete_previous(update)
    
    if letters_count == 0:
        keyboard = [
            [InlineKeyboardButton("🔍 Найти слово", callback_data="dict_search")],
            [InlineKeyboardButton("⬅️ Назад к выбору словаря", callback_data="dictionary_main")],
            [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"📭 В словаре {language_name} пока нет слов.{moksha_info}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
    
    await query.message.reply_text(
        f"📖 <b>{language_name}</b>\n\nВыбери первую букву слова:{moksha_info}",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ============================================
# ПОКАЗ СЛОВ ПО БУКВЕ
# ============================================

async def dictionary_letter(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Показать слова по букве с пагинацией"""
    query = update.callback_query
    await query.answer()
    
    # Определяем букву и страницу
    if query.data.startswith('dict_letter_page_'):
        parts = query.data.split('_')
        letter = parts[3]
        page = int(parts[4]) if len(parts) > 4 else 0
        context.user_data['dict_letter'] = letter
        context.user_data['dict_letter_page'] = page
    else:
        letter = query.data.replace('dict_letter_', '')
        page = 0
        context.user_data['dict_letter'] = letter
        context.user_data['dict_letter_page'] = page
    
    language_from = context.user_data.get('dict_language', 'ru')
    per_page = 5
    
    words, total = await get_words_by_letter(language_from, letter, page, per_page)
    
    await delete_previous(update)
    
    if not words:
        language_name = get_language_name(language_from)
        moksha_info = ""
        if language_from == 'mdf':
            moksha_info = (
                "\n\n<i>Полный словарь — @MokshaWordBot\n"
                "Группа ВК (чтобы начать пользоваться, надо написать сообщение в группу): https://vk.ru/club237187875</i>"
            )
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к буквам", callback_data=f"dict_lang_{language_from}")],
            [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"📭 В словаре {language_name} нет слов на букву '{letter}'.{moksha_info}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
    
    reply_markup = await get_words_by_letter_keyboard(
        words, letter, page, total, per_page, language_from
    )
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    start = page * per_page + 1
    end = min((page + 1) * per_page, total)
    
    message = f"📖 <b>Слова на букву '{letter}'</b>\n"
    message += f"📄 {start}-{end} из {total}\n\n"
    
    await query.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ============================================
# ПОКАЗ ДЕТАЛЕЙ СЛОВА
# ============================================

async def dictionary_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали слова"""
    query = update.callback_query
    await query.answer()
    
    card_id = int(query.data.split('_')[2])
    card = await get_card_by_id(card_id)
    
    if not card:
        await delete_previous(update)
        await query.message.reply_text("❌ Слово не найдено")
        return
    
    message = format_card_info(card)
    
    lang_from = context.user_data.get('dict_language', 'ru')
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад к буквам", callback_data=f"dict_lang_{lang_from}")],
        [InlineKeyboardButton("🔍 Найти слово", callback_data="dict_search")],
        [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await delete_previous(update)
    
    if card.get('image_url'):
        try:
            await query.message.reply_photo(
                photo=card['image_url'],
                caption=message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            await query.message.reply_text(
                f"{message}\n\n⚠️ <i>Картинка не загрузилась</i>",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
    else:
        await query.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

# ============================================
# ПОИСК В СЛОВАРЕ
# ============================================

async def dictionary_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать поиск в словаре"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['dict_search_page'] = 0
    context.user_data['dict_search_query'] = None
    
    await delete_previous(update)
    await query.message.reply_text(
        "🔍 <b>Поиск слова</b>\n\n"
        "Напиши слово или его часть.\n"
        "Для поиска по первым буквам используй * (звёздочку):\n"
        "Например: <code>ку*</code> — найдет все слова, начинающиеся на 'ку'.\n\n"
        "Результат поиска:\n"
        "• (рус.) — слова на русском\n"
        "• (мокш.) — слова на мокшанском\n\n"
        "Для отмены отправь /cancel\n"
        "Чтобы перезапустить бота, отправь /start",
        parse_mode='HTML'
    )
    context.user_data['awaiting_dict_search'] = True

async def dictionary_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка поиска в словаре"""
    query_text = update.message.text.strip()
    
    if query_text.lower() == '/cancel':
        context.user_data.pop('awaiting_dict_search', None)
        await update.message.reply_text("❌ Поиск отменён.")
        return
    
    context.user_data['dict_search_query'] = query_text
    context.user_data['dict_search_page'] = 0
    
    await show_search_results(update, context, query_text, 0)

async def show_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE, query_text: str, page: int):
    """Показать результаты поиска с пагинацией"""
    per_page = 5
    results, total = await search_words_by_pattern(query_text, page=page, per_page=per_page)
    
    if not results:
        keyboard = [
            [InlineKeyboardButton("📞 Связаться с поддержкой", callback_data="contact_support")],
            [InlineKeyboardButton("🔍 Новый поиск", callback_data="dict_search")],
            [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await delete_previous(update)
            await update.callback_query.message.reply_text(
                "🔍 <b>Слово не найдено</b>\n\n"
                "Попробуйте изменить запрос или связаться с поддержкой, чтобы предложить новое слово.",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "🔍 <b>Слово не найдено</b>\n\n"
                "Попробуйте изменить запрос или связаться с поддержкой, чтобы предложить новое слово.",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        context.user_data.pop('awaiting_dict_search', None)
        return
    
    reply_markup = await get_search_results_keyboard(results, query_text, page, total, per_page)
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    start = page * per_page + 1
    end = min((page + 1) * per_page, total)
    
    message = f"🔍 <b>Результаты поиска</b>\n"
    message += f"📄 {start}-{end} из {total}\n\n"
    
    if update.callback_query:
        await delete_previous(update)
        await update.callback_query.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    context.user_data.pop('awaiting_dict_search', None)

async def dict_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пагинации в результатах поиска"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    query_text = parts[3]
    page = int(parts[4]) if len(parts) > 4 else 0
    
    await show_search_results(update, context, query_text, page)

# ============================================
# ОБРАБОТЧИК ВЫБОРА ТЕМАТИКИ
# ============================================

async def topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора тематики"""
    query = update.callback_query
    await query.answer()
    
    topic = query.data.replace('topic_', '')
    context.user_data['selected_topic'] = topic
    
    # Получаем количество слов в тематике
    from database.cards import get_words_count_by_topic
    count = await get_words_count_by_topic(topic)
    context.user_data['topic_words_count'] = count
    
    await query.edit_message_text(
        f"✅ Выбрана тематика: <b>{topic}</b>\n\nНачинаю изучение...",
        parse_mode='HTML'
    )
    
    import asyncio
    await asyncio.sleep(0.5)
    
    # Импортируем study из текущего модуля (чтобы избежать циклического импорта)
    from .study import study
    await study(update, context)