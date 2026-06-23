from telegram import Update
from telegram.ext import ContextTypes
from database.progress import get_user_stats
from database.users import update_activity, reset_reminder_flag
from bot.keyboards import get_stats_keyboard
from bot.utils import delete_previous, format_user_stats

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя"""
    user_id = update.effective_user.id
    stats = await get_user_stats(user_id)
    
    await update_activity(user_id)
    await reset_reminder_flag(user_id)
    
    message = format_user_stats(stats)
    reply_markup = get_stats_keyboard()
    
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