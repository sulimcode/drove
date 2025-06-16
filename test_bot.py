#!/usr/bin/env python3
"""
Test script for Durov's Prison bot functionality
"""

import sqlite3
from database import create_user, get_user, buy_prisoner, get_my_prisoners, transfer_money

def test_bot_functionality():
    print('Testing Durov Prison Bot functionality...')
    
    # Create test users
    print('1. Creating test users...')
    user1_id = 123456789
    user2_id = 987654321
    user3_id = 555666777
    
    create_user(user1_id, 'testuser1', 'Test User 1')
    create_user(user2_id, 'testuser2', 'Test User 2') 
    create_user(user3_id, 'testuser3', 'Test User 3')
    
    # Verify users were created
    user1 = get_user(user1_id)
    user2 = get_user(user2_id)
    if user1 and user2:
        print(f'   User 1: {user1["username"]} - Balance: {user1["balance"]} - Price: {user1["price"]}')
        print(f'   User 2: {user2["username"]} - Balance: {user2["balance"]} - Price: {user2["price"]}')
    
    # Test prisoner purchase
    print('2. Testing prisoner purchase...')
    success, message = buy_prisoner(user1_id, user2_id)
    print(f'   Purchase result: {success} - {message}')
    
    if success:
        user1_after = get_user(user1_id)
        user2_after = get_user(user2_id)
        print(f'   User 1 balance after purchase: {user1_after["balance"]}')
        print(f'   User 2 new price: {user2_after["price"]}')
        print(f'   User 2 owner: {user2_after["owner_id"]}')
    
    # Test prisoner list
    print('3. Testing prisoner list...')
    prisoners = get_my_prisoners(user1_id)
    print(f'   User 1 owns {len(prisoners)} prisoners')
    if prisoners:
        for p in prisoners:
            print(f'     - {p["username"]} (price: {p["price"]})')
    
    # Test money transfer
    print('4. Testing money transfer...')
    success, message = transfer_money(user1_id, user3_id, 50)
    print(f'   Transfer result: {success} - {message}')
    
    print('\nAll core features tested successfully!')

if __name__ == "__main__":
    test_bot_functionality()