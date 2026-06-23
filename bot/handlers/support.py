from telegram import Update
from telegram.ext import ContextTypes
from database.support import (
    save_support_message, get_pending_messages, 
    get_message_by_id, mark_message_responded
)
from database.users import update_activity
from bot.keyboards import get_support_reply_keyboard, get_back_button
from bot.utils import delete_previous
from config import ADMIN_ID

# ============================================
# ОБРАБОТКА КНОПКИ "СВЯЗАТЬСЯ"
# ============================================

async def contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопки 'Связаться с поддержкой'"""
    query = update.callback_query
    await query.answer()
    
    await delete_previous(update)
    await query.message.reply_text(
        "📝 <b>Напишите ваше сообщение в поддержку</b>\n\n"
        "Опишите вашу проблему или вопрос, и я передам его администратору.\n"
        "Обычно ответ приходит в течение 24 часов.\n\n"
        "Для отмены отправьте /cancel",
        parse_mode='HTML'
    )
    context.user_data['awaiting_support_message'] = True

# ============================================
# ОБРАБОТКА СООБЩЕНИЯ В ПОДДЕРЖКУ
# ============================================

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщения в поддержку от пользователя"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    if message_text.lower() == '/cancel':
        context.user_data.pop('awaiting_support_message', None)
        from .start import start
        await start(update, context)
        return
    
    msg_id = await save_support_message(user_id, message_text)
    
    user = update.effective_user
    user_name = user.first_name or user.username or str(user_id)
    
    reply_markup = get_support_reply_keyboard(msg_id)
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 <b>Новое обращение в поддержку!</b>\n\n"
             f"👤 От: {user_name}\n"
             f"🆔 ID: {user_id}\n"
             f"📝 Сообщение:\n{message_text}",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    await update.message.reply_text(
        "✅ Ваше сообщение отправлено в поддержку!\n"
        "Мы ответим вам как можно скорее."
    )
    
    context.user_data.pop('awaiting_support_message', None)

# ============================================
# ПРОСМОТР ОБРАЩЕНИЙ (АДМИН)
# ============================================

async def check_support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра обращений (только для админа)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    messages = await get_pending_messages()
    
    if not messages:
        await update.message.reply_text("📭 Нет новых обращений.")
        return
    
    from database.db import get_db
    db = await get_db()
    
    for msg_id, user_id, user_message, created_at in messages:
        async with db.execute('SELECT first_name, username FROM users WHERE user_id = ?',
                            (user_id,)) as cursor:
            user_info = await cursor.fetchone()
        
        user_name = user_info[0] if user_info else str(user_id)
        
        reply_markup = get_support_reply_keyboard(msg_id)
        
        await update.message.reply_text(
            f"📩 <b>Обращение #{msg_id}</b>\n\n"
            f"👤 От: {user_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📝 Сообщение:\n{user_message}\n\n"
            f"📅 {created_at}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

# ============================================
# ОТВЕТ АДМИНА НА ОБРАЩЕНИЕ
# ============================================

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия на кнопку 'Ответить' в обращении"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("reply_to_"):
        msg_id = int(data.split("_")[2])
        context.user_data['replying_to'] = msg_id
        
        await delete_previous(update)
        await query.message.reply_text(
            "✏️ <b>Напишите ваш ответ пользователю</b>\n\n"
            "Отправьте текст ответа.\n"
            "Для отмены отправьте /cancel",
            parse_mode='HTML'
        )

async def handle_admin_response_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста ответа администратора"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    msg_id = context.user_data.get('replying_to')
    if not msg_id:
        await update.message.reply_text("❌ Нет активного обращения для ответа.")
        return
    
    response_text = update.message.text.strip()
    
    if response_text.lower() == '/cancel':
        context.user_data.pop('replying_to', None)
        await update.message.reply_text("❌ Отправка ответа отменена.")
        return
    
    msg_data = await get_message_by_id(msg_id)
    if not msg_data:
        await update.message.reply_text("❌ Сообщение не найдено.")
        context.user_data.pop('replying_to', None)
        return
    
    await mark_message_responded(msg_id, response_text)
    
    user_id_to_reply = msg_data[1]
    user_message = msg_data[2]
    
    try:
        await context.bot.send_message(
            chat_id=user_id_to_reply,
            text=f"📩 <b>На Ваше обращение поступил ответ:</b>\n\n"
                 f"Ваше сообщение: {user_message}\n\n"
                 f"✉️ Ответ:\n{response_text}\n\n"
                 f"С уважением, команда бота 🌟",
            parse_mode='HTML'
        )
        
        await update.message.reply_text(
            f"✅ Ответ отправлен пользователю!\n\n"
            f"📝 Ваш ответ:\n{response_text}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке ответа: {e}")
    
    context.user_data.pop('replying_to', None)