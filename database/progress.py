import aiosqlite
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from .db import get_db
from .cards import auto_backup, get_all_topics

# ============================================
# ФУНКЦИИ ДЛЯ ПРОГРЕССА
# ============================================

async def update_progress(user_id: int, card_id: int, is_correct: Optional[bool] = None):
    """Обновить прогресс пользователя по карточке"""
    db = await get_db()
    
    if is_correct is None:
        # Просто обновляем время последнего показа
        await db.execute('''
            INSERT INTO user_progress (user_id, card_id, last_shown)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, card_id) DO UPDATE SET
            last_shown = CURRENT_TIMESTAMP
        ''', (user_id, card_id))
        
    elif is_correct:
        # Правильный ответ: увеличиваем счётчик
        await db.execute('''
            INSERT INTO user_progress (user_id, card_id, correct_count, last_shown)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, card_id) DO UPDATE SET
            correct_count = correct_count + 1,
            last_shown = CURRENT_TIMESTAMP
        ''', (user_id, card_id))
        
        # Проверяем, достиг ли пользователь порога mastery
        async with db.execute('''
            SELECT correct_count FROM user_progress 
            WHERE user_id = ? AND card_id = ?
        ''', (user_id, card_id)) as cursor:
            result = await cursor.fetchone()
            from config import MASTERY_THRESHOLD
            if result and result[0] >= MASTERY_THRESHOLD:
                await db.execute('''
                    UPDATE user_progress SET mastered = TRUE 
                    WHERE user_id = ? AND card_id = ?
                ''', (user_id, card_id))
                
    else:
        # Неправильный ответ: сбрасываем correct_count, увеличиваем wrong_count
        await db.execute('''
            INSERT INTO user_progress (user_id, card_id, correct_count, wrong_count, last_shown)
            VALUES (?, ?, 0, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, card_id) DO UPDATE SET
            correct_count = 0,
            wrong_count = wrong_count + 1,
            last_shown = CURRENT_TIMESTAMP
        ''', (user_id, card_id))
    
    await db.commit()

async def get_user_stats(user_id: int) -> Dict:
    """Получить статистику пользователя"""
    db = await get_db()
    
    # Основная статистика
    async with db.execute('''
        SELECT 
            COUNT(CASE WHEN mastered = TRUE THEN 1 END) as mastered_count,
            COALESCE(SUM(wrong_count), 0) as total_wrong,
            COUNT(CASE WHEN hint_used = TRUE THEN 1 END) as hints_used
        FROM user_progress
        WHERE user_id = ?
    ''', (user_id,)) as cursor:
        stats = await cursor.fetchone()
    
    # Общее количество карточек
    async with db.execute('SELECT COUNT(*) FROM cards') as cursor:
        total_cards = await cursor.fetchone()
    
    # Количество тематик
    all_topics = await get_all_topics()
    
    # Количество выученных тематик
    mastered_topics = 0
    for topic in all_topics:
        async with db.execute('''
            SELECT COUNT(*) FROM cards 
            WHERE topics LIKE ? 
            AND card_id NOT IN (
                SELECT card_id FROM user_progress 
                WHERE user_id = ? AND mastered = TRUE
            )
        ''', (f'%{topic}%', user_id)) as cursor:
            remaining = await cursor.fetchone()
            if remaining and remaining[0] == 0:
                mastered_topics += 1
    
    return {
        'mastered': stats[0] or 0 if stats else 0,
        'total_cards': total_cards[0] or 0 if total_cards else 0,
        'wrong': stats[1] or 0 if stats else 0,
        'hints': stats[2] or 0 if stats else 0,
        'mastered_topics': mastered_topics,
        'total_topics': len(all_topics)
    }

async def clear_user_stats(user_id: int) -> bool:
    """Очистить статистику пользователя"""
    try:
        db = await get_db()
        await db.execute('DELETE FROM user_progress WHERE user_id = ?', (user_id,))
        await db.commit()
        await auto_backup()
        return True
    except:
        return False

async def get_user_progress_for_card(user_id: int, card_id: int) -> Optional[Dict]:
    """Получить прогресс пользователя по конкретной карточке"""
    db = await get_db()
    async with db.execute('''
        SELECT correct_count, wrong_count, hint_used, mastered, last_shown
        FROM user_progress
        WHERE user_id = ? AND card_id = ?
    ''', (user_id, card_id)) as cursor:
        row = await cursor.fetchone()
        if row:
            return {
                'correct_count': row[0],
                'wrong_count': row[1],
                'hint_used': bool(row[2]),
                'mastered': bool(row[3]),
                'last_shown': row[4]
            }
        return None

async def get_mastered_words_count(user_id: int) -> int:
    """Получить количество выученных слов пользователя"""
    db = await get_db()
    async with db.execute('''
        SELECT COUNT(*) FROM user_progress
        WHERE user_id = ? AND mastered = TRUE
    ''', (user_id,)) as cursor:
        result = await cursor.fetchone()
        return result[0] if result else 0

async def get_total_words_count() -> int:
    """Получить общее количество слов в базе"""
    db = await get_db()
    async with db.execute('SELECT COUNT(*) FROM cards') as cursor:
        result = await cursor.fetchone()
        return result[0] if result else 0

async def get_user_activity(user_id: int, days: int = 7) -> List[Dict]:
    """Получить активность пользователя за последние N дней"""
    cutoff_date = datetime.now() - timedelta(days=days)
    db = await get_db()
    async with db.execute('''
        SELECT 
            DATE(last_shown) as date,
            COUNT(*) as total_shown,
            SUM(CASE WHEN mastered = TRUE THEN 1 ELSE 0 END) as new_mastered
        FROM user_progress
        WHERE user_id = ? AND last_shown >= ?
        GROUP BY DATE(last_shown)
        ORDER BY date DESC
    ''', (user_id, cutoff_date)) as cursor:
        rows = await cursor.fetchall()
        return [
            {
                'date': row[0],
                'total_shown': row[1],
                'new_mastered': row[2] or 0
            }
            for row in rows
        ]

async def reset_progress(user_id: int, card_id: int) -> bool:
    """Сбросить прогресс по одной карточке"""
    try:
        db = await get_db()
        await db.execute('''
            DELETE FROM user_progress
            WHERE user_id = ? AND card_id = ?
        ''', (user_id, card_id))
        await db.commit()
        return True
    except:
        return False

async def reset_all_progress(user_id: int) -> bool:
    """Сбросить весь прогресс пользователя"""
    try:
        db = await get_db()
        await db.execute('DELETE FROM user_progress WHERE user_id = ?', (user_id,))
        await db.commit()
        await auto_backup()
        return True
    except:
        return False

async def mark_hint_used(user_id: int, card_id: int):
    """Отметить, что пользователь использовал подсказку для карточки"""
    db = await get_db()
    await db.execute('''
        INSERT INTO user_progress (user_id, card_id, hint_used)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, card_id) DO UPDATE SET
        hint_used = 1
    ''', (user_id, card_id))
    await db.commit()