# ============================================
# ФАЙЛ ДЛЯ ЗАПУСКА НА RENDER
# ============================================

import os
import asyncio
import threading
import subprocess
import sqlite3
from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Бот работает!"

@app.route('/health')
def health():
    return "✅ OK", 200

def restore_db_if_needed():
    """Восстановить базу, если она пустая или повреждена"""
    logger.info("🔍 Проверяю состояние базы данных...")
    
    # Проверяем, есть ли папка с бэкапами
    if not os.path.exists("backups"):
        logger.info("📭 Папка backups/ не найдена. Пропускаю восстановление.")
        return
    
    # Получаем список бэкапов
    backup_files = sorted([f for f in os.listdir("backups") if f.startswith("words_")])
    if not backup_files:
        logger.info("📭 Нет файлов бэкапа. Пропускаю восстановление.")
        return
    
    needs_restore = False
    
    # Проверяем, существует ли база
    if not os.path.exists("words.db"):
        logger.warning("⚠️ База данных не найдена. Нужно восстановление.")
        needs_restore = True
    else:
        # Проверяем размер
        if os.path.getsize("words.db") < 1024:
            logger.warning("⚠️ База данных повреждена (размер < 1 КБ). Нужно восстановление.")
            needs_restore = True
        else:
            # Проверяем, есть ли слова
            try:
                conn = sqlite3.connect("words.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM cards")
                count = cursor.fetchone()[0]
                conn.close()
                if count == 0:
                    logger.warning("⚠️ База данных пуста (нет слов). Нужно восстановление.")
                    needs_restore = True
                else:
                    logger.info(f"✅ База данных в порядке ({count} слов).")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при проверке базы: {e}. Нужно восстановление.")
                needs_restore = True
    
    if needs_restore:
        logger.info("🔄 Восстанавливаю базу данных из резервной копии...")
        try:
            # Запускаем restore_db.py
            result = subprocess.run(
                ["python", "restore_db.py"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            if result.returncode == 0:
                logger.info("✅ База данных успешно восстановлена!")
                # Проверяем результат
                if os.path.exists("words.db"):
                    size = os.path.getsize("words.db")
                    logger.info(f"📊 Размер восстановленной базы: {size} байт")
                    # Проверяем количество слов
                    try:
                        conn = sqlite3.connect("words.db")
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM cards")
                        count = cursor.fetchone()[0]
                        conn.close()
                        logger.info(f"📚 Восстановлено слов: {count}")
                    except:
                        pass
            else:
                logger.error(f"❌ Ошибка при восстановлении: {result.stderr}")
        except Exception as e:
            logger.error(f"❌ Исключение при восстановлении: {e}")

def run_bot():
    """Запуск бота"""
    try:
        from bot import main as bot_main
        logger.info("🚀 Запуск бота...")
        asyncio.run(bot_main())
    except Exception as e:
        logger.error(f"Ошибка в боте: {e}")
        import traceback
        traceback.print_exc()

def run_flask():
    """Запуск Flask в отдельном потоке"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    logger.info("🚀 Запуск сервера...")
    
    # ========== ВОССТАНАВЛИВАЕМ БАЗУ ДО ЗАПУСКА БОТА ==========
    restore_db_if_needed()
    # ==========================================================
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask запущен")
    
    # Запускаем бота в основном потоке
    run_bot()