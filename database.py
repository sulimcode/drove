"""
Database management for Durov's Prison game
Handles all database operations including user management, transactions, and ownership tracking
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import threading

logger = logging.getLogger(__name__)

# Thread-local storage for database connections
local_data = threading.local()

def get_db_connection():
    """Get thread-local database connection"""
    if not hasattr(local_data, 'connection'):
        local_data.connection = sqlite3.connect('durov_prison.db', check_same_thread=False)
        local_data.connection.row_factory = sqlite3.Row
    return local_data.connection

def reset_database():
    """Reset database - DROP ALL TABLES and recreate them"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Drop all tables
    tables_to_drop = [
        'profit_log',
        'prisoner_upgrades', 
        'work_assignments',
        'income_log',
        'transactions',
        'ownership_history',
        'users'
    ]
    
    for table in tables_to_drop:
        try:
            cursor.execute(f'DROP TABLE IF EXISTS {table}')
            logger.info(f"Dropped table: {table}")
        except sqlite3.Error as e:
            logger.error(f"Error dropping table {table}: {e}")
    
    conn.commit()
    logger.info("All tables dropped successfully")
    
    # Reinitialize database with clean tables
    init_database()
    logger.info("Database reset completed - all data cleared")

def init_database():
    """Initialize database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 300,
            points REAL DEFAULT 0.0,
            price INTEGER DEFAULT 100,
            owner_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_income TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referral_code TEXT UNIQUE,
            shield_until TIMESTAMP,
            shield_active BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Ownership history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ownership_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prisoner_id INTEGER,
            old_owner_id INTEGER,
            new_owner_id INTEGER,
            price INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prisoner_id) REFERENCES users (telegram_id),
            FOREIGN KEY (old_owner_id) REFERENCES users (telegram_id),
            FOREIGN KEY (new_owner_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER,
            to_user_id INTEGER,
            amount INTEGER,
            transaction_type TEXT,
            description TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_user_id) REFERENCES users (telegram_id),
            FOREIGN KEY (to_user_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Income log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS income_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            prisoner_count INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Work assignments table for prisoners
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            prisoner_id INTEGER,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'working',
            expected_reward INTEGER,
            completed BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (owner_id) REFERENCES users (telegram_id),
            FOREIGN KEY (prisoner_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Prisoner upgrades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prisoner_upgrades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prisoner_id INTEGER,
            upgrade_level INTEGER DEFAULT 1,
            income_multiplier REAL DEFAULT 1.0,
            upgrade_cost INTEGER DEFAULT 100,
            total_invested INTEGER DEFAULT 0,
            last_upgraded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prisoner_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Profit tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            profit_generated INTEGER DEFAULT 0,
            profit_received INTEGER DEFAULT 0,
            period_start TIMESTAMP,
            period_end TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id)
        )
    ''')
    
    # Add points column to existing users if it doesn't exist
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN points REAL DEFAULT 0.0')
        conn.commit()
        logger.info("Added points column to users table")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    conn.commit()
    logger.info("Database initialized successfully")

def create_user(telegram_id: int, username: str = None, first_name: str = None, referrer_id: int = None) -> bool:
    """Create a new user in the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Generate unique referral code
        referral_code = f"trap_{telegram_id}"
        
        cursor.execute('''
            INSERT INTO users (telegram_id, username, first_name, referral_code)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, username, first_name, referral_code))
        
        # If user was referred, set the referrer as owner
        if referrer_id:
            cursor.execute('''
                UPDATE users SET owner_id = ? WHERE telegram_id = ?
            ''', (referrer_id, telegram_id))
            
            # Add to ownership history
            cursor.execute('''
                INSERT INTO ownership_history (prisoner_id, old_owner_id, new_owner_id, price)
                VALUES (?, NULL, ?, 0)
            ''', (telegram_id, referrer_id))
            
            logger.info(f"User {telegram_id} captured by referrer {referrer_id}")
        
        conn.commit()
        logger.info(f"Created new user: {telegram_id} (@{username})")
        return True
        
    except sqlite3.IntegrityError:
        logger.warning(f"User {telegram_id} already exists")
        return False

def get_user(telegram_id: int) -> Optional[Dict]:
    """Get user information by telegram ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    row = cursor.fetchone()
    
    if row:
        return dict(row)
    return None

def update_user_balance(telegram_id: int, amount: int) -> bool:
    """Update user balance (can be positive or negative)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET balance = balance + ? WHERE telegram_id = ?
    ''', (amount, telegram_id))
    
    conn.commit()
    return cursor.rowcount > 0

