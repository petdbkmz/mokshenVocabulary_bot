import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.progress import update_progress, mark_hint_used
from database.users import update_activity, reset_reminder_flag
from database.cards import (
    get_random_card_excluding, get_card_by_id, get_card_tuple_by_id,
    get_hints_for_card, get_multiple_choice_hints,
    get_words_count_by_topic, reset_user_progress_by_topic,
    get_express_cards,
)
from bot.keyboards import (
    get_study_keyboard, get_study_without_hint_keyboard,
    get_topics_keyboard, get_back_button
)
from bot.utils import delete_previous, is_no_hint_type, format_card_info
from config import NO_HINT_TYPES, EXPRESS_MODE_SIZE

# ============================================
# ОСНОВНАЯ ФУНКЦИЯ ИЗУЧЕНИЯ
# ============================================

async def study(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать случайную карточку (или продолжить express-mode)"""
    user_id = update.effective_user.id
    
    # Очищаем транзитное состояние (НЕ трогаем express_*)
    for key in (
        'awaiting_support_message', 'replying_to', 'awaiting_add_word',
        'awaiting_delete_word', 'awaiting_edit', 'awaiting_search',
        'awaiting_notification', 'awaiting_thanks_edit', 'awaiting_dict_search',
    ):
        context.user_data.pop(key, None)
    
    await update_activity(user_id)
    await reset_reminder_flag(user_id)
    
    # === EXPRESS-MODE: продолжаем, если активен ===
    if context.user_data.get('express_mode'):
        await show_next_express_card(update, context)
        return
    
    # === Обычный режим ===
    if 'selected_topic' not in context.user_data:
        await show_topic_selection(update, context)
        return
    
    topic = context.user_data['selected_topic']
    last_card_id = context.user_data.get('last_card_id', None)
    
    card = await get_random_card_excluding(
        user_id, 
        topic if topic != "Все слова" else None, 
        last_card_id
    )
    
    if not card:
        await show_topic_completed(update, context, topic)
        return
    
    card_data = await prepare_card_data(card)
    context.user_data['current_card'] = card_data
    context.user_data['last_card_id'] = card_data['card_id']
    
    await update_progress(user_id, card_data['card_id'], None)
    await show_card(update, user_id, card_data)

# ============================================
# EXPRESS-MODE
# ============================================

async def start_express(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запустить экспресс-режим (10 случайных слов)"""
    user_id = update.effective_user.id
    
    # ВАЖНО: не трогаем selected_topic и last_card_id — экспресс не должен
    # влиять на ранее начатый процесс обучения.
    # Сбрасываем только текущую карточку и (пере)запускаем express-сессию.
    for k in ('current_card', 'express_mode', 'express_queue', 'express_total', 'express_shown'):
        context.user_data.pop(k, None)
    
    cards = await get_express_cards(user_id, EXPRESS_MODE_SIZE)
    
    if not cards:
        msg = ("❌ Нет доступных слов для экспресс-режима.\n"
               "Возможно, все слова уже выучены или в базе пока нет слов "
               "подходящего типа.")
        if update.callback_query:
            await update.callback_query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)
        return
    
    context.user_data['express_mode'] = True
    context.user_data['express_queue'] = list(cards)
    context.user_data['express_total'] = len(cards)
    context.user_data['express_shown'] = 0
    
    await update_activity(user_id)
    await reset_reminder_flag(user_id)
    await show_next_express_card(update, context)

async def show_next_express_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать следующую карточку из экспресс-очереди"""
    user_id = update.effective_user.id
    queue = context.user_data.get('express_queue', [])
    total = context.user_data.get('express_total', 0)
    shown = context.user_data.get('express_shown', 0)
    
    if not queue or shown >= total:
        await show_express_complete(update, context)
        return
    
    card_id = queue.pop(0)
    context.user_data['express_queue'] = queue
    context.user_data['express_shown'] = shown + 1
    
    card = await get_card_tuple_by_id(card_id)
    if not card:
        # Карточка могла быть удалена — берём следующую
        await show_next_express_card(update, context)
        return
    
    card_data = await prepare_card_data(card)
    context.user_data['current_card'] = card_data
    await update_progress(user_id, card_data['card_id'], None)
    await show_card(update, user_id, card_data)

async def show_express_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспресс-режим завершён"""
    total = context.user_data.get('express_total', 0)
    saved_topic = context.user_data.get('selected_topic')  # ← читаем ДО очистки
    
    for k in ('express_mode', 'express_queue', 'express_total', 'express_shown', 'current_card'):
        context.user_data.pop(k, None)
    
    keyboard = []
    if saved_topic:
        keyboard.append([InlineKeyboardButton(
            f"📚 Продолжить: {saved_topic}",
            callback_data="continue_study"
        )])
    else:
        keyboard.append([InlineKeyboardButton(
            "📚 К выбору тематики",
            callback_data="back_to_topics"
        )])
    keyboard.append([InlineKeyboardButton("🔄 Ещё раз", callback_data="express_mode")])
    keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = (f"🎉 <b>Экспресс-режим завершён!</b>\n\n"
               f"📊 Вы прошли {total} слов.\n\n"
               f"Продолжайте в том же духе! 💪")
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def prepare_card_data(card_tuple) -> dict:
    """Преобразовать кортеж из БД в словарь"""
    (card_id, word, translation, lang_from, lang_to, 
     image_url, card_type, wrong_hints, topics, 
     alt_trans, first_letter, created_by, created_at, updated_at) = card_tuple
    
    if wrong_hints:
        try:
            wrong_hints = json.loads(wrong_hints)
        except Exception:
            wrong_hints = []
    if topics:
        topics = topics.split(',')
    if alt_trans:
        alt_trans = alt_trans.split(',')
    
    return {
        'card_id': card_id,
        'word': word,
        'translation': translation,
        'lang_from': lang_from,
        'lang_to': lang_to,
        'image_url': image_url,
        'card_type': card_type,
        'wrong_hints': wrong_hints or [],
        'topics': topics or [],
        'alternative_translations': alt_trans or [],
        'hint_shown': False
    }

