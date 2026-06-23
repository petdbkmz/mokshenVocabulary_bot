import sqlite3
import shutil
import os
import glob

DB_NAME = "words.db"
BACKUP_DIR = "backups"

def restore_latest_db():
    """Восстановить последнюю резервную копию базы данных"""
    backup_files = sorted(glob.glob(f"{BACKUP_DIR}/words_*.db"))
    
    if not backup_files:
        print("❌ Нет резервных копий для восстановления")
        return False
    
    latest_backup = backup_files[-1]  # Берём последнюю
    shutil.copy2(latest_backup, DB_NAME)
    print(f"✅ База данных восстановлена из: {latest_backup}")
    return True

def restore_db_by_timestamp(timestamp):
    """Восстановить базу данных по временной метке"""
    backup_file = f"{BACKUP_DIR}/words_{timestamp}.db"
    if os.path.exists(backup_file):
        shutil.copy2(backup_file, DB_NAME)
        print(f"✅ База данных восстановлена из: {backup_file}")
        return True
    else:
        print(f"❌ Файл не найден: {backup_file}")
        return False

if __name__ == "__main__":
    restore_latest_db()