def update_user_points(telegram_id: int, amount: float) -> bool:
    """Update user points (can be positive or negative)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET points = points + ? WHERE telegram_id = ?
    ''', (amount, telegram_id))
    
    conn.commit()
    return cursor.rowcount > 0

def add_referral_points(user_id: int) -> bool:
    """Add 1 point for successful referral"""
    return update_user_points(user_id, 1.0)

def add_purchase_points(user_id: int, purchase_price: int) -> bool:
    """Add 0.01% of purchase price as points"""
    points_earned = purchase_price * 0.0001  # 0.01% = 0.0001
    return update_user_points(user_id, points_earned)

def transfer_money(from_user_id: int, to_user_id: int, amount: int) -> Tuple[bool, str]:
    """Transfer money between users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check sender's balance
    cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (from_user_id,))
    sender_balance = cursor.fetchone()
    
    if not sender_balance or sender_balance[0] < amount:
        return False, "Недостаточно монет для перевода! 💸"
    
    # Perform transfer
    cursor.execute('UPDATE users SET balance = balance - ? WHERE telegram_id = ?', (amount, from_user_id))
    cursor.execute('UPDATE users SET balance = balance + ? WHERE telegram_id = ?', (amount, to_user_id))
    
    # Log transaction
    cursor.execute('''
        INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type, description)
        VALUES (?, ?, ?, 'transfer', 'Перевод между игроками')
    ''', (from_user_id, to_user_id, amount))
    
    conn.commit()
    return True, f"Перевод {amount} монет выполнен успешно! 💰"

