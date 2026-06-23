from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.cards import get_thanks_text, set_thanks_text
from bot.keyboards import get_thanks_keyboard
from bot.utils import delete_previous
from config import ADMIN_ID

async def show_thanks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать сообщение с благодарностью"""
    query = update.callback_query
    await query.answer()
    
    thanks_text = await get_thanks_text()
    is_admin = query.from_user.id == ADMIN_ID
    
    reply_markup = await get_thanks_keyboard(is_admin)
    
    await delete_previous(update)
    await query.message.reply_text(
        thanks_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def edit_thanks_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование текста благодарности (только для админа)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    await delete_previous(update)
    await query.message.reply_text(
        "✏️ <b>Редактирование текста благодарности</b>\n\n"
        "Отправьте новый текст благодарности.\n"
        "Он будет показываться всем пользователям при нажатии на кнопку 'Выразить благодарность'.\n\n"
        "Для отмены отправьте /cancel",
        parse_mode='HTML'
    )
    context.user_data['awaiting_thanks_edit'] = True

async def edit_thanks_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нового текста благодарности"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if not context.user_data.get('awaiting_thanks_edit'):
        return
    
    text = update.message.text.strip()
    
    if text.lower() == '/cancel':
        context.user_data.pop('awaiting_thanks_edit', None)
        await update.message.reply_text("❌ Редактирование отменено.")
        return
    
    await set_thanks_text(text)
    context.user_data.pop('awaiting_thanks_edit', None)
    
    await update.message.reply_text(
        f"✅ Текст благодарности обновлён!\n\n"
        f"Новый текст:\n\n{text}",
        parse_mode='HTML'
    )