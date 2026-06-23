import aiosqlite
from config import DB_NAME, DEFAULT_THANKS_TEXT
from .db import get_db

async def init_db():
    """Создание всех таблиц в базе данных"""
    db = await get_db()
    
    # Таблица пользователей
    await db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_editor BOOLEAN DEFAULT FALSE,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reminder_sent BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Таблица карточек
    await db.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            translation TEXT NOT NULL,
            language_from TEXT NOT NULL,
            language_to TEXT NOT NULL,
            image_url TEXT,
            card_type TEXT NOT NULL,
            wrong_hints TEXT,
            topics TEXT,
            alternative_translations TEXT,
            first_letter TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица прогресса
    await db.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            user_id INTEGER,
            card_id INTEGER,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0,
            hint_used BOOLEAN DEFAULT FALSE,
            last_shown TIMESTAMP,
            mastered BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (card_id) REFERENCES cards(card_id),
            PRIMARY KEY (user_id, card_id)
        )
    ''')
    
    # Таблица для удалённых слов
    await db.execute('''
        CREATE TABLE IF NOT EXISTS deleted_cards_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            word TEXT,
            translation TEXT,
            deleted_by INTEGER,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица для обращений в поддержку
    await db.execute('''
        CREATE TABLE IF NOT EXISTS support_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_message TEXT,
            admin_response TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            responded_at TIMESTAMP
        )
    ''')
    
    # Таблица для конфигураций бота
    await db.execute('''
        CREATE TABLE IF NOT EXISTS bot_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    await db.commit()
    
    # Миграция для новых полей
    await migrate_db()
    
    # Добавляем текст благодарности по умолчанию
    await db.execute('''
        INSERT OR IGNORE INTO bot_config (key, value)
        VALUES ('thanks_text', ?)
    ''', (DEFAULT_THANKS_TEXT,))
    await db.commit()
    
    from config import ADMIN_ID
    from .users import set_editor
    await set_editor(ADMIN_ID, True)

async def migrate_db():
    """Обновить структуру БД для новых полей"""
    db = await get_db()
    
    # Пробуем добавить новые колонки (если их нет)
    for column in ['topics', 'alternative_translations', 'first_letter']:
        try:
            await db.execute(f"ALTER TABLE cards ADD COLUMN {column} TEXT")
        except aiosqlite.OperationalError:
            pass  # Колонка уже существует
    
    try:
        await db.execute("ALTER TABLE users ADD COLUMN reminder_sent BOOLEAN DEFAULT FALSE")
    except aiosqlite.OperationalError:
        pass
    
    # Обновляем first_letter для существующих слов
    await db.execute('''
        UPDATE cards 
        SET first_letter = UPPER(SUBSTR(word, 1, 1))
        WHERE first_letter IS NULL
    ''')
    
    await db.commit()