def buy_prisoner(buyer_id: int, prisoner_id: int) -> Tuple[bool, str]:
    """Buy a prisoner from their current owner"""
    from game_logic import GameLogic
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get prisoner info
    prisoner = get_user(prisoner_id)
    if not prisoner:
        return False, "Заключённый не найден! 🔍"
    
    # Can't buy yourself
    if buyer_id == prisoner_id:
        return False, "Ты не можешь купить самого себя! 🤡"
    
    # Check if already owned by buyer
    if prisoner['owner_id'] == buyer_id:
        return False, "Этот заключённый уже твой! 🔐"
    
    # Check if shield is active
    shield_status = check_shield_status(prisoner_id)
    if shield_status['has_shield']:
        hours_left = shield_status['time_left']
        return False, f"🛡️ Этот заключённый защищён щитом! Осталось {hours_left} часов до истечения защиты."
    
    price = prisoner['price']
    
    # Check buyer's balance
    buyer = get_user(buyer_id)
    if buyer['balance'] < price:
        return False, f"Недостаточно монет! Нужно {price} монет. 💸"
    
    old_owner_id = prisoner['owner_id']
    
    # Calculate new dynamic price after purchase
    base_new_price = int(price * 1.3)  # Basic 30% increase
    
    # Apply dynamic pricing factors for future price calculation
    # The price increases more if the prisoner has good trading history, income stability, etc.
    try:
        dynamic_multiplier = 1.0
        
        # Get trading activity for this prisoner
        cursor.execute('''
            SELECT COUNT(*) FROM ownership_history 
            WHERE prisoner_id = ? AND timestamp > datetime('now', '-30 days')
        ''', (prisoner_id,))
        recent_trades = cursor.fetchone()[0]
        
        if recent_trades >= 3:
            dynamic_multiplier += 0.1  # Active trading increases future price more
        
        # Check prisoner's empire value if they own others
        prisoners_owned = get_my_prisoners(prisoner_id)
        if len(prisoners_owned) >= 5:
            dynamic_multiplier += 0.15  # Valuable prisoners cost more
        
        new_price = int(base_new_price * dynamic_multiplier)
    except Exception as e:
        logger.error(f"Error calculating dynamic price: {e}")
        new_price = base_new_price
    
    # Transfer ownership
    cursor.execute('''
        UPDATE users SET owner_id = ?, price = ? WHERE telegram_id = ?
    ''', (buyer_id, new_price, prisoner_id))
    
    # Update buyer's balance
    cursor.execute('''
        UPDATE users SET balance = balance - ? WHERE telegram_id = ?
    ''', (price, buyer_id))
    
    # Pay previous owner if exists
    if old_owner_id:
        cursor.execute('''
            UPDATE users SET balance = balance + ? WHERE telegram_id = ?
        ''', (price, old_owner_id))
        
        # Log transaction to old owner
        cursor.execute('''
            INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type, description)
            VALUES (?, ?, ?, 'sale', 'Продажа заключённого')
        ''', (buyer_id, old_owner_id, price))
    
    # Log purchase transaction
    cursor.execute('''
        INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type, description)
        VALUES (?, ?, ?, 'purchase', 'Покупка заключённого')
    ''', (buyer_id, prisoner_id, price))
    
    # Add to ownership history
    cursor.execute('''
        INSERT INTO ownership_history (prisoner_id, old_owner_id, new_owner_id, price)
        VALUES (?, ?, ?, ?)
    ''', (prisoner_id, old_owner_id, buyer_id, price))
    
    # Award points to buyer (0.01% of purchase price)
    add_purchase_points(buyer_id, price)
    
    conn.commit()
    
    # Calculate points earned for display
    points_earned = round(price * 0.0001, 4)
    
    username = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner_id}"
    return True, f"🎉 Ты купил @{username} за {price} монет! ⭐ Получено очков: {points_earned}. Теперь он твой заключённый!"

def get_my_prisoners(owner_id: int) -> List[Dict]:
    """Get list of prisoners owned by user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT telegram_id, username, first_name, price, created_at
        FROM users WHERE owner_id = ?
        ORDER BY created_at DESC
    ''', (owner_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def get_random_prisoners(count: int = 5, exclude_user_id: int = None) -> List[Dict]:
    """Get random prisoners that can be bought"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT telegram_id, username, first_name, price, owner_id
        FROM users 
        WHERE telegram_id != ? 
        ORDER BY RANDOM() 
        LIMIT ?
    '''
    
    cursor.execute(query, (exclude_user_id or 0, count))
    return [dict(row) for row in cursor.fetchall()]

def get_sorted_prisoners(sort_by: str, exclude_user_id: int = None, count: int = 10) -> List[Dict]:
    """Get prisoners sorted by specified criteria"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Define sorting criteria
    order_clause = {
        'price_asc': 'ORDER BY price ASC',
        'price_desc': 'ORDER BY price DESC',
        'random': 'ORDER BY RANDOM()'
    }.get(sort_by, 'ORDER BY RANDOM()')
    
    query = f'''
        SELECT telegram_id, username, first_name, price, owner_id
        FROM users 
        WHERE telegram_id != ? 
        {order_clause}
        LIMIT ?
    '''
    
    cursor.execute(query, (exclude_user_id or 0, count))
    return [dict(row) for row in cursor.fetchall()]

def search_prisoners_by_username(search_term: str, exclude_user_id: int = None) -> List[Dict]:
    """Search for prisoners by username or first name"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT telegram_id, username, first_name, price, owner_id
        FROM users 
        WHERE telegram_id != ? 
        AND (username LIKE ? OR first_name LIKE ?)
        ORDER BY price ASC
        LIMIT 10
    '''
    
    search_pattern = f"%{search_term}%"
    cursor.execute(query, (exclude_user_id or 0, search_pattern, search_pattern))
    return [dict(row) for row in cursor.fetchall()]

