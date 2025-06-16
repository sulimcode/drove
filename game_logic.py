"""
Game logic and calculations for Durov's Prison
Handles complex game mechanics and business logic
"""

import random
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from database import (
    get_user, update_user_balance, get_my_prisoners, 
    get_db_connection, get_random_prisoners
)

logger = logging.getLogger(__name__)

class GameLogic:
    """Core game logic handler"""
    
    # Game constants
    STARTING_BALANCE = 300
    STARTING_PRICE = 100
    PRICE_INCREASE_MULTIPLIER = 1.3
    MIN_HOURLY_INCOME = 1
    MAX_HOURLY_INCOME = 3
    TRANSFER_FEE_PERCENT = 0  # No transfer fee for now
    
    @staticmethod
    def calculate_hourly_income(prisoner_count: int) -> int:
        """Calculate hourly income based on prisoner count"""
        if prisoner_count == 0:
            return 0
        
        total_income = 0
        for _ in range(prisoner_count):
            # Each prisoner generates 1-3 coins per hour
            income = random.randint(GameLogic.MIN_HOURLY_INCOME, GameLogic.MAX_HOURLY_INCOME)
            total_income += income
            
        return total_income
    
    @staticmethod
    def calculate_new_price(current_price: int) -> int:
        """Calculate new price after purchase (30% increase)"""
        return int(current_price * GameLogic.PRICE_INCREASE_MULTIPLIER)
    
    @staticmethod
    def calculate_dynamic_price(user_id: int) -> int:
        """Calculate dynamic price based on trading history, income stability, and prisoner parameters"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        user = get_user(user_id)
        if not user:
            return GameLogic.STARTING_PRICE
        
        base_price = user['price']
        
        # Factor 1: Trading History (Liquidity)
        liquidity_multiplier = GameLogic._calculate_liquidity_multiplier(user_id, cursor)
        
        # Factor 2: Income Stability
        stability_multiplier = GameLogic._calculate_income_stability_multiplier(user_id, cursor)
        
        # Factor 3: Prisoner Empire Parameters
        empire_multiplier = GameLogic._calculate_empire_multiplier(user_id, cursor)
        
        # Factor 4: Profit Performance
        profit_multiplier = GameLogic._calculate_profit_multiplier(user_id, cursor)
        
        # Combine all multipliers (cap at reasonable limits)
        total_multiplier = min(4.0, max(0.5, liquidity_multiplier * stability_multiplier * empire_multiplier * profit_multiplier))
        
        new_price = int(base_price * total_multiplier)
        
        # Ensure minimum price
        return max(50, new_price)
    
    @staticmethod
    def _calculate_liquidity_multiplier(user_id: int, cursor) -> float:
        """Calculate price multiplier based on trading history"""
        # Get trading frequency (how many times bought/sold)
        cursor.execute('''
            SELECT COUNT(*) as trade_count,
                   AVG(price) as avg_historical_price,
                   MAX(price) as max_historical_price
            FROM ownership_history 
            WHERE prisoner_id = ?
            AND timestamp > datetime('now', '-30 days')
        ''', (user_id,))
        
        result = cursor.fetchone()
        trade_count = result[0] if result else 0
        avg_historical_price = result[1] if result and result[1] else 0
        max_historical_price = result[2] if result and result[2] else 0
        
        # Base multiplier from trading frequency
        if trade_count == 0:
            frequency_multiplier = 1.0  # No trading history
        elif trade_count <= 2:
            frequency_multiplier = 1.05  # Low activity
        elif trade_count <= 5:
            frequency_multiplier = 1.15  # Medium activity
        else:
            frequency_multiplier = 1.25  # High liquidity
        
        # Price trend multiplier
        current_user = get_user(user_id)
        current_price = current_user['price'] if current_user else 0
        
        if avg_historical_price > 0 and current_price > avg_historical_price:
            trend_multiplier = 1.1  # Price increasing trend
        elif max_historical_price > 0 and current_price > max_historical_price:
            trend_multiplier = 1.2  # New high price
        else:
            trend_multiplier = 1.0
        
        return frequency_multiplier * trend_multiplier
    
    @staticmethod
    def _calculate_income_stability_multiplier(user_id: int, cursor) -> float:
        """Calculate price multiplier based on income stability"""
        # Get income history for last 7 days
        cursor.execute('''
            SELECT amount, timestamp
            FROM income_log 
            WHERE user_id = ?
            AND timestamp > datetime('now', '-7 days')
            ORDER BY timestamp DESC
        ''', (user_id,))
        
        income_records = cursor.fetchall()
        
        if len(income_records) < 3:
            return 1.0  # Not enough data
        
        amounts = [record[0] for record in income_records]
        avg_income = sum(amounts) / len(amounts)
        
        # Calculate income stability (lower variance = more stable)
        variance = sum((x - avg_income) ** 2 for x in amounts) / len(amounts)
        stability_score = max(0, 100 - variance)  # Higher score = more stable
        
        # Convert stability to multiplier
        if stability_score >= 80:
            stability_multiplier = 1.3  # Very stable income
        elif stability_score >= 60:
            stability_multiplier = 1.2  # Stable income
        elif stability_score >= 40:
            stability_multiplier = 1.1  # Moderately stable
        else:
            stability_multiplier = 1.0  # Unstable income
        
        # Bonus for consistent daily income
        daily_income_count = len(set(record[1][:10] for record in income_records))  # Count unique days
        if daily_income_count >= 5:  # Income for 5+ different days
            stability_multiplier *= 1.1
        
        return stability_multiplier
    
    @staticmethod
    def _calculate_empire_multiplier(user_id: int, cursor) -> float:
        """Calculate price multiplier based on prisoner count and their parameters"""
        from database import get_prisoner_upgrade_info
        
        prisoners = get_my_prisoners(user_id)
        prisoner_count = len(prisoners)
        
        if prisoner_count == 0:
            return 0.9  # No prisoners = lower value
        
        # Base multiplier from prisoner count
        if prisoner_count >= 20:
            count_multiplier = 1.4  # Large empire
        elif prisoner_count >= 10:
            count_multiplier = 1.3  # Medium empire
        elif prisoner_count >= 5:
            count_multiplier = 1.2  # Small empire
        else:
            count_multiplier = 1.1  # Few prisoners
        
        # Calculate average prisoner value including upgrades
        total_prisoner_value = 0
        total_upgrade_investment = 0
        
        for prisoner in prisoners:
            prisoner_value = prisoner['price']
            upgrade_info = get_prisoner_upgrade_info(prisoner['telegram_id'])
            upgrade_investment = upgrade_info['total_invested']
            
            total_prisoner_value += prisoner_value
            total_upgrade_investment += upgrade_investment
        
        avg_prisoner_value = total_prisoner_value / prisoner_count if prisoner_count > 0 else 0
        avg_upgrade_investment = total_upgrade_investment / prisoner_count if prisoner_count > 0 else 0
        
        # Quality multiplier based on average prisoner value
        if avg_prisoner_value >= 500:
            quality_multiplier = 1.3  # High-value prisoners
        elif avg_prisoner_value >= 300:
            quality_multiplier = 1.2  # Medium-value prisoners
        elif avg_prisoner_value >= 150:
            quality_multiplier = 1.1  # Average prisoners
        else:
            quality_multiplier = 1.0  # Low-value prisoners
        
        # Upgrade investment multiplier
        if avg_upgrade_investment >= 1000:
            upgrade_multiplier = 1.4  # Heavy upgrader
        elif avg_upgrade_investment >= 500:
            upgrade_multiplier = 1.3  # Active upgrader
        elif avg_upgrade_investment >= 200:
            upgrade_multiplier = 1.2  # Some upgrades
        elif avg_upgrade_investment >= 50:
            upgrade_multiplier = 1.1  # Basic upgrades
        else:
            upgrade_multiplier = 1.0  # No upgrades
        
        # Calculate empire growth trend (comparing recent vs older acquisitions)
        cursor.execute('''
            SELECT price, timestamp
            FROM ownership_history 
            WHERE new_owner_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        ''', (user_id,))
        
        recent_purchases = cursor.fetchall()
        growth_multiplier = 1.0
        
        if len(recent_purchases) >= 5:
            recent_avg = sum(p[0] for p in recent_purchases[:3]) / 3
            older_avg = sum(p[0] for p in recent_purchases[3:6]) / 3 if len(recent_purchases) >= 6 else recent_avg
            
            if recent_avg > older_avg * 1.2:  # Buying increasingly expensive prisoners
                growth_multiplier = 1.15
        
        return count_multiplier * quality_multiplier * upgrade_multiplier * growth_multiplier
    
    @staticmethod
    def _calculate_profit_multiplier(user_id: int, cursor) -> float:
        """Calculate price multiplier based on profit generation and efficiency"""
        from database import get_profit_statistics
        
        profit_stats = get_profit_statistics(user_id)
        
        # Profit generation multiplier (how much money user generates for owners)
        avg_generated = profit_stats['avg_generated']
        if avg_generated >= 100:
            generation_multiplier = 1.4  # High profit generator
        elif avg_generated >= 50:
            generation_multiplier = 1.3  # Good profit generator
        elif avg_generated >= 20:
            generation_multiplier = 1.2  # Decent profit generator
        elif avg_generated >= 10:
            generation_multiplier = 1.1  # Some profit generation
        else:
            generation_multiplier = 1.0  # Low/no profit generation
        
        # Profit efficiency multiplier (net profit - received vs generated)
        net_profit = profit_stats['net_profit']
        if net_profit >= 200:
            efficiency_multiplier = 1.3  # Very profitable to own
        elif net_profit >= 100:
            efficiency_multiplier = 1.2  # Profitable to own
        elif net_profit >= 50:
            efficiency_multiplier = 1.15  # Moderately profitable
        elif net_profit >= 0:
            efficiency_multiplier = 1.1  # Break-even or small profit
        else:
            efficiency_multiplier = 0.9  # Loss-making (costs more than generates)
        
        # Activity consistency multiplier
        days_active = profit_stats['days_active']
        if days_active >= 6:
            consistency_multiplier = 1.2  # Very consistent
        elif days_active >= 4:
            consistency_multiplier = 1.15  # Good consistency
        elif days_active >= 2:
            consistency_multiplier = 1.1  # Some consistency
        else:
            consistency_multiplier = 1.0  # Inconsistent activity
        
        return generation_multiplier * efficiency_multiplier * consistency_multiplier
    
    @staticmethod
    def calculate_empire_value(user_id: int) -> Dict[str, int]:
        """Calculate total empire value for a user"""
        prisoners = get_my_prisoners(user_id)
        
        total_value = 0
        prisoner_count = len(prisoners)
        
        for prisoner in prisoners:
            total_value += prisoner['price']
        
        return {
            'prisoner_count': prisoner_count,
            'total_value': total_value,
            'avg_price': total_value // prisoner_count if prisoner_count > 0 else 0
        }
    
    @staticmethod
    def get_user_rank(user_id: int, category: str = 'prisoners') -> Dict[str, int]:
        """Get user's rank in different categories"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if category == 'prisoners':
            cursor.execute('''
                SELECT user_rank.telegram_id, user_rank.prisoner_count, 
                       ROW_NUMBER() OVER (ORDER BY user_rank.prisoner_count DESC) as rank
                FROM (
                    SELECT u.telegram_id, COUNT(p.telegram_id) as prisoner_count
                    FROM users u
                    LEFT JOIN users p ON u.telegram_id = p.owner_id
                    GROUP BY u.telegram_id
                ) user_rank
                WHERE user_rank.telegram_id = ?
            ''', (user_id,))
        elif category == 'balance':
            cursor.execute('''
                SELECT telegram_id, balance,
                       ROW_NUMBER() OVER (ORDER BY balance DESC) as rank
                FROM users
                WHERE telegram_id = ?
            ''', (user_id,))
        elif category == 'value':
            cursor.execute('''
                SELECT user_rank.telegram_id, user_rank.total_value,
                       ROW_NUMBER() OVER (ORDER BY user_rank.total_value DESC) as rank
                FROM (
                    SELECT u.telegram_id, COALESCE(SUM(p.price), 0) as total_value
                    FROM users u
                    LEFT JOIN users p ON u.telegram_id = p.owner_id
                    GROUP BY u.telegram_id
                ) user_rank
                WHERE user_rank.telegram_id = ?
            ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            return dict(result)
        return {'rank': 0}
    
    @staticmethod
    def calculate_transfer_fee(amount: int) -> int:
        """Calculate transfer fee (currently 0%)"""
        return int(amount * GameLogic.TRANSFER_FEE_PERCENT / 100)
    
    @staticmethod
    def validate_purchase(buyer_id: int, prisoner_id: int) -> Tuple[bool, str]:
        """Validate if purchase can be made"""
        buyer = get_user(buyer_id)
        prisoner = get_user(prisoner_id)
        
        if not buyer or not prisoner:
            return False, "Пользователь не найден! 👻"
        
        if buyer_id == prisoner_id:
            return False, "Нельзя купить самого себя, гений! 🤡"
        
        if prisoner['owner_id'] == buyer_id:
            return False, "Этот зэк уже твой! 🔐"
        
        if buyer['balance'] < prisoner['price']:
            return False, f"Недостаточно монет! Нужно {prisoner['price']}, а у тебя {buyer['balance']} 💸"
        
        return True, "OK"
    
    @staticmethod
    def calculate_daily_stats(user_id: int) -> Dict[str, int]:
        """Calculate daily statistics for user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get today's income
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) as daily_income
            FROM income_log
            WHERE user_id = ? AND DATE(timestamp) = DATE('now')
        ''', (user_id,))
        
        daily_income = cursor.fetchone()[0]
        
        # Get today's transactions
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'purchase' THEN amount ELSE 0 END), 0) as spent,
                COALESCE(SUM(CASE WHEN transaction_type = 'sale' THEN amount ELSE 0 END), 0) as earned
            FROM transactions
            WHERE from_user_id = ? AND DATE(timestamp) = DATE('now')
        ''', (user_id,))
        
        result = cursor.fetchone()
        daily_spent = result[0] if result else 0
        daily_earned = result[1] if result else 0
        
        return {
            'daily_income': daily_income,
            'daily_spent': daily_spent,
            'daily_earned': daily_earned,
            'daily_profit': daily_income + daily_earned - daily_spent
        }
    
    @staticmethod
    def get_market_statistics() -> Dict[str, int]:
        """Get overall market statistics"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # Average price
        cursor.execute('SELECT AVG(price) FROM users')
        avg_price = int(cursor.fetchone()[0] or 0)
        
        # Total transactions today
        cursor.execute('''
            SELECT COUNT(*) FROM transactions 
            WHERE DATE(timestamp) = DATE('now')
        ''')
        daily_transactions = cursor.fetchone()[0]
        
        # Most expensive prisoner
        cursor.execute('SELECT MAX(price) FROM users')
        max_price = cursor.fetchone()[0] or 0
        
        return {
            'total_users': total_users,
            'avg_price': avg_price,
            'daily_transactions': daily_transactions,
            'max_price': max_price
        }
    
    @staticmethod
    def generate_random_event(user_id: int) -> Optional[Dict[str, Any]]:
        """Generate random events for users (future feature)"""
        # Placeholder for future random events like:
        # - Prisoner escape (lose prisoner)
        # - Bonus income
        # - Price fluctuations
        # - Special offers
        
        events = [
            {
                'type': 'bonus_income',
                'message': '🎰 Бонус! Ты получил дополнительный доход!',
                'amount': random.randint(10, 50)
            },
            {
                'type': 'price_boost',
                'message': '📈 Твоя стоимость выросла на рынке!',
                'multiplier': 1.1
            }
        ]
        
        # 5% chance of random event
        if random.random() < 0.05:
            return random.choice(events)
        
        return None
    
    @staticmethod
    def check_achievements(user_id: int) -> List[Dict[str, str]]:
        """Check for user achievements (future feature)"""
        achievements = []
        
        user = get_user(user_id)
        prisoners = get_my_prisoners(user_id)
        empire_value = GameLogic.calculate_empire_value(user_id)
        
        # Achievement: First prisoner
        if len(prisoners) == 1:
            achievements.append({
                'title': '👑 Первый подчинённый',
                'description': 'Ты купил своего первого заключённого!'
            })
        
        # Achievement: Rich user
        if user and user['balance'] >= 1000:
            achievements.append({
                'title': '💰 Богач',
                'description': 'У тебя больше 1000 монет!'
            })
        
        # Achievement: Empire builder
        if len(prisoners) >= 10:
            achievements.append({
                'title': '🏛️ Строитель империи',
                'description': 'У тебя 10 или больше заключённых!'
            })
        
        return achievements
    
    @staticmethod
    def simulate_market_fluctuation():
        """Simulate market price fluctuations (future feature)"""
        # This could randomly adjust all user prices by small amounts
        # to simulate market dynamics
        pass
    
    @staticmethod
    def get_recommended_targets(user_id: int, count: int = 3) -> List[Dict]:
        """Get recommended prisoners to buy based on user's strategy"""
        user = get_user(user_id)
        if not user:
            return []
        
        # Get prisoners in user's price range
        max_price = min(user['balance'], user['balance'] * 0.8)  # Don't spend all money
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT telegram_id, username, first_name, price, owner_id
            FROM users 
            WHERE telegram_id != ? 
            AND price <= ?
            AND owner_id != ?
            ORDER BY 
                CASE 
                    WHEN owner_id IS NULL THEN 1  -- Prefer free prisoners
                    ELSE 2 
                END,
                price ASC  -- Then by price
            LIMIT ?
        ''', (user_id, max_price, user_id, count))
        
        return [dict(row) for row in cursor.fetchall()]

