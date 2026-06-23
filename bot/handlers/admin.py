import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.users import (
    is_editor, set_editor, get_all_editors, 
    get_all_users_paginated, get_user_id_by_username
)
from database.progress import clear_user_stats
from database.support import get_pending_messages
from database.cards import (
    get_all_cards, search_cards, get_card_by_id, 
    update_card, delete_card, add_card,
    get_table_data, format_table_message
)
from database.support import get_pending_messages
from .start import start
from database.progress import get_user_stats
from bot.keyboards import (
    get_admin_panel_keyboard, get_edit_card_keyboard,
    get_confirm_delete_keyboard, get_confirm_clear_stats_keyboard,
    get_admin_cards_pagination_keyboard, get_users_pagination_keyboard,
    get_back_to_admin_button
)
from bot.utils import delete_previous, parse_wrong_hints, validate_card_data
from config import ADMIN_ID, CARD_TYPES
from .start import start

# ============================================
# ДЕКОРАТОР ДЛЯ ПРОВЕРКИ ПРАВ
# ============================================

def editor_required(func):
    """Декоратор для проверки прав редактора"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not await is_editor(user_id):
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ У вас нет прав для выполнения этой команды.\n"
                    "Только редакторы могут управлять словами."
                )
            else:
                await update.message.reply_text(
                    "❌ У вас нет прав для выполнения этой команды.\n"
                    "Только редакторы могут управлять словами."
                )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ============================================
# АДМИН-ПАНЕЛЬ
# ============================================

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать админ-панель"""
    query = update.callback_query
    if query:
        await query.answer()
    
    reply_markup = get_admin_panel_keyboard()
    
    await delete_previous(update)
    if query:
        await query.message.reply_text(
            "⚙️ <b>Админ-панель</b>\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "⚙️ <b>Админ-панель</b>\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

# ============================================
# УПРАВЛЕНИЕ РЕДАКТОРАМИ
# ============================================

async def manage_editors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление редакторами"""
    query = update.callback_query
    await query.answer()
    
    editors = await get_all_editors()
    
    message = "👥 <b>Редакторы</b>\n\n"
    if editors:
        for editor in editors:
            user_id, username, first_name, last_name = editor
            name = first_name or last_name or username or str(user_id)
            message += f"• {name} (ID: {user_id})\n"
    else:
        message += "Нет редакторов.\n"
    
    message += f"\n<b>Команды для управления:</b>\n"
    message += f"<code>/add_editor ID</code> - добавить редактора\n"
    message += f"<code>/remove_editor ID</code> - удалить редактора\n\n"
    message += f"<i>Чтобы узнать ID пользователя, попроси его написать @userinfobot</i>"
    
    reply_markup = get_back_to_admin_button()
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

@editor_required
async def add_editor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить редактора"""
    try:
        user_id = int(context.args[0])
        await set_editor(user_id, True)
        await update.message.reply_text(f"✅ Пользователь {user_id} назначен редактором!")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Использование: /add_editor ID_пользователя")

@editor_required
async def remove_editor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить редактора"""
    try:
        user_id = int(context.args[0])
        if user_id == ADMIN_ID:
            await update.message.reply_text("❌ Нельзя удалить главного администратора!")
            return
        await set_editor(user_id, False)
        await update.message.reply_text(f"✅ Пользователь {user_id} лишён прав редактора!")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Использование: /remove_editor ID_пользователя")

# ============================================
# СПИСОК ПОЛЬЗОВАТЕЛЕЙ
# ============================================

@editor_required
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Показать список пользователей с пагинацией (от новых к старым)"""
    query = update.callback_query
    if query:
        await query.answer()
    
    per_page = 10
    users, total = await get_all_users_paginated(page, per_page)
    
    if not users:
        if query:
            await query.edit_message_text("👥 Пользователей пока нет.")
        else:
            await update.message.reply_text("👥 Пользователей пока нет.")
        return
    
    message = f"👥 <b>Список пользователей</b>\n"
    message += f"📊 Всего пользователей: <b>{total}</b>\n\n"
    
    start = page * per_page + 1
    message += f"📄 <i>Новые сверху (стр. {page + 1})</i>\n\n"
    
    for idx, user in enumerate(users, start=start):
        name = user['first_name'] if user['first_name'] != 'Нет' else ''
        if user['last_name'] != 'Нет':
            name += f" {user['last_name']}"
        name = name.strip() or 'Без имени'
        username = f"@{user['username']}" if user['username'] != 'Нет' else 'Нет username'
        editor = "⭐ Редактор" if user['is_editor'] else ""
        message += f"{idx}. {name}\n"
        message += f"   🆔 {user['user_id']}\n"
        message += f"   📛 {username}\n"
        if editor:
            message += f"   {editor}\n"
        if user['created_at']:
            created = user['created_at'][:10] if isinstance(user['created_at'], str) else str(user['created_at'])[:10]
            message += f"   📅 {created}\n"
        message += "\n"
    
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    reply_markup = get_users_pagination_keyboard(page, total_pages)
    
    if query:
        await query.edit_message_text(
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

async def users_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка пагинации списка пользователей"""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split('_')[2])
    await list_users(update, context, page)

# ============================================
# УПРАВЛЕНИЕ КАРТОЧКАМИ
# ============================================

@editor_required
async def list_cards(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Показать список карточек с пагинацией"""
    query = update.callback_query
    if query:
        await query.answer()
    
    limit = 5
    offset = page * limit
    
    cards = await get_all_cards(limit, offset)
    
    if not cards:
        if query:
            await query.edit_message_text("📭 Слова не найдены.")
        else:
            await update.message.reply_text("📭 Слова не найдены.")
        return
    
    message = f"📋 <b>Список слов (стр. {page + 1})</b>\n\n"
    for idx, card in enumerate(cards, start=offset + 1):
        from config import CARD_TYPES
        card_type_display = CARD_TYPES.get(card['card_type'], card['card_type'])
        message += f"{idx}. <b>{card['word']}</b> → {card['translation']}\n"
        message += f"   Тип: {card_type_display}, ID: {card['card_id']}\n"
        if card['image_url']:
            message += f"   🖼️ Есть картинка\n"
        if card.get('topics'):
            message += f"   📚 Тематики: {', '.join(card['topics'])}\n"
    
    reply_markup = get_admin_cards_pagination_keyboard(cards, page, limit)
    
    if query:
        await query.edit_message_text(
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

@editor_required
async def handle_add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка добавления слова"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if text.lower() == '/cancel':
        context.user_data.pop('awaiting_add_word', None)
        await update.message.reply_text("❌ Добавление слова отменено.")
        return
    
    parts = text.split('|')
    if len(parts) < 5:
        types_list = "\n".join([f"  • {k} - {v}" for k, v in CARD_TYPES.items()])
        await update.message.reply_text(
            f"❌ Неверный формат!\n"
            "Нужно: слово|перевод|язык_откуда|язык_куда|тип\n"
            "Языки: mdf (мокшанский), ru (русский)\n"
            f"Типы: {', '.join(CARD_TYPES.keys())}\n"
            "Пример: кал|рыба|mdf|ru|noun\n\n"
            f"<b>Доступные типы:</b>\n{types_list}\n\n"
            "Для отмены отправьте /cancel",
            parse_mode='HTML'
        )
        return
    
    try:
        word = parts[0].strip()
        translation = parts[1].strip()
        language_from = parts[2].strip()
        language_to = parts[3].strip()
        card_type = parts[4].strip()
        image_url = parts[5].strip() if len(parts) > 5 and parts[5].strip() else None
        wrong_hints = []
        topics = []
        alt_trans = []
        
        # Парсим неправильные варианты
        if len(parts) > 6 and parts[6].strip():
            wrong_hints = parse_wrong_hints(parts[6].strip())
        
        # Парсим тематики
        if len(parts) > 7 and parts[7].strip():
            topics = [t.strip() for t in parts[7].split(',') if t.strip()]
        
        # Парсим альтернативные переводы
        if len(parts) > 8 and parts[8].strip():
            alt_trans = [t.strip() for t in parts[8].split(',') if t.strip()]
        
        # Валидация
        is_valid, error = validate_card_data(word, translation, language_from, language_to, card_type)
        if not is_valid:
            await update.message.reply_text(f"❌ {error}")
            return
        
        card_id = await add_card(
            word, translation, language_from, language_to,
            card_type, user_id, image_url, wrong_hints, topics, alt_trans
        )
        
        await update.message.reply_text(
            f"✅ Слово <b>{word}</b> добавлено! (ID: {card_id})",
            parse_mode='HTML'
        )
        
        context.user_data.pop('awaiting_add_word', None)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

@editor_required
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка поиска слов (админский)"""
    text = update.message.text.strip()
    
    if text.lower() == '/cancel':
        context.user_data.pop('awaiting_search', None)
        await update.message.reply_text("❌ Поиск отменён.")
        return
    
    results = await search_cards(text)
    
    if not results:
        await update.message.reply_text("🔍 Ничего не найдено.")
    else:
        message = f"🔍 <b>Результаты поиска ({len(results)})</b>\n\n"
        for i, card in enumerate(results[:20], 1):
            from config import CARD_TYPES
            card_type_display = CARD_TYPES.get(card['card_type'], card['card_type'])
            message += f"{i}. <b>{card['word']}</b> → {card['translation']}\n"
            message += f"   Тип: {card_type_display}, ID: {card['card_id']}\n"
            if card.get('topics'):
                message += f"   📚 Тематики: {', '.join(card['topics'])}\n"
        
        if len(results) > 20:
            message += f"\n... и ещё {len(results) - 20} результатов"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    context.user_data.pop('awaiting_search', None)

@editor_required
async def handle_delete_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка удаления слова по ID"""
    text = update.message.text.strip()
    
    if text.lower() == '/cancel':
        context.user_data.pop('awaiting_delete_word', None)
        await update.message.reply_text("❌ Удаление отменено.")
        return
    
    try:
        card_id = int(text)
        card = await get_card_by_id(card_id)
        
        if not card:
            await update.message.reply_text(f"❌ Слово с ID {card_id} не найдено.")
            return
        
        reply_markup = get_confirm_delete_keyboard(card_id)
        
        await update.message.reply_text(
            f"⚠️ <b>ВНИМАНИЕ!</b>\n\n"
            f"Вы уверены, что хотите удалить слово:\n"
            f"<b>{card['word']}</b> → {card['translation']}\n"
            f"ID: {card_id}\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        context.user_data.pop('awaiting_delete_word', None)
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, отправь число (ID слова).")

# ============================================
# РЕДАКТИРОВАНИЕ КАРТОЧЕК
# ============================================

async def handle_edit_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий редактирования"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("edit_select_"):
        card_id = int(data.split("_")[2])
        card = await get_card_by_id(card_id)
        
        if not card:
            await query.edit_message_text("❌ Карточка не найдена")
            return
        
        context.user_data['editing_card_id'] = card_id
        reply_markup = await get_edit_card_keyboard(card_id)
        
        from config import CARD_TYPES
        card_type_display = CARD_TYPES.get(card['card_type'], card['card_type'])
        image_status = "🖼️ Есть" if card['image_url'] else "❌ Нет"
        topics_display = ', '.join(card['topics']) if card.get('topics') else '❌ Нет'
        alt_trans_display = ', '.join(card['alternative_translations']) if card.get('alternative_translations') else '❌ Нет'
        
        await query.edit_message_text(
            f"✏️ <b>Редактирование</b>\n\n"
            f"Слово: {card['word']}\n"
            f"Перевод: {card['translation']}\n"
            f"Тип: {card_type_display}\n"
            f"Язык: {card['language_from']} → {card['language_to']}\n"
            f"Картинка: {image_status}\n"
            f"Тематики: {topics_display}\n"
            f"Альт. переводы: {alt_trans_display}\n"
            f"ID: {card['card_id']}\n\n"
            f"Выберите поле для редактирования:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    elif data.startswith("edit_field_"):
        parts = data.split("_")
        field = parts[2]
        card_id = int(parts[3])
        
        context.user_data['editing_field'] = field
        context.user_data['editing_card_id'] = card_id
        
        field_names = {
            'word': 'слово',
            'translation': 'перевод',
            'type': 'тип',
            'image': 'ссылку на картинку',
            'hints': 'неправильные варианты (в кавычках, через запятую)',
            'topics': 'тематики (через запятую)',
            'alt_trans': 'альтернативные переводы (через запятую)'
        }
        
        hints = ""
        if field == 'type':
            hints = f"\n\nДоступные типы: {', '.join(CARD_TYPES.keys())}"
        
        await query.edit_message_text(
            f"✏️ Введите новое значение для поля <b>{field_names.get(field, field)}</b>:{hints}\n\n"
            "Для отмены отправьте /cancel",
            parse_mode='HTML'
        )
        context.user_data['awaiting_edit'] = True
    
    elif data.startswith("edit_delete_"):
        card_id = int(data.split("_")[2])
        reply_markup = get_confirm_delete_keyboard(card_id)
        
        await query.edit_message_text(
            "⚠️ <b>ВНИМАНИЕ!</b>\n\n"
            "Вы уверены, что хотите удалить эту карточку?\n"
            "Это действие нельзя отменить!",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def handle_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка редактирования поля карточки"""
    text = update.message.text.strip()
    card_id = context.user_data.get('editing_card_id')
    field = context.user_data.get('editing_field')
    
    if not card_id or not field:
        await update.message.reply_text("❌ Ошибка: не выбрана карточка для редактирования.")
        return
    
    if text.lower() == '/cancel':
        context.user_data.clear()
        await update.message.reply_text("❌ Редактирование отменено.")
        return
    
    try:
        if field == 'word':
            await update_card(card_id, word=text)
        elif field == 'translation':
            await update_card(card_id, translation=text)
        elif field == 'type':
            if text not in CARD_TYPES:
                await update.message.reply_text(f"❌ Неверный тип. Доступны: {', '.join(CARD_TYPES.keys())}")
                return
            await update_card(card_id, card_type=text)
        elif field == 'image':
            if text.lower() in ['удалить', 'нет', 'none', 'null']:
                await update_card(card_id, image_url=None)
            else:
                await update_card(card_id, image_url=text)
        elif field == 'hints':
            wrong_hints = parse_wrong_hints(text)
            await update_card(card_id, wrong_hints=wrong_hints)
        elif field == 'topics':
            topics = [t.strip() for t in text.split(',') if t.strip()]
            await update_card(card_id, topics=topics)
        elif field == 'alt_trans':
            alt_trans = [t.strip() for t in text.split(',') if t.strip()]
            await update_card(card_id, alternative_translations=alt_trans)
        
        await update.message.reply_text("✅ Карточка обновлена!")
        context.user_data.clear()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def confirm_delete_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления карточки"""
    query = update.callback_query
    await query.answer()
    
    card_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    
    card = await get_card_by_id(card_id)
    
    if await delete_card(card_id, user_id):
        await query.edit_message_text(f"✅ Карточка <b>{card['word']}</b> удалена!", parse_mode='HTML')
    else:
        await query.edit_message_text("❌ Ошибка при удалении карточки")

# ============================================
# СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ (АДМИН)
# ============================================

@editor_required
async def handle_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя по ID или username"""
    user_id_input = update.message.text.strip()
    
    if user_id_input.lower() == '/cancel':
        context.user_data.pop('awaiting_user_stats', None)
        await update.message.reply_text("❌ Операция отменена.")
        return
    
    try:
        try:
            target_user_id = int(user_id_input)
        except ValueError:
            target_user_id = await get_user_id_by_username(user_id_input)
            if not target_user_id:
                await update.message.reply_text(
                    f"❌ Пользователь с username '{user_id_input}' не найден.\n"
                    "Попробуй использовать ID или другой username."
                )
                return
        
        stats = await get_user_stats(target_user_id)
        
        from database.db import get_db
        db = await get_db()
        async with db.execute('SELECT first_name, username FROM users WHERE user_id = ?',
                            (target_user_id,)) as cursor:
            user_info = await cursor.fetchone()
        
        user_name = user_info[0] if user_info else str(target_user_id)
        username = user_info[1] if user_info and user_info[1] else "Нет"
        
        from bot.utils import format_user_stats
        message = format_user_stats(stats, user_name, username)
        
        await update.message.reply_text(message, parse_mode='HTML')
        context.user_data.pop('awaiting_user_stats', None)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

@editor_required
async def handle_clear_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистить статистику пользователя по ID или username"""
    user_id_input = update.message.text.strip()
    
    if user_id_input.lower() == '/cancel':
        context.user_data.pop('awaiting_clear_stats', None)
        await update.message.reply_text("❌ Операция отменена.")
        return
    
    try:
        try:
            target_user_id = int(user_id_input)
        except ValueError:
            target_user_id = await get_user_id_by_username(user_id_input)
            if not target_user_id:
                await update.message.reply_text(
                    f"❌ Пользователь с username '{user_id_input}' не найден."
                )
                return
        
        from database.db import get_db
        db = await get_db()
        async with db.execute('SELECT first_name, username FROM users WHERE user_id = ?',
                            (target_user_id,)) as cursor:
            user_info = await cursor.fetchone()
        
        user_name = user_info[0] if user_info else str(target_user_id)
        
        reply_markup = get_confirm_clear_stats_keyboard(target_user_id)
        
        await update.message.reply_text(
            f"⚠️ <b>ВНИМАНИЕ!</b>\n\n"
            f"Вы уверены, что хотите очистить статистику пользователя:\n"
            f"<b>{user_name}</b> (ID: {target_user_id})\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        context.user_data.pop('awaiting_clear_stats', None)
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, отправь ID или username пользователя.")

async def confirm_clear_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение очистки статистики"""
    query = update.callback_query
    await query.answer()
    
    target_user_id = int(query.data.split("_")[2])
    
    success = await clear_user_stats(target_user_id)
    
    if success:
        await query.edit_message_text(f"✅ Статистика пользователя {target_user_id} очищена!", parse_mode='HTML')
    else:
        await query.edit_message_text(f"❌ Ошибка при очистке статистики пользователя {target_user_id}", parse_mode='HTML')

# ============================================
# ПРОСМОТР ТАБЛИЦ БД
# ============================================

@editor_required
async def tables_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список всех таблиц в базе данных"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
        else:
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    import sqlite3
    from config import DB_NAME
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        conn.close()
        
        if not tables:
            if update.callback_query:
                await update.callback_query.edit_message_text("📭 В базе данных нет таблиц.")
            else:
                await update.message.reply_text("📭 В базе данных нет таблиц.")
            return
        
        keyboard = []
        for table in tables:
            table_name = table[0]
            if table_name.startswith('sqlite_'):
                continue
            keyboard.append([InlineKeyboardButton(f"📋 {table_name}", callback_data=f"view_table_{table_name}_0")])
        
        keyboard.append([InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "📚 <b>Таблицы базы данных</b>\n\n"
            f"Всего таблиц: {len(tables)}\n"
            "Нажми на кнопку, чтобы посмотреть содержимое:"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
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
            
    except Exception as e:
        error_msg = f"❌ Ошибка: {e}"
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def view_table_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку с названием таблицы"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    parts = query.data.split('_')
    if len(parts) >= 4:
        table_name = '_'.join(parts[2:-1])
        page = int(parts[-1])
    else:
        table_name = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 0
    
    data = await get_table_data(table_name, page=page, per_page=20)
    message = await format_table_message(data)
    
    total_pages = (data['total'] + data['per_page'] - 1) // data['per_page'] if data['total'] > 0 else 1
    
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
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def refresh_table_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновить содержимое таблицы"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    parts = query.data.split('_')
    if len(parts) >= 4:
        table_name = '_'.join(parts[2:-1])
        page = int(parts[-1])
    else:
        table_name = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 0
    
    await view_table_callback(update, context)

async def show_tables_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к списку таблиц"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    # Просто вызываем tables_command, но с callback_query
    await tables_command(update, context)

# ============================================
# РАССЫЛКА УВЕДОМЛЕНИЙ
# ============================================

@editor_required
async def send_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс рассылки уведомления"""
    query = update.callback_query
    await query.answer()
    
    await delete_previous(update)
    await query.message.reply_text(
        "📢 <b>Отправка уведомления</b>\n\n"
        "Введите текст уведомления, который получат все пользователи бота.\n"
        "Для отмены отправьте /cancel",
        parse_mode='HTML'
    )
    context.user_data['awaiting_notification'] = True

@editor_required
async def handle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста уведомления и рассылка"""
    user_id = update.effective_user.id
    
    if not context.user_data.get('awaiting_notification'):
        return
    
    text = update.message.text.strip()
    
    if text.lower() == '/cancel':
        context.user_data.pop('awaiting_notification', None)
        await update.message.reply_text("❌ Отправка уведомления отменена.")
        return
    
    from database.db import get_db
    db = await get_db()
    async with db.execute('SELECT user_id FROM users') as cursor:
        users = await cursor.fetchall()
    
    await update.message.reply_text(f"⏳ Начинаю рассылку {len(users)} пользователям...")
    
    sent = 0
    failed = 0
    
    import asyncio
    for user_row in users:
        user_id_to_send = user_row[0]
        try:
            await context.bot.send_message(
                chat_id=user_id_to_send,
                text=text,
                parse_mode='HTML'
            )
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await update.message.reply_text(
        f"✅ Рассылка завершена!\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}"
    )
    
    context.user_data.pop('awaiting_notification', None)

# ============================================
# ОБРАБОТКА ДЕЙСТВИЙ В АДМИН-ПАНЕЛИ
# ============================================

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий в админ-панели"""
    query = update.callback_query
    data = query.data

    print(f"🔘 Админ-кнопка: {data}")

    # === ИМПОРТ ===
    if data == "admin_import":
        await query.edit_message_text(
            "📥 Отправьте Excel файл.\n\n"
            "Ожидаемые колонки:\n"
            "1. word - слово (мокшанский/русский)\n"
            "2. translation - перевод\n"
            "3. language_from - язык (mdf/ru)\n"
            "4. language_to - язык перевода\n"
            "5. card_type - тип\n"
            "6. image_url - ссылка на картинку (опц.)\n"
            "7. wrong_hints - неправильные варианты в кавычках (опц.)\n"
            "8. topics - тематики через запятую (опц.)\n"
            "9. alternative_translations - альтернативные переводы через запятую (опц.)\n\n"
            f"Доступные типы: {', '.join(CARD_TYPES.keys())}\n\n"
            "Для отмены отправьте /cancel"
        )
        return

    # === ДОБАВЛЕНИЕ СЛОВА ===
    if data == "admin_add_word":
        types_list = "\n".join([f"  • {k} - {v}" for k, v in CARD_TYPES.items()])
        await query.edit_message_text(
            f"➕ <b>Добавление нового слова</b>\n\n"
            "Отправь сообщение в формате:\n"
            "<code>слово|перевод|язык_откуда|язык_куда|тип|картинка(опц)|неправильные_варианты(опц)|тематики(опц)|альтернативные_переводы(опц)</code>\n\n"
            "Пример для существительного:\n"
            "<code>кал|рыба|mdf|ru|noun</code>\n\n"
            f"<b>Доступные типы:</b>\n{types_list}\n\n"
            "Для отмены отправьте /cancel",
            parse_mode='HTML'
        )
        context.user_data['awaiting_add_word'] = True
        return

    # === ПОИСК СЛОВА ===
    if data == "admin_search":
        await query.edit_message_text(
            "🔍 <b>Поиск слов</b>\n\n"
            "Отправь слово или перевод для поиска.\n\n"
            "Для отмены отправьте /cancel",
            parse_mode='HTML'
        )
        context.user_data['awaiting_search'] = True
        return

    # === СПИСОК ВСЕХ СЛОВ ===
    if data == "admin_list":
        await list_cards(update, context, page=0)
        return

    # === УДАЛЕНИЕ СЛОВА ===
    if data == "admin_delete_word":
        await query.edit_message_text(
            "🗑️ <b>Удаление слова</b>\n\n"
            "Отправь ID слова, которое хочешь удалить.\n"
            "ID можно посмотреть в списке слов.\n\n"
            "Для отмены отправьте /cancel",
            parse_mode='HTML'
        )
        context.user_data['awaiting_delete_word'] = True
        return

    # === УПРАВЛЕНИЕ РЕДАКТОРАМИ ===
    if data == "admin_editors":
        await manage_editors(update, context)
        return

    # === ОБРАЩЕНИЯ В ПОДДЕРЖКУ ===
    if data == "admin_support":
        from database.support import get_pending_messages
        messages = await get_pending_messages()
        if not messages:
            await query.edit_message_text("📭 Нет новых обращений.")
        else:
            await query.edit_message_text(
                f"📩 <b>Новые обращения ({len(messages)})</b>\n\n"
                "Используй команду /check_support для просмотра всех обращений.",
                parse_mode='HTML'
            )
        return

    # === СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ ===
    if data == "admin_user_stats":
        await query.edit_message_text(
            "📊 <b>Статистика пользователя</b>\n\n"
            "Отправь ID или username пользователя, чтобы посмотреть его статистику.\n\n"
            "Для отмены отправьте /cancel",
            parse_mode='HTML'
        )
        context.user_data['awaiting_user_stats'] = True
        return

    # === ОЧИСТКА СТАТИСТИКИ ===
    if data == "admin_clear_stats":
        await query.edit_message_text(
            "🗑️ <b>Очистка статистики</b>\n\n"
            "Отправь ID или username пользователя, чтобы очистить его статистику.\n"
            "⚠️ Это действие нельзя отменить!\n\n"
            "Для отмены отправьте /cancel",
            parse_mode='HTML'
        )
        context.user_data['awaiting_clear_stats'] = True
        return

    # === ПРОСМОТР ТАБЛИЦ БД ===
    if data == "admin_tables":  # <-- ДОБАВЛЕНО!
        await tables_command(update, context)
        return

    # === СПИСОК ПОЛЬЗОВАТЕЛЕЙ ===
    if data == "admin_users":
        await list_users(update, context, page=0)
        return

    # === ВОЗВРАТ В ГЛАВНОЕ МЕНЮ ===
    if data == "back_to_menu":
        from .start import start
        await start(update, context)
        return

    # === НЕИЗВЕСТНАЯ КОМАНДА ===
    await query.edit_message_text("❌ Неизвестная команда в админ-панели.")

# ============================================
# РЕЗЕРВНОЕ КОПИРОВАНИЕ
# ============================================

@editor_required
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создать резервную копию базы данных и отправить админу"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return
    
    await update.message.reply_text("⏳ Создаю резервную копию...")
    
    try:
        import subprocess
        result = subprocess.run(
            ["python", "backup_db.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        
        if result.returncode != 0:
            await update.message.reply_text(f"❌ Ошибка при создании копии:\n{result.stderr}")
            return
        
        backup_dir = "backups"
        if os.path.exists(backup_dir):
            backup_files = sorted([f for f in os.listdir(backup_dir) if f.startswith("words_")])
            if backup_files:
                latest_backup = os.path.join(backup_dir, backup_files[-1])
                await context.bot.send_document(
                    chat_id=user_id,
                    document=open(latest_backup, "rb"),
                    caption=f"📦 Резервная копия базы данных\n\nФайл: {backup_files[-1]}"
                )
                await update.message.reply_text("✅ Резервная копия создана и отправлена!")
                return
        
        await update.message.reply_text("❌ Не удалось найти созданную копию.")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при создании копии: {e}")