def get_ownership_history(prisoner_id: int) -> List[Dict]:
    """Get ownership history for a prisoner"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT oh.*, u1.username as old_owner_username, u2.username as new_owner_username
        FROM ownership_history oh
        LEFT JOIN users u1 ON oh.old_owner_id = u1.telegram_id
        LEFT JOIN users u2 ON oh.new_owner_id = u2.telegram_id
        WHERE oh.prisoner_id = ?
        ORDER BY oh.timestamp ASC
    ''', (prisoner_id,))
    
    return [dict(row) for row in cursor.fetchall()]

def get_leaderboard(category: str = 'prisoners') -> List[Dict]:
    """Get leaderboard data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if category == 'prisoners':
        cursor.execute('''
            SELECT u.telegram_id, u.username, u.first_name, COUNT(p.telegram_id) as prisoner_count
            FROM users u
            LEFT JOIN users p ON u.telegram_id = p.owner_id
            GROUP BY u.telegram_id
            ORDER BY prisoner_count DESC
            LIMIT 10
        ''')
    elif category == 'balance':
        cursor.execute('''
            SELECT telegram_id, username, first_name, balance
            FROM users
            ORDER BY balance DESC
            LIMIT 10
        ''')
    elif category == 'value':
        cursor.execute('''
            SELECT u.telegram_id, u.username, u.first_name, 
                   COALESCE(SUM(p.price), 0) as total_value
            FROM users u
            LEFT JOIN users p ON u.telegram_id = p.owner_id
            GROUP BY u.telegram_id
            ORDER BY total_value DESC
            LIMIT 10
        ''')
    
    return [dict(row) for row in cursor.fetchall()]

def generate_hourly_income():
    """Generate hourly income for all users with prisoners (enhanced with upgrades)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all users with their prisoners and upgrade info
    cursor.execute('''
        SELECT u.telegram_id, p.telegram_id as prisoner_id, p.price
        FROM users u
        JOIN users p ON u.telegram_id = p.owner_id
        WHERE p.telegram_id IS NOT NULL
    ''')
    
    user_prisoners = cursor.fetchall()
    user_incomes = {}
    
    import random
    
    for row in user_prisoners:
        owner_id = row[0]
        prisoner_id = row[1]
        prisoner_price = row[2]
        
        # Get upgrade multiplier for this prisoner
        upgrade_info = get_prisoner_upgrade_info(prisoner_id)
        income_multiplier = upgrade_info['multiplier']
        
        # Calculate base income (1-3 coins per prisoner)
        base_income = random.randint(1, 3)
        
        # Apply upgrade multiplier
        enhanced_income = int(base_income * income_multiplier)
        
        # Add to owner's total income
        if owner_id not in user_incomes:
            user_incomes[owner_id] = {'total_income': 0, 'prisoner_count': 0, 'generated_profit': 0}
        
        user_incomes[owner_id]['total_income'] += enhanced_income
        user_incomes[owner_id]['prisoner_count'] += 1
        user_incomes[owner_id]['generated_profit'] += enhanced_income
    
    # Update balances and log income/profit
    for user_id, income_data in user_incomes.items():
        total_income = income_data['total_income']
        prisoner_count = income_data['prisoner_count']
        generated_profit = income_data['generated_profit']
        
        # Update user balance
        cursor.execute('''
            UPDATE users SET balance = balance + ?, last_income = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        ''', (total_income, user_id))
        
        # Log income
        cursor.execute('''
            INSERT INTO income_log (user_id, amount, prisoner_count)
            VALUES (?, ?, ?)
        ''', (user_id, total_income, prisoner_count))
        
        # Log profit data (user generated profit for their owner)
        log_profit_data(user_id, 0, total_income)  # received income
        
        # Log that this user generated profit for their owner
        user = get_user(user_id)
        if user and user['owner_id']:
            log_profit_data(user['owner_id'], generated_profit, 0)  # generated profit
        
        # Log transaction
        cursor.execute('''
            INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type, description)
            VALUES (NULL, ?, ?, 'income', 'Почасовой доход с заключённых')
        ''', (user_id, total_income))
    
    conn.commit()
    logger.info(f"Generated hourly income for {len(user_incomes)} users")

def get_user_by_referral_code(referral_code: str) -> Optional[Dict]:
    """Get user by referral code"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE referral_code = ?', (referral_code,))
    row = cursor.fetchone()
    
    if row:
        return dict(row)
    return None

