"""
Background scheduler for Durov's Prison game
Handles periodic tasks like hourly income generation
"""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from database import generate_hourly_income, get_db_connection
from game_logic import GameLogic

logger = logging.getLogger(__name__)

scheduler = None

def start_scheduler():
    """Start the background scheduler"""
    global scheduler
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        
        # Hourly income generation (every hour)
        scheduler.add_job(
            generate_hourly_income,  # Use sync version
            trigger=IntervalTrigger(hours=1),
            id='hourly_income',
            name='Generate hourly income for all users',
            replace_existing=True
        )
        
        # Daily statistics update (at midnight)
        scheduler.add_job(
            update_daily_statistics_sync,
            trigger=CronTrigger(hour=0, minute=0),
            id='daily_stats',
            name='Update daily statistics',
            replace_existing=True
        )
        
        # Market fluctuation simulation (every 6 hours)
        scheduler.add_job(
            simulate_market_changes_sync,
            trigger=IntervalTrigger(hours=6),
            id='market_fluctuation',
            name='Simulate market price changes',
            replace_existing=True
        )
        
        # Dynamic price updates (every 4 hours)
        scheduler.add_job(
            update_dynamic_prices_sync,
            trigger=IntervalTrigger(hours=4),
            id='dynamic_pricing',
            name='Update dynamic player prices',
            replace_existing=True
        )
        
        # Database cleanup (weekly)
        scheduler.add_job(
            cleanup_old_data_sync,
            trigger=CronTrigger(day_of_week=0, hour=2, minute=0),  # Sunday at 2 AM
            id='weekly_cleanup',
            name='Clean up old data',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Background scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        # Continue without scheduler for now

def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")

def generate_hourly_income_job():
    """Job to generate hourly income for all users"""
    try:
        logger.info("Starting hourly income generation...")
        generate_hourly_income()
        logger.info("Hourly income generation completed")
    except Exception as e:
        logger.error(f"Error in hourly income generation: {e}")

def update_daily_statistics_sync():
    """Update daily statistics and leaderboards"""
    try:
        logger.info("Updating daily statistics...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create daily_stats table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_users INTEGER,
                total_transactions INTEGER,
                total_volume INTEGER,
                avg_price REAL,
                top_user_by_prisoners INTEGER,
                top_user_by_balance INTEGER
            )
        ''')
        
        # Create daily statistics snapshot
        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats (
                date, 
                total_users, 
                total_transactions, 
                total_volume,
                avg_price,
                top_user_by_prisoners,
                top_user_by_balance
            )
            SELECT 
                DATE('now') as date,
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM transactions WHERE DATE(timestamp) = DATE('now')) as total_transactions,
                (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE DATE(timestamp) = DATE('now')) as total_volume,
                (SELECT AVG(price) FROM users) as avg_price,
                (SELECT telegram_id FROM users u 
                 LEFT JOIN users p ON u.telegram_id = p.owner_id 
                 GROUP BY u.telegram_id 
                 ORDER BY COUNT(p.telegram_id) DESC 
                 LIMIT 1) as top_user_by_prisoners,
                (SELECT telegram_id FROM users ORDER BY balance DESC LIMIT 1) as top_user_by_balance
        ''')
        
        conn.commit()
        logger.info("Daily statistics updated successfully")
        
    except Exception as e:
        logger.error(f"Error updating daily statistics: {e}")

def simulate_market_changes_sync():
    """Simulate market price fluctuations"""
    try:
        logger.info("Simulating market changes...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Small random price adjustments (±5%) for market dynamics
        import random
        
        cursor.execute('SELECT telegram_id, price FROM users')
        users = cursor.fetchall()
        
        updates = []
        for user_id, current_price in users:
            # 20% chance of price change
            if random.random() < 0.2:
                change_factor = random.uniform(0.95, 1.05)  # ±5%
                new_price = max(50, int(current_price * change_factor))  # Minimum price 50
                updates.append((new_price, user_id))
        
        if updates:
            cursor.executemany('UPDATE users SET price = ? WHERE telegram_id = ?', updates)
            conn.commit()
            logger.info(f"Updated prices for {len(updates)} users")
        
    except Exception as e:
        logger.error(f"Error simulating market changes: {e}")

def update_dynamic_prices_sync():
    """Update all player prices based on dynamic factors"""
    try:
        logger.info("Updating dynamic prices for all players...")
        
        from game_logic import GameLogic
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute('SELECT telegram_id, price FROM users')
        users = cursor.fetchall()
        
        updates_count = 0
        for user_id, current_price in users:
            try:
                # Calculate new dynamic price
                new_price = GameLogic.calculate_dynamic_price(user_id)
                
                # Only update if price changed significantly (more than 5% difference)
                price_change_percent = abs(new_price - current_price) / current_price if current_price > 0 else 0
                
                if price_change_percent > 0.05:  # 5% threshold
                    cursor.execute('''
                        UPDATE users SET price = ? WHERE telegram_id = ?
                    ''', (new_price, user_id))
                    updates_count += 1
            
            except Exception as e:
                logger.error(f"Error updating price for user {user_id}: {e}")
                continue
        
        conn.commit()
        logger.info(f"Dynamic pricing update completed - updated {updates_count} players")
        
    except Exception as e:
        logger.error(f"Error updating dynamic prices: {e}")

def cleanup_old_data_sync():
    """Clean up old data to keep database size manageable"""
    try:
        logger.info("Starting database cleanup...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Keep only last 30 days of income logs
        cursor.execute('''
            DELETE FROM income_log 
            WHERE timestamp < datetime('now', '-30 days')
        ''')
        
        # Keep only last 90 days of transactions
        cursor.execute('''
            DELETE FROM transactions 
            WHERE timestamp < datetime('now', '-90 days')
            AND transaction_type != 'purchase'  -- Keep all purchase records
        ''')
        
        # Vacuum database to reclaim space
        cursor.execute('VACUUM')
        
        conn.commit()
        logger.info("Database cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during database cleanup: {e}")

# Keep async versions for manual triggers
async def generate_hourly_income_job_async():
    """Async job to generate hourly income for all users"""
    generate_hourly_income_job()

async def update_daily_statistics():
    """Async version of daily statistics update"""
    update_daily_statistics_sync()

async def simulate_market_changes():
    """Async version of market changes simulation"""
    simulate_market_changes_sync()

async def cleanup_old_data():
    """Async version of database cleanup"""
    cleanup_old_data_sync()

async def send_daily_report():
    """Send daily report to admin users (future feature)"""
    try:
        # This could send daily statistics to admin users
        # Implementation would require bot instance access
        pass
    except Exception as e:
        logger.error(f"Error sending daily report: {e}")

def get_scheduler_status():
    """Get current scheduler status"""
    global scheduler
    if scheduler:
        return {
            'running': scheduler.running,
            'jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in scheduler.get_jobs()
            ]
        }
    return {'running': False, 'jobs': []}

# Manual job triggers (for testing/admin purposes)
async def trigger_hourly_income():
    """Manually trigger hourly income generation"""
    await generate_hourly_income_job()

async def trigger_daily_stats():
    """Manually trigger daily statistics update"""
    await update_daily_statistics()

async def trigger_market_simulation():
    """Manually trigger market simulation"""
    await simulate_market_changes()
