import aiosqlite
from typing import List, Dict, Optional, Tuple
from .db import get_db
from .cards import auto_backup

# ============================================
# ФУНКЦИИ ДЛЯ ПОДДЕРЖКИ
# ============================================

async def save_support_message(user_id: int, message: str) -> int:
    """Сохранить сообщение в поддержку"""
    db = await get_db()
    cursor = await db.execute('''
        INSERT INTO support_messages (user_id, user_message, status)
        VALUES (?, ?, 'pending')
    ''', (user_id, message))
    await db.commit()
    await auto_backup()
    return cursor.lastrowid

async def get_pending_messages() -> List[Tuple]:
    """Получить все непрочитанные сообщения в поддержку"""
    db = await get_db()
    async with db.execute('''
        SELECT message_id, user_id, user_message, created_at
        FROM support_messages
        WHERE status = 'pending'
        ORDER BY created_at ASC
    ''') as cursor:
        return await cursor.fetchall()

async def get_all_messages(limit: int = 50, offset: int = 0) -> List[Tuple]:
    """Получить все сообщения в поддержку с пагинацией"""
    db = await get_db()
    async with db.execute('''
        SELECT message_id, user_id, user_message, admin_response, status, created_at, responded_at
        FROM support_messages
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset)) as cursor:
        return await cursor.fetchall()

async def get_message_by_id(message_id: int) -> Optional[Tuple]:
    """Получить сообщение по ID"""
    db = await get_db()
    async with db.execute('SELECT * FROM support_messages WHERE message_id = ?', (message_id,)) as cursor:
        return await cursor.fetchone()

async def mark_message_responded(message_id: int, response: str):
    """Отметить сообщение как отвеченное"""
    db = await get_db()
    await db.execute('''
        UPDATE support_messages
        SET status = 'responded', 
            admin_response = ?,
            responded_at = CURRENT_TIMESTAMP
        WHERE message_id = ?
    ''', (response, message_id))
    await db.commit()
    await auto_backup()

async def get_messages_by_user(user_id: int, limit: int = 20) -> List[Tuple]:
    """Получить все сообщения пользователя в поддержку"""
    db = await get_db()
    async with db.execute('''
        SELECT message_id, user_message, admin_response, status, created_at, responded_at
        FROM support_messages
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit)) as cursor:
        return await cursor.fetchall()

async def delete_message(message_id: int) -> bool:
    """Удалить сообщение из поддержки (только для админа)"""
    try:
        db = await get_db()
        await db.execute('DELETE FROM support_messages WHERE message_id = ?', (message_id,))
        await db.commit()
        return True
    except:
        return False

async def get_unresponded_count() -> int:
    """Получить количество неотвеченных сообщений"""
    db = await get_db()
    async with db.execute('''
        SELECT COUNT(*) FROM support_messages WHERE status = 'pending'
    ''') as cursor:
        result = await cursor.fetchone()
        return result[0] if result else 0