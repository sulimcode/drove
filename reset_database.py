#!/usr/bin/env python3
"""
Database reset script for Durov's Prison game
This script will completely clear all data and reset the database
"""

import os
from database import reset_database

def main():
    print("🔄 Сброс базы данных Тюрьмы Дурова...")
    print("⚠️  Все данные будут удалены!")
    
    # Execute database reset
    try:
        reset_database()
        print("✅ База данных успешно очищена!")
        print("✅ Все таблицы пересозданы!")
        print("✅ Игра готова к запуску с чистого листа!")
        
        # Show database file info
        db_file = 'durov_prison.db'
        if os.path.exists(db_file):
            size = os.path.getsize(db_file)
            print(f"📁 Размер файла базы данных: {size} байт")
        
    except Exception as e:
        print(f"❌ Ошибка при сбросе базы данных: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()