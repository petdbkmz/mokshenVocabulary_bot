import aiosqlite
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .db import get_db
from .cards import auto_backup

async def set_editor(user_id: int, is_editor: bool):
    """Назначить или убрать роль редактора"""
    db = await get_db()
    await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    await db.execute('UPDATE users SET is_editor = ? WHERE user_id = ?', (1 if is_editor else 0, user_id))
    await db.commit()
    await auto_backup()

async def is_editor(user_id: int) -> bool:
    """Проверить, является ли пользователь редактором"""
    db = await get_db()
    async with db.execute('SELECT is_editor FROM users WHERE user_id = ?', (user_id,)) as cursor:
        result = await cursor.fetchone()
        return bool(result[0]) if result else False

async def get_all_editors():
    """Получить список всех редакторов"""
    db = await get_db()
    async with db.execute('SELECT user_id, username, first_name, last_name FROM users WHERE is_editor = 1') as cursor:
        return await cursor.fetchall()

async def get_user_days(user_id: int) -> int:
    """Получить количество дней с момента регистрации пользователя"""
    db = await get_db()
    async with db.execute('SELECT created_at FROM users WHERE user_id = ?', (user_id,)) as cursor:
        result = await cursor.fetchone()
        if result:
            created_at = datetime.fromisoformat(result[0].replace('Z', '+00:00'))
            days = (datetime.now() - created_at).days
            return days
        return 0

async def get_user_id_by_username(username: str) -> Optional[int]:
    """Получить user_id по username"""
    db = await get_db()
    username = username.lstrip('@')
    async with db.execute('SELECT user_id FROM users WHERE username = ?', (username,)) as cursor:
        result = await cursor.fetchone()
        return result[0] if result else None

async def get_all_users_paginated(page: int = 0, per_page: int = 10) -> Tuple[List[Dict], int]:
    """Получить всех пользователей с пагинацией (от новых к старым)"""
    db = await get_db()
    offset = page * per_page
    
    async with db.execute('SELECT COUNT(*) FROM users') as cursor:
        total = (await cursor.fetchone())[0]
    
    async with db.execute('''
        SELECT user_id, username, first_name, last_name, is_editor, created_at, last_activity
        FROM users 
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset)) as cursor:
        rows = await cursor.fetchall()
        users = []
        for row in rows:
            users.append({
                'user_id': row[0],
                'username': row[1] or 'Нет',
                'first_name': row[2] or 'Нет',
                'last_name': row[3] or 'Нет',
                'is_editor': bool(row[4]),
                'created_at': row[5],
                'last_activity': row[6]
            })
        return users, total

async def update_activity(user_id: int):
    """Обновить время последней активности пользователя"""
    db = await get_db()
    await db.execute('UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
    await db.commit()

async def reset_reminder_flag(user_id: int):
    """Сбросить флаг напоминания (при активности пользователя)"""
    db = await get_db()
    await db.execute('UPDATE users SET reminder_sent = 0 WHERE user_id = ?', (user_id,))
    await db.commit()

async def mark_reminder_sent(user_id: int):
    """Отметить, что пользователю было отправлено напоминание"""
    db = await get_db()
    await db.execute('UPDATE users SET reminder_sent = 1 WHERE user_id = ?', (user_id,))
    await db.commit()

async def get_users_for_reminder(days: int = 1):
    """Получить пользователей для напоминания"""
    cutoff_date = datetime.now() - timedelta(days=days)
    db = await get_db()
    async with db.execute('''
        SELECT user_id, first_name, last_name, username 
        FROM users 
        WHERE last_activity < ? 
        AND user_id NOT IN (
            SELECT user_id FROM user_progress 
            WHERE last_shown > ?
            GROUP BY user_id
        )
    ''', (cutoff_date, cutoff_date)) as cursor:
        return await cursor.fetchall()