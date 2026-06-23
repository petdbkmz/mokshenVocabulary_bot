from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def delete_previous(update: Update):
    """Удалить предыдущее сообщение"""
    if update.callback_query:
        try:
            await update.callback_query.delete_message()
        except:
            pass

async def send_new_message(update: Update, text: str, reply_markup: InlineKeyboardMarkup = None, parse_mode: str = 'HTML'):
    """Отправить новое сообщение вместо редактирования"""
    await delete_previous(update)
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

async def send_message_to_user(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, 
                                reply_markup: InlineKeyboardMarkup = None, parse_mode: str = 'HTML'):
    """Отправить сообщение пользователю по chat_id"""
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )

async def get_user_info(user_id: int) -> dict:
    """Получить информацию о пользователе из БД"""
    from database.db import get_db
    db = await get_db()
    async with db.execute('''
        SELECT user_id, username, first_name, last_name, is_editor, created_at, last_activity
        FROM users WHERE user_id = ?
    ''', (user_id,)) as cursor:
        row = await cursor.fetchone()
        if row:
            return {
                'user_id': row[0],
                'username': row[1] or 'Нет',
                'first_name': row[2] or 'Нет',
                'last_name': row[3] or 'Нет',
                'is_editor': bool(row[4]),
                'created_at': row[5],
                'last_activity': row[6]
            }
        return None

def parse_wrong_hints(text: str) -> list:
    """Парсить неправильные варианты (в кавычках)"""
    wrong_hints = []
    current_hint = []
    in_quotes = False
    
    for char in text:
        if char == '"':
            in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            if current_hint:
                wrong_hints.append(''.join(current_hint).strip().strip('" '))
                current_hint = []
        else:
            current_hint.append(char)
    
    if current_hint:
        wrong_hints.append(''.join(current_hint).strip().strip('" '))
    
    return wrong_hints

def format_card_info(card: dict) -> str:
    """Форматировать информацию о карточке для отображения"""
    from config import CARD_TYPES
    
    card_type_display = CARD_TYPES.get(card['card_type'], card['card_type'])
    lang_label = "мокш." if card['language_from'] == 'mdf' else "рус."
    
    message = f"📖 <b>{card['word']}</b> — {card['translation']}\n"
    message += f"Тип: {card_type_display}\n"
    message += f"Язык: {lang_label}\n"
    
    if card.get('alternative_translations'):
        alt_trans = ', '.join(card['alternative_translations'])
        message += f"🔄 Версии перевода: {alt_trans}\n"
    
    if card.get('topics'):
        topics = ', '.join(card['topics'])
        message += f"🏷️ Тематики: {topics}"
    
    return message

def get_language_label(language_from: str) -> str:
    """Получить метку языка"""
    return "мокш." if language_from == 'mdf' else "рус."

def get_language_name(language_from: str) -> str:
    """Получить название языка"""
    from config import LANGUAGES
    return LANGUAGES.get(language_from, language_from)

def get_card_type_display(card_type: str) -> str:
    """Получить отображаемое название типа"""
    from config import CARD_TYPES
    return CARD_TYPES.get(card_type, card_type)

def is_no_hint_type(card_type: str) -> bool:
    """Проверить, относится ли тип к категории 'без подсказки'"""
    from config import NO_HINT_TYPES
    return card_type in NO_HINT_TYPES

def format_user_stats(stats: dict, user_name: str = None, username: str = None) -> str:
    """Форматировать статистику пользователя для отображения"""
    message = f"📊 <b>Статистика пользователя</b>\n\n"
    
    if user_name:
        message += f"👤 Имя: {user_name}\n"
    if username:
        message += f"📛 Username: @{username}\n"
    
    message += f"🎯 Выучено слов: {stats['mastered']} из {stats['total_cards']}\n"
    message += f"📚 Изучено тематик: {stats['mastered_topics']} из {stats['total_topics']}\n"
    message += f"❌ Ошибок: {stats['wrong']}\n"
    message += f"💡 Использовано подсказок: {stats['hints']}\n"
    message += f"📈 Прогресс: {int(stats['mastered']/stats['total_cards']*100) if stats['total_cards'] > 0 else 0}%\n"
    
    return message

def get_default_user_stats() -> dict:
    """Получить пустую статистику по умолчанию"""
    return {
        'mastered': 0,
        'total_cards': 0,
        'wrong': 0,
        'hints': 0,
        'mastered_topics': 0,
        'total_topics': 0
    }

def validate_card_data(word: str, translation: str, language_from: str, language_to: str, card_type: str) -> tuple:
    """Валидация данных карточки. Возвращает (is_valid, error_message)"""
    from config import LANGUAGES, CARD_TYPES
    
    if not word or not word.strip():
        return False, "Слово не может быть пустым"
    
    if not translation or not translation.strip():
        return False, "Перевод не может быть пустым"
    
    if language_from not in LANGUAGES:
        return False, f"Неверный язык: {language_from}. Доступны: mdf, ru"
    
    if language_to not in LANGUAGES:
        return False, f"Неверный язык: {language_to}. Доступны: mdf, ru"
    
    if card_type not in CARD_TYPES:
        return False, f"Неверный тип. Доступны: {', '.join(CARD_TYPES.keys())}"
    
    return True, "OK"