# Game statistics and analytics
class GameAnalytics:
    """Analytics and statistics for the game"""
    
    @staticmethod
    def get_user_activity_score(user_id: int) -> int:
        """Calculate user activity score"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Count recent transactions
        cursor.execute('''
            SELECT COUNT(*) FROM transactions 
            WHERE (from_user_id = ? OR to_user_id = ?)
            AND timestamp > datetime('now', '-7 days')
        ''', (user_id, user_id))
        
        recent_transactions = cursor.fetchone()[0]
        
        # Get prisoner count
        prisoners = get_my_prisoners(user_id)
        prisoner_count = len(prisoners)
        
        # Calculate score
        activity_score = recent_transactions * 10 + prisoner_count * 5
        
        return activity_score
    
    @staticmethod
    def get_top_traders(limit: int = 10) -> List[Dict]:
        """Get top traders by transaction volume"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.telegram_id, u.username, u.first_name,
                   COUNT(t.id) as transaction_count,
                   COALESCE(SUM(t.amount), 0) as total_volume
            FROM users u
            LEFT JOIN transactions t ON (u.telegram_id = t.from_user_id OR u.telegram_id = t.to_user_id)
            WHERE t.timestamp > datetime('now', '-30 days')
            GROUP BY u.telegram_id
            ORDER BY total_volume DESC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
