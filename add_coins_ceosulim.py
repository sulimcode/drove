#!/usr/bin/env python3
"""
Script to add 5,000,000 coins to @ceosulim
"""

from database import init_database, admin_get_user_by_username, admin_add_coins, create_user

def main():
    print("🔧 Инициализация базы данных...")
    init_database()
    
    # Check if ceosulim exists
    user = admin_get_user_by_username('ceosulim')
    
    if not user:
        print("⚠️  Пользователь @ceosulim не найден. Создаю пользователя...")
        # Create user with a placeholder telegram_id (will be updated when they start the bot)
        # Using a special ID for admin user
        admin_id = 999999999  # Placeholder ID
        create_user(admin_id, 'ceosulim', 'CEO Sulim')
        user = admin_get_user_by_username('ceosulim')
        print(f"✅ Пользователь @ceosulim создан с ID {admin_id}")
    
    print(f"👤 Найден пользователь: @{user['username']}")
    print(f"💰 Текущий баланс: {user['balance']} монет")
    
    # Add 5,000,000 coins
    amount = 5000000
    success = admin_add_coins(user['telegram_id'], amount)
    
    if success:
        # Get updated user info
        updated_user = admin_get_user_by_username('ceosulim')
        print(f"✅ Успешно добавлено {amount:,} монет!")
        print(f"💰 Новый баланс: {updated_user['balance']:,} монет")
    else:
        print("❌ Ошибка при добавлении монет!")

if __name__ == "__main__":
    main()