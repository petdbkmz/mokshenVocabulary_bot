import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# ТОКЕН БОТА (ОБЯЗАТЕЛЬНО!)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Создай файл .env")

# ID АДМИНИСТРАТОРА
ADMIN_ID = int(os.environ.get("ADMIN_ID", 6376219906))

# Настройки напоминаний
REMINDER_DAYS = int(os.environ.get("REMINDER_DAYS", 1))
REMINDER_HOUR = int(os.environ.get("REMINDER_HOUR", 10))
REMINDER_MINUTE = int(os.environ.get("REMINDER_MINUTE", 0))

# Ссылка для благодарности
THANKS_LINK = os.environ.get("THANKS_LINK", "https://pay.cloudtips.ru/p/551d8791")

# Имя файла базы данных
DB_NAME = "words.db"

# Количество правильных ответов для заучивания
MASTERY_THRESHOLD = 3