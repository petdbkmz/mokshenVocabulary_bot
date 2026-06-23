from telegram import Update
from telegram.ext import ContextTypes
from database.users import update_activity, reset_reminder_flag
from bot.keyboards import get_main_menu_keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и регистрация пользователя"""
    user = update.effective_user
    user_id = user.id
    
    # Регистрируем пользователя
    from database.db import get_db
    db = await get_db()
    await db.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
    ''', (user_id, user.username, user.first_name, user.last_name))
    await db.commit()
    
    # Сбрасываем флаг напоминания
    await reset_reminder_flag(user_id)
    await update_activity(user_id)
    
    # Очищаем состояние пользователя
    context.user_data.clear()
    
    reply_markup = await get_main_menu_keyboard(user_id)
    
    text = f"👋 Привет, {user.first_name}!\n\nЯ помогу тебе учить слова мокшанского языка.\nВыбери действие на кнопках ниже:"
    
    if update.callback_query:
        await update.callback_query.delete_message()
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)