def update_user_info(telegram_id: int, username: str = None, first_name: str = None):
    """Update user information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users SET username = ?, first_name = ? WHERE telegram_id = ?
    ''', (username, first_name, telegram_id))
    
    conn.commit()

def send_prisoners_to_work(owner_id: int) -> Tuple[bool, str, int]:
    """Send all prisoners of an owner to work for 1 hour"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all prisoners owned by the user
    prisoners = get_my_prisoners(owner_id)
    
    if not prisoners:
        return False, "У тебя нет заключённых для отправки на работу! 🤷‍♂️", 0
    
    # Check if any prisoners are already working
    cursor.execute('''
        SELECT COUNT(*) FROM work_assignments 
        WHERE owner_id = ? AND completed = FALSE
    ''', (owner_id,))
    
    active_jobs = cursor.fetchone()[0]
    if active_jobs > 0:
        return False, "Твои заключённые уже работают! Дождись завершения текущих заданий. ⏰", 0
    
    total_expected_reward = 0
    
    # Create work assignments for each prisoner
    for prisoner in prisoners:
        # Calculate expected reward based on prisoner's price (level)
        base_reward = max(5, prisoner['price'] // 20)  # Minimum 5 coins, scales with price
        import random
        reward_multiplier = random.uniform(0.8, 1.2)  # Random factor
        expected_reward = int(base_reward * reward_multiplier)
        total_expected_reward += expected_reward
        
        # Insert work assignment
        cursor.execute('''
            INSERT INTO work_assignments (owner_id, prisoner_id, end_time, expected_reward)
            VALUES (?, ?, datetime('now', '+1 hour'), ?)
        ''', (owner_id, prisoner['telegram_id'], expected_reward))
    
    conn.commit()
    
    return True, f"🏭 Отправил {len(prisoners)} заключённых на работу!\nОжидаемая прибыль: {total_expected_reward} монет\nВремя завершения: через 1 час", len(prisoners)

def collect_work_rewards(owner_id: int) -> Tuple[bool, str, int]:
    """Collect rewards from completed work assignments"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get completed work assignments
    cursor.execute('''
        SELECT wa.*, u.username, u.first_name 
        FROM work_assignments wa
        JOIN users u ON wa.prisoner_id = u.telegram_id
        WHERE wa.owner_id = ? AND wa.completed = FALSE 
        AND datetime('now') >= wa.end_time
    ''', (owner_id,))
    
    completed_jobs = cursor.fetchall()
    
    if not completed_jobs:
        return False, "Нет готовых заданий для сбора награды! 🕐", 0
    
    total_reward = 0
    prisoner_names = []
    
    for job in completed_jobs:
        job_dict = dict(job)
        reward = job_dict['expected_reward']
        total_reward += reward
        
        prisoner_name = job_dict['username'] or job_dict['first_name'] or f"ID{job_dict['prisoner_id']}"
        prisoner_names.append(f"@{prisoner_name}")
        
        # Mark as completed
        cursor.execute('''
            UPDATE work_assignments SET completed = TRUE WHERE id = ?
        ''', (job_dict['id'],))
    
    # Add reward to owner's balance
    cursor.execute('''
        UPDATE users SET balance = balance + ? WHERE telegram_id = ?
    ''', (total_reward, owner_id))
    
    # Log transaction
    cursor.execute('''
        INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type, description)
        VALUES (NULL, ?, ?, 'work_reward', 'Награда за работу заключённых')
    ''', (owner_id, total_reward))
    
    conn.commit()
    
    workers_text = ", ".join(prisoner_names[:3])
    if len(prisoner_names) > 3:
        workers_text += f" и ещё {len(prisoner_names) - 3}"
    
    return True, f"💰 Собрал награду за работу!\nРаботники: {workers_text}\nПолучено: {total_reward} монет", total_reward

def get_work_status(owner_id: int) -> Dict:
    """Get current work status for owner's prisoners"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get active work assignments
    cursor.execute('''
        SELECT wa.*, u.username, u.first_name 
        FROM work_assignments wa
        JOIN users u ON wa.prisoner_id = u.telegram_id
        WHERE wa.owner_id = ? AND wa.completed = FALSE
    ''', (owner_id,))
    
    active_jobs = cursor.fetchall()
    
    if not active_jobs:
        return {
            'has_active_jobs': False,
            'workers_count': 0,
            'total_expected': 0,
            'ready_to_collect': 0,
            'still_working': 0
        }
    
    ready_count = 0
    working_count = 0
    total_expected = 0
    
    for job in active_jobs:
        job_dict = dict(job)
        total_expected += job_dict['expected_reward']
        
        # Check if job is completed
        cursor.execute('''
            SELECT datetime('now') >= ?
        ''', (job_dict['end_time'],))
        
        is_ready = cursor.fetchone()[0]
        
        if is_ready:
            ready_count += 1
        else:
            working_count += 1
    
    return {
        'has_active_jobs': True,
        'workers_count': len(active_jobs),
        'total_expected': total_expected,
        'ready_to_collect': ready_count,
        'still_working': working_count
    }

def buy_self_freedom(user_id: int) -> Tuple[bool, str]:
    """Allow prisoner to buy their own freedom"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    user = get_user(user_id)
    if not user:
        return False, "Пользователь не найден!"
    
    # Check if user is actually owned by someone
    if not user['owner_id']:
        return False, "Ты уже свободен! 🆓"
    
    # Check if user has enough money to buy themselves
    freedom_price = user['price']
    if user['balance'] < freedom_price:
        return False, f"Недостаточно монет для самовыкупа! Нужно {freedom_price}, а у тебя {user['balance']} монет. 💸"
    
    # Check if shield is active
    if user.get('shield_active') and user.get('shield_until'):
        cursor.execute('SELECT datetime("now") < ?', (user['shield_until'],))
        shield_active = cursor.fetchone()[0]
        if shield_active:
            return False, "На тебе стоит защитный щит! Самовыкуп невозможен до его истечения. 🛡️"
    
    old_owner_id = user['owner_id']
    
    # Remove ownership and deduct money
    cursor.execute('''
        UPDATE users SET owner_id = NULL, balance = balance - ? WHERE telegram_id = ?
    ''', (freedom_price, user_id))
    
    # Add ownership history
    cursor.execute('''
        INSERT INTO ownership_history (prisoner_id, old_owner_id, new_owner_id, price)
        VALUES (?, ?, NULL, ?)
    ''', (user_id, old_owner_id, freedom_price))
    
    # Log transaction
    cursor.execute('''
        INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type, description)
        VALUES (?, NULL, ?, 'self_buyout', 'Самовыкуп из тюрьмы')
    ''', (user_id, freedom_price))
    
    conn.commit()
    
    return True, f"🆓 Поздравляю! Ты выкупил свою свободу за {freedom_price} монет!\nТеперь ты свободен и никому не принадлежишь!"

def activate_shield(owner_id: int, prisoner_id: int) -> Tuple[bool, str]:
    """Activate protection shield for a prisoner"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if owner actually owns this prisoner
    prisoner = get_user(prisoner_id)
    if not prisoner or prisoner['owner_id'] != owner_id:
        return False, "Этот заключённый тебе не принадлежит! 🚫"
    
    # Check if shield is already active
    if prisoner.get('shield_active') and prisoner.get('shield_until'):
        cursor.execute('SELECT datetime("now") < ?', (prisoner['shield_until'],))
        shield_active = cursor.fetchone()[0]
        if shield_active:
            return False, "На этом заключённом уже стоит активный щит! 🛡️"
    
    # Calculate shield cost (35% of prisoner's price)
    shield_cost = int(prisoner['price'] * 0.35)
    
    # Check owner's balance
    owner = get_user(owner_id)
    if owner['balance'] < shield_cost:
        return False, f"Недостаточно монет для активации щита! Нужно {shield_cost}, а у тебя {owner['balance']} монет. 💸"
    
    # Activate shield for 24 hours
    cursor.execute('''
        UPDATE users 
        SET shield_active = TRUE, shield_until = datetime('now', '+24 hours')
        WHERE telegram_id = ?
    ''', (prisoner_id,))
    
    # Deduct cost from owner
    cursor.execute('''
        UPDATE users SET balance = balance - ? WHERE telegram_id = ?
    ''', (shield_cost, owner_id))
    
    # Log transaction
    cursor.execute('''
        INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type, description)
        VALUES (?, ?, ?, 'shield_activation', 'Активация защитного щита')
    ''', (owner_id, prisoner_id, shield_cost))
    
    conn.commit()
    
    prisoner_name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner_id}"
    
    return True, f"🛡️ Защитный щит активирован!\nЗаключённый: @{prisoner_name}\nСтоимость: {shield_cost} монет\nДействует: 24 часа"

