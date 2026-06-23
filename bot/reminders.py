import logging
from datetime import datetime
from telegram.ext import ContextTypes
from database.users import get_users_for_reminder, mark_reminder_sent
from config import REMINDER_DAYS

logger = logging.getLogger(__name__)

async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Отправка напоминаний пользователям (вызывается JobQueue)"""
    try:
        users = await get_users_for_reminder(REMINDER_DAYS)
        
        for user_id, first_name, last_name, username in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📚 <b>Напоминание!</b>\n\n"
                         f"{first_name or 'Друг'}, ты не занимался уже {REMINDER_DAYS} день!\n"
                         "Не забывай учить новые слова каждый день.\n\n"
                         "Начни сейчас: /study",
                    parse_mode='HTML'
                )
                await mark_reminder_sent(user_id)
                logger.info(f"Напоминание отправлено пользователю {user_id}")
            except Exception as e:
                logger.error(f"Не удалось отправить напоминание {user_id}: {e}")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминаний: {e}")