async def show_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Показать выбор тематики"""
    reply_markup = await get_topics_keyboard(page)
    
    from database.cards import get_all_topics_with_counts
    topics_with_counts = await get_all_topics_with_counts()
    total = len(topics_with_counts)
    total_words = sum(count for _, count in topics_with_counts)
    
    message = f"📚 <b>Выбери тематику для изучения</b>\n\n"
    message += f"📝 Всего тематик: {total}\n"
    message += f"📚 Всего слов: {total_words // 2}"
    
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

async def show_topic_completed(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str):
    """Показать сообщение о завершении тематики"""
    keyboard = [
        [InlineKeyboardButton("🔄 Выучить ещё раз", callback_data=f"reset_topic_{topic}")],
        [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"🎉 Поздравляю! Ты выучил все слова по тематике '{topic}'!"
    
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
    
    context.user_data.pop('selected_topic', None)

async def show_card(update: Update, user_id: int, card_data: dict):
    """Показать карточку с кнопками"""
    card_id = card_data['card_id']
    word = card_data['word']
    card_type = card_data['card_type']
    lang_from = card_data['lang_from']
    
    if is_no_hint_type(card_type):
        await show_choice_card(update, user_id, card_id, word, card_data['translation'])
        return
    
    if lang_from == 'ru':
        message = f"Переведите слово с русского:\n<b>{word}</b>?"
    else:
        message = f"Переведите слово на русский:\n<b>{word}</b>?"
    
    reply_markup = get_study_keyboard(card_id)
    
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

async def show_choice_card(update, user_id: int, card_id: int, word: str, correct_answer: str):
    """Показать карточку с вариантами ответа"""
    hints = await get_multiple_choice_hints(card_id, correct_answer)
    
    keyboard = []
    for hint_text, is_correct in hints:
        callback_data = f"choice_{card_id}_{'correct' if is_correct else 'wrong'}"
        keyboard.append([InlineKeyboardButton(hint_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data=f"skip_{card_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"Выбери правильный перевод для:\n<b>{word}</b>"
    
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

# ============================================
# ОБРАБОТЧИКИ КНОПОК
# ============================================

async def handle_hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку 'Подсказка'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    card_id = int(query.data.split("_")[1])
    
    if 'current_card' not in context.user_data:
        await delete_previous(update)
        await query.message.reply_text("❌ Карточка не найдена. Начни заново /study")
        return
    
    card = context.user_data['current_card']
    
    if card['card_id'] != card_id:
        await delete_previous(update)
        await query.message.reply_text("❌ Это не текущая карточка. Начни заново /study")
        return
    
    if is_no_hint_type(card['card_type']):
        await delete_previous(update)
        await query.message.reply_text("❌ Для этого типа карточек подсказка не требуется, выбери вариант ниже.")
        return
    
    card['hint_shown'] = True
    context.user_data['current_card'] = card
    await mark_hint_used(user_id, card_id)
    
    await delete_previous(update)
    
    if card['image_url']:
        await show_image_hint(update, query, card_id, card['image_url'])
        return
    
    await show_word_choice(update, query, user_id, card_id, card['word'], card['translation'], card['card_type'], card['lang_to'])

async def show_image_hint(update, query, card_id: int, image_url: str):
    """Показать картинку-подсказку"""
    keyboard = [
        [InlineKeyboardButton("⏭️ Пропустить", callback_data=f"skip_{card_id}")],
        [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"🖼️ <b>Подсказка:</b>\n\nВот картинка, которая поможет вспомнить слово."
    
    try:
        await query.message.reply_photo(
            photo=image_url,
            caption=message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception:
        await query.message.reply_text(
            "⚠️ Не удалось загрузить картинку. Попробуйте ещё раз.",
            reply_markup=reply_markup
        )

async def show_word_choice(update, query, user_id: int, card_id: int, word: str, correct_answer: str, card_type: str, language_to: str):
    """Показать варианты ответа для обычных слов"""
    hints = await get_hints_for_card(card_id, correct_answer, card_type, language_to)
    
    keyboard = []
    for hint_text, is_correct in hints:
        callback_data = f"choice_{card_id}_{'correct' if is_correct else 'wrong'}"
        keyboard.append([InlineKeyboardButton(hint_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data=f"skip_{card_id}")])
    keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"Выбери правильный перевод для слова:\n<b>{word}</b>"
    
    await query.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку 'Пропустить'"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    card_id = int(query.data.split("_")[1])
    chat_id = query.message.chat_id
    
    if 'current_card' not in context.user_data:
        await delete_previous(update)
        await query.message.reply_text("❌ Карточка не найдена. Начни заново /study")
        return
    
    card = context.user_data['current_card']
    
    if card['card_id'] != card_id:
        await delete_previous(update)
        await query.message.reply_text("❌ Это не текущая карточка. Начни заново /study")
        return
    
    await update_progress(user_id, card_id, False)
    
    card_info = await get_card_by_id(card_id)
    
    await delete_previous(update)
    
    if card_info:
        await query.message.reply_text(
            f"⏭️ Пропущено!\nПравильный ответ: <tg-spoiler>{card_info['translation']}</tg-spoiler>",
            parse_mode='HTML'
        )
    
    context.user_data.pop('current_card', None)
    
    await asyncio.sleep(1.5)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="⏳ Загружаю следующее слово..."
    )
    
    await study(update, context)

async def choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора варианта"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data.split('_')
    chat_id = query.message.chat_id
    
    if len(data) >= 3:
        card_id = int(data[1])
        result = data[2]
        
        card_info = await get_card_by_id(card_id)
        if not card_info:
            await delete_previous(update)
            await query.message.reply_text("❌ Карточка не найдена")
            return
        
        await delete_previous(update)
        
        if result == 'correct':
            await update_progress(user_id, card_id, True)
            await query.message.reply_text(
                f"✅ Правильно! Отлично! 🎉",
                parse_mode='HTML'
            )
        else:
            await update_progress(user_id, card_id, False)
            await query.message.reply_text(
                f"❌ Неверно!\nПравильный ответ: <tg-spoiler>{card_info['translation']}</tg-spoiler>",
                parse_mode='HTML'
            )
        
        context.user_data.pop('current_card', None)
        
        await asyncio.sleep(1.5)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏳ Загружаю следующее слово..."
        )
        
        await study(update, context)

async def reset_topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбросить прогресс по тематике"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    topic = query.data.replace('reset_topic_', '')
    
    count = await reset_user_progress_by_topic(user_id, topic)
    
    if count > 0:
        await query.edit_message_text(
            f"🔄 Прогресс по тематике <b>{topic}</b> сброшен!\n"
            f"Сброшено: {count} слов\n\n"
            "Начинаю заново...",
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(
            f"🔄 Прогресс по тематике <b>{topic}</b> сброшен!\n\n"
            "Начинаю заново...",
            parse_mode='HTML'
        )
    
    await asyncio.sleep(1.5)
    context.user_data['selected_topic'] = topic
    await study(update, context)

# ============================================
# ОБРАБОТКА ТЕКСТОВЫХ ОТВЕТОВ
# ============================================

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка письменного ответа пользователя"""
    user_id = update.effective_user.id
    user_answer = update.message.text.strip().lower()
    chat_id = update.message.chat_id
    
    await update_activity(user_id)
    await reset_reminder_flag(user_id)
    
    if 'current_card' not in context.user_data:
        await update.message.reply_text("Сначала начни изучение командой /study")
        return
    
    card = context.user_data['current_card']
    correct_answer = card['translation'].lower()
    
    alt_translations = card.get('alternative_translations', [])
    alt_translations_lower = [t.lower().strip() for t in alt_translations] if alt_translations else []
    
    is_correct = (user_answer == correct_answer) or (user_answer in alt_translations_lower)
    
    if is_correct:
        await update_progress(user_id, card['card_id'], True)
        await update.message.reply_text(
            f"✅ Правильно! 🎉",
            parse_mode='HTML'
        )
    else:
        await update_progress(user_id, card['card_id'], False)
        await update.message.reply_text(
            f"❌ Неверно!\nПравильный ответ: <tg-spoiler>{card['translation']}</tg-spoiler>",
            parse_mode='HTML'
        )
    
    context.user_data.pop('current_card', None)
    
    await asyncio.sleep(1.5)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="⏳ Загружаю следующее слово..."
    )
    
    await study(update, context)