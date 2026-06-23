import sqlite3
import json

DB_NAME = "words.db"

def view_all_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Получаем список всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("=" * 60)
    print("📊 БАЗА ДАННЫХ")
    print("=" * 60)
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 ТАБЛИЦА: {table_name}")
        print("-" * 40)
        
        # Получаем структуру таблицы
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print("Структура:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        
        # Получаем данные
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nДанные ({len(rows)} записей):")
            # Получаем имена колонок
            cursor.execute(f"PRAGMA table_info({table_name})")
            col_names = [col[1] for col in cursor.fetchall()]
            
            for i, row in enumerate(rows[:10]):  # Показываем первые 10 записей
                print(f"  {i+1}. ", end="")
                for j, col_name in enumerate(col_names):
                    value = row[j] if j < len(row) else 'N/A'
                    if col_name == 'wrong_hints' and value:
                        try:
                            value = json.loads(value)
                        except:
                            pass
                    print(f"{col_name}: {value}", end=" | ")
                print()
            
            if len(rows) > 10:
                print(f"  ... и ещё {len(rows) - 10} записей")
        else:
            print("  (пусто)")
    
    conn.close()

if __name__ == "__main__":
    view_all_tables()