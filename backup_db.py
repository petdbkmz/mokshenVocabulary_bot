import sqlite3
import shutil
import os
from datetime import datetime
import sys
import io

# Включаем поддержку UTF-8 для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_NAME = "words.db"
BACKUP_DIR = "backups"

def backup_db():
    """Создать резервную копию базы данных"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_DIR}/words_{timestamp}.db"
    
    shutil.copy2(DB_NAME, backup_file)
    print(f"✅ Резервная копия создана: {backup_file}")
    
    # Удаляем старые резервные копии (оставляем последние 5)
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("words_")])
    if len(backups) > 5:
        for old_backup in backups[:-5]:
            os.remove(os.path.join(BACKUP_DIR, old_backup))
            print(f"🗑️ Удалена старая копия: {old_backup}")

if __name__ == "__main__":
    backup_db()