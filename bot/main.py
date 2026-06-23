import logging
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN
from database.init_db import init_db
from bot.handlers import *
from bot.reminders import send_reminders

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    logger.info("🚀 Запуск бота...")
    
    # Инициализируем БД
    await init_db()
    
    # Создаём приложение (НОВЫЙ СПОСОБ)
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("study", study))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(CommandHandler("tables", tables_command))
    application.add_handler(CommandHandler("add_editor", add_editor_command))
    application.add_handler(CommandHandler("remove_editor", remove_editor_command))
    application.add_handler(CommandHandler("check_support", check_support_command))
    
    # Регистрируем обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Настраиваем напоминания через JobQueue
    from config import REMINDER_HOUR, REMINDER_MINUTE
    job_queue = application.job_queue
    if job_queue:
        import datetime
        job_queue.run_daily(
            send_reminders,
            time=datetime.time(hour=REMINDER_HOUR, minute=REMINDER_MINUTE),
            name="daily_reminders"
        )
        logger.info(f"⏰ Напоминания настроены на {REMINDER_HOUR:02d}:{REMINDER_MINUTE:02d}")
    
    # === НОВЫЙ СПОСОБ ЗАПУСКА (для версии 21.x) ===
    logger.info("✅ Бот запущен!")
    await application.initialize()
    await application.start()
    
    # Начинаем polling
    await application.updater.start_polling()
    
    # Держим бота активным
    logger.info("✅ Бот готов к работе!")
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")