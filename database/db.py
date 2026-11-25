import aiosqlite
from config import DB_NAME

# Единое подключение к БД (пул)
_db_connection = None

async def get_db():
    """Получить подключение к БД (создаёт, если нет)"""
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(DB_NAME)
        # Включаем поддержку внешних ключей
        await _db_connection.execute("PRAGMA foreign_keys = ON")
        # Unicode-aware lowercase для case-insensitive поиска
        # (встроенный LOWER в SQLite не трогает кириллицу)
        await _db_connection.create_function(
            "ulower", 1,
            lambda s: s.lower() if isinstance(s, str) else s
        )
    return _db_connection

async def close_db():
    """Закрыть подключение к БД"""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None