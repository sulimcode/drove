#!/usr/bin/env python3
"""
Test script to verify admin commands and user purchase functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import (
    init_database, create_user, get_user, buy_prisoner,
    admin_add_coins, admin_set_coins, admin_get_user_by_username,
    admin_get_all_users
)

def test_admin_functions():
    """Test admin functions"""
    print("=== Testing Admin Functions ===")
    
    # Initialize database
    init_database()
    
    # Create test users
    print("Creating test users...")
    create_user(123456, "testuser1", "Test User 1")
    create_user(789012, "testuser2", "Test User 2")
    
    # Test admin_get_user_by_username
    user = admin_get_user_by_username("testuser1")
    if user:
        print(f"✅ Found user: @{user['username']} with balance {user['balance']}")
    else:
        print("❌ Failed to find user")
        return False
    
    # Test admin_add_coins
    print("Testing admin_add_coins...")
    success = admin_add_coins(123456, 1000)
    if success:
        updated_user = get_user(123456)
        print(f"✅ Added 1000 coins. New balance: {updated_user['balance']}")
    else:
        print("❌ Failed to add coins")
        return False
    
    # Test admin_set_coins
    print("Testing admin_set_coins...")
    success = admin_set_coins(123456, 5000)
    if success:
        updated_user = get_user(123456)
        print(f"✅ Set balance to 5000. Current balance: {updated_user['balance']}")
    else:
        print("❌ Failed to set coins")
        return False
    
    return True

def test_buy_prisoner():
    """Test prisoner purchase functionality"""
    print("\n=== Testing Prisoner Purchase ===")
    
    # Get test users
    buyer = get_user(123456)  # testuser1 with 5000 coins
    prisoner = get_user(789012)  # testuser2 with default 300 coins
    
    if not buyer or not prisoner:
        print("❌ Test users not found")
        return False
    
    print(f"Buyer: @{buyer['username']} - Balance: {buyer['balance']} coins")
    print(f"Prisoner: @{prisoner['username']} - Price: {prisoner['price']} coins")
    
    # Test purchase
    print("Attempting to buy prisoner...")
    success, message = buy_prisoner(buyer['telegram_id'], prisoner['telegram_id'])
    
    if success:
        print(f"✅ Purchase successful: {message}")
        
        # Check updated balances
        updated_buyer = get_user(buyer['telegram_id'])
        updated_prisoner = get_user(prisoner['telegram_id'])
        
        print(f"Updated buyer balance: {updated_buyer['balance']} coins")
        print(f"Updated prisoner price: {updated_prisoner['price']} coins")
        print(f"Prisoner owner: {updated_prisoner['owner_id']}")
        
        return True
    else:
        print(f"❌ Purchase failed: {message}")
        return False

def test_admin_list_users():
    """Test admin user listing"""
    print("\n=== Testing Admin User List ===")
    
    users = admin_get_all_users()
    if users:
        print(f"✅ Found {len(users)} users in database:")
        for i, user in enumerate(users[:5], 1):  # Show first 5
            name = user['username'] or user['first_name'] or f"ID{user['telegram_id']}"
            print(f"  {i}. @{name} - {user['balance']} coins, {user['prisoner_count']} prisoners")
        return True
    else:
        print("❌ No users found or error occurred")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Bot Fixes...")
    
    try:
        # Test admin functions
        if not test_admin_functions():
            print("❌ Admin functions test failed")
            return
        
        # Test prisoner purchase
        if not test_buy_prisoner():
            print("❌ Prisoner purchase test failed")
            return
        
        # Test admin user list
        if not test_admin_list_users():
            print("❌ Admin user list test failed")
            return
        
        print("\n🎉 All tests passed! Bot fixes are working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()