def get_prisoner_upgrade_info(prisoner_id: int) -> Dict:
    """Get upgrade information for a prisoner"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT upgrade_level, income_multiplier, upgrade_cost, total_invested
        FROM prisoner_upgrades 
        WHERE prisoner_id = ?
    ''', (prisoner_id,))
    
    result = cursor.fetchone()
    if result:
        return {
            'level': result[0],
            'multiplier': result[1],
            'next_cost': result[2],
            'total_invested': result[3]
        }
    else:
        # Create initial upgrade record
        cursor.execute('''
            INSERT INTO prisoner_upgrades (prisoner_id, upgrade_level, income_multiplier, upgrade_cost)
            VALUES (?, 1, 1.0, 100)
        ''', (prisoner_id,))
        conn.commit()
        return {
            'level': 1,
            'multiplier': 1.0,
            'next_cost': 100,
            'total_invested': 0
        }

def upgrade_prisoner(owner_id: int, prisoner_id: int) -> Tuple[bool, str]:
    """Upgrade a prisoner to increase their income generation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if owner actually owns this prisoner
    prisoner = get_user(prisoner_id)
    if not prisoner or prisoner['owner_id'] != owner_id:
        return False, "Ты не владеешь этим заключённым!"
    
    # Get current upgrade info
    upgrade_info = get_prisoner_upgrade_info(prisoner_id)
    upgrade_cost = upgrade_info['next_cost']
    
    # Check owner's balance
    owner = get_user(owner_id)
    if owner['balance'] < upgrade_cost:
        return False, f"Недостаточно монет! Нужно {upgrade_cost} монет для улучшения."
    
    # Calculate new stats
    new_level = upgrade_info['level'] + 1
    new_multiplier = round(upgrade_info['multiplier'] * 1.2, 2)  # 20% increase per level
    new_upgrade_cost = int(upgrade_cost * 1.5)  # Cost increases by 50% each level
    new_total_invested = upgrade_info['total_invested'] + upgrade_cost
    
    # Update owner's balance
    cursor.execute('''
        UPDATE users SET balance = balance - ? WHERE telegram_id = ?
    ''', (upgrade_cost, owner_id))
    
    # Update upgrade info
    cursor.execute('''
        UPDATE prisoner_upgrades 
        SET upgrade_level = ?, income_multiplier = ?, upgrade_cost = ?, 
            total_invested = ?, last_upgraded = CURRENT_TIMESTAMP
        WHERE prisoner_id = ?
    ''', (new_level, new_multiplier, new_upgrade_cost, new_total_invested, prisoner_id))
    
    # Update prisoner's price based on investment
    price_increase = int(upgrade_cost * 0.8)  # 80% of upgrade cost added to price
    cursor.execute('''
        UPDATE users SET price = price + ? WHERE telegram_id = ?
    ''', (price_increase, prisoner_id))
    
    # Log transaction
    cursor.execute('''
        INSERT INTO transactions (from_user_id, to_user_id, amount, transaction_type, description)
        VALUES (?, ?, ?, 'upgrade', 'Улучшение заключённого')
    ''', (owner_id, prisoner_id, upgrade_cost))
    
    conn.commit()
    
    return True, f"✅ Заключённый улучшен до уровня {new_level}! Множитель дохода: ×{new_multiplier}"

