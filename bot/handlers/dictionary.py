from html import escape
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.cards import (
    get_card_by_id, get_words_by_letter, get_all_letters,
    search_words_by_pattern, get_all_topics_with_counts, get_words_by_category,
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
    
    context.user_data.pop('dict_back_to', None)
    context.user_data.pop('dict_language', None)  # сброс языка, чтобы «По категориям» всегда спрашивал
    context.user_data.pop('dict_categories_cache', None)
    
    reply_markup = get_dictionary_main_keyboard()
    
    await delete_previous(update)
    await query.message.reply_text(
        "📖 <b>Словарь</b>\n\nВыбери словарь:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ============================================
# СЛОВАРЬ ПО КАТЕГОРИЯМ
# ============================================

async def dictionary_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть список категорий в словаре.
    Если язык уже известен (пришли с экрана букв) — сразу показываем категории.
    Иначе — предлагаем выбрать язык.
    """
    lang = context.user_data.get('dict_language')
    
    if not lang:
        keyboard = [
            [InlineKeyboardButton("📖 Русско-мокшанский", callback_data="dict_cat_lang_ru")],
            [InlineKeyboardButton("📖 Мокшень-рузонь валкс", callback_data="dict_cat_lang_mdf")],
            [InlineKeyboardButton("⬅️ Назад к выбору словаря", callback_data="dictionary_main")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = "📂 <b>Словарь по категориям</b>\n\nВыберите язык:"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    await _show_dictionary_categories(update, context, 0)


async def dict_categories_lang_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор языка для категорий словаря"""
    query = update.callback_query
    await query.answer()
    
    lang = query.data.replace('dict_cat_lang_', '')
    context.user_data['dict_language'] = lang
    context.user_data.pop('dict_back_to', None)
    await _show_dictionary_categories(update, context, 0)


async def dict_categories_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пагинация списка категорий"""
    page = int(update.callback_query.data.split('_')[-1])
    await _show_dictionary_categories(update, context, page)


async def _show_dictionary_categories(update, context, page=0):
    """Показать список категорий с пагинацией"""
    lang = context.user_data.get('dict_language')
    topics_with_counts = await get_all_topics_with_counts(language_from=lang)
    context.user_data['dict_categories_cache'] = [t for t, _ in topics_with_counts]
    context.user_data.pop('dict_back_to', None)
    
    total = len(topics_with_counts)
    per_page = 10
    start = page * per_page
    end = start + per_page
    current = topics_with_counts[start:end]
    
    keyboard = []
    for idx, (topic, count) in enumerate(current, start=start):
        # При фильтре по языку каждая карточка = одно слово, делить на 2 не нужно
        display_count = count if lang else count // 2
        keyboard.append([InlineKeyboardButton(
            f"📂 {topic} (Слов: {display_count})",
            callback_data=f"dict_cat_view_{idx}_0"
        )])
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"dict_cat_list_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"dict_cat_list_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("🔍 Найти слово", callback_data="dict_search")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад к выбору словаря", callback_data="dictionary_main")])
    keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "📂 <b>Словарь по категориям</b>\n\nВыберите категорию:"
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
        except Exception:
            # Если текущее сообщение — фото (нельзя редактировать), пересоздаём
            try:
                await update.callback_query.delete_message()
            except Exception:
                pass
            await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


async def dict_category_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр слов в выбранной категории (вход/пагинация)"""
    parts = update.callback_query.data.split('_')
    idx = int(parts[3])
    page = int(parts[4]) if len(parts) > 4 else 0
    
    cache = context.user_data.get('dict_categories_cache', [])
    if idx >= len(cache):
        await update.callback_query.edit_message_text("❌ Категория не найдена.")
        return
    
    topic = cache[idx]
    await _show_category_words(update, context, topic, idx, page)


async def _show_category_words(update, context, topic: str, idx: int, page: int = 0):
    """Показать слова выбранной категории"""
    lang = context.user_data.get('dict_language')
    per_page = 5
    words, total = await get_words_by_category(topic, page, per_page, language_from=lang)
    
    # Определяем, нужно ли пересоздавать сообщение (если сейчас на фото)
    on_photo = bool(getattr(update.callback_query.message, 'photo', None))
    
    if not words:
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к категориям", callback_data="dict_cat_list_0")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = f"📭 В категории '{escape(topic)}' нет слов."
        if on_photo:
            try:
                await update.callback_query.delete_message()
            except Exception:
                pass
            await update.callback_query.message.reply_text(msg, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(msg, reply_markup=reply_markup)
        return
    
    context.user_data['dict_back_to'] = f"dict_cat_view_{idx}_{page}"
    
    keyboard = []
    for w in words:
        lang_label = "мокш." if w['language_from'] == 'mdf' else "рус."
        keyboard.append([InlineKeyboardButton(
            f"{w['word']} ({lang_label})",
            callback_data=f"dict_word_{w['card_id']}"
        )])
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"dict_cat_view_{idx}_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"dict_cat_view_{idx}_{page+1}"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к категориям", callback_data="dict_cat_list_0")])
    keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    start_rec = page * per_page + 1
    end_rec = min((page + 1) * per_page, total)
    message = f"📂 <b>{escape(topic)}</b>\n📄 {start_rec}-{end_rec} из {total}\n\n"
    
    if on_photo:
        try:
            await update.callback_query.delete_message()
        except Exception:
            pass
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

# ============================================
# ПОКАЗ СЛОВ ПО БУКВЕ
# ============================================

async def dictionary_letter(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Показать слова по букве с пагинацией"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.pop('dict_back_to', None)
    
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
    start_rec = page * per_page + 1
    end_rec = min((page + 1) * per_page, total)
    
    message = f"📖 <b>Слова на букву '{letter}'</b>\n"
    message += f"📄 {start_rec}-{end_rec} из {total}\n\n"
    
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
    
    keyboard = []
    back_cb = context.user_data.get('dict_back_to')
    if back_cb:
        keyboard.append([InlineKeyboardButton("⬅️ Назад к списку", callback_data=back_cb)])
    else:
        keyboard.append([InlineKeyboardButton("⬅️ Назад к буквам", callback_data=f"dict_lang_{lang_from}")])
    keyboard.append([InlineKeyboardButton("🔍 Найти слово", callback_data="dict_search")])
    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])
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
        except Exception:
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
    context.user_data.pop('dict_back_to', None)
    
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
        
        msg = ("🔍 <b>Слово не найдено</b>\n\n"
               "Попробуйте изменить запрос или связаться с поддержкой, чтобы предложить новое слово.")
        
        if update.callback_query:
            await delete_previous(update)
            await update.callback_query.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
        context.user_data.pop('awaiting_dict_search', None)
        return
    
    reply_markup = await get_search_results_keyboard(results, query_text, page, total, per_page)
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    start_rec = page * per_page + 1
    end_rec = min((page + 1) * per_page, total)
    
    message = f"🔍 <b>Результаты поиска</b>\n"
    message += f"📄 {start_rec}-{end_rec} из {total}\n\n"
    
    if update.callback_query:
        await delete_previous(update)
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')
    
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
    context.user_data.pop('express_mode', None)
    context.user_data.pop('express_queue', None)
    
    from database.cards import get_words_count_by_topic
    count = await get_words_count_by_topic(topic)
    context.user_data['topic_words_count'] = count
    
    await query.edit_message_text(
        f"✅ Выбрана тематика: <b>{escape(topic)}</b>\n\nНачинаю изучение...",
        parse_mode='HTML'
    )
    
    import asyncio
    await asyncio.sleep(0.5)
    
    from .study import study
    await study(update, context)