def log_profit_data(user_id: int, profit_generated: int, profit_received: int):
    """Log profit data for pricing calculations"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if there's a record for today
    cursor.execute('''
        SELECT id, profit_generated, profit_received 
        FROM profit_log 
        WHERE user_id = ? AND DATE(period_end) = DATE('now')
    ''', (user_id,))
    
    result = cursor.fetchone()
    if result:
        # Update existing record
        new_generated = result[1] + profit_generated
        new_received = result[2] + profit_received
        cursor.execute('''
            UPDATE profit_log 
            SET profit_generated = ?, profit_received = ?, period_end = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_generated, new_received, result[0]))
    else:
        # Create new record
        cursor.execute('''
            INSERT INTO profit_log (user_id, profit_generated, profit_received, period_start)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, profit_generated, profit_received))
    
    conn.commit()

def get_profit_statistics(user_id: int) -> Dict:
    """Get profit statistics for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get last 7 days profit data
    cursor.execute('''
        SELECT 
            COALESCE(SUM(profit_generated), 0) as total_generated,
            COALESCE(SUM(profit_received), 0) as total_received,
            COALESCE(AVG(profit_generated), 0) as avg_generated,
            COALESCE(AVG(profit_received), 0) as avg_received,
            COUNT(*) as days_active
        FROM profit_log 
        WHERE user_id = ? AND period_end > datetime('now', '-7 days')
    ''', (user_id,))
    
    result = cursor.fetchone()
    if result:
        return {
            'total_generated': int(result[0]),
            'total_received': int(result[1]),
            'avg_generated': int(result[2]),
            'avg_received': int(result[3]),
            'days_active': result[4],
            'net_profit': int(result[1] - result[0])  # received - generated
        }
    else:
        return {
            'total_generated': 0,
            'total_received': 0,
            'avg_generated': 0,
            'avg_received': 0,
            'days_active': 0,
            'net_profit': 0
        }

def check_shield_status(user_id: int) -> Dict:
    """Check shield status for a user"""
    user = get_user(user_id)
    if not user:
        return {'has_shield': False, 'time_left': 0}
    
    if not user.get('shield_active') or not user.get('shield_until'):
        return {'has_shield': False, 'time_left': 0}
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if shield is still active
    cursor.execute('''
        SELECT 
            datetime("now") < ?,
            CAST((julianday(?) - julianday("now")) * 24 AS INTEGER) as hours_left
    ''', (user['shield_until'], user['shield_until']))
    
    result = cursor.fetchone()
    is_active = result[0]
    hours_left = max(0, result[1]) if result[1] else 0
    
    # If shield expired, deactivate it
    if not is_active:
        cursor.execute('''
            UPDATE users SET shield_active = FALSE, shield_until = NULL WHERE telegram_id = ?
        ''', (user_id,))
        conn.commit()
        return {'has_shield': False, 'time_left': 0}
    
    return {'has_shield': True, 'time_left': hours_left}
