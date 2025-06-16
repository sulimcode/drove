#!/usr/bin/env python3
"""
Telegram Bot: Durov's Prison Game
Main entry point for the bot application
"""

import os
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import init_database
from bot_handlers import (
    start_handler, button_handler, message_handler, 
    referral_handler, help_handler, set_bot_instance
)
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the bot"""
    # Bot token - directly embedded for reliability
    bot_token = "7708193142:AAE6stASmZ9VKhSJ9v9jEZ4F92kgvfun-J4"
    
    # Fallback to environment variable if needed
    if not bot_token:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        logger.error("Bot token not available!")
        return
    
    # Initialize database
    init_database()
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Set bot instance for notifications
    set_bot_instance(application.bot)
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Start background scheduler for hourly income
    start_scheduler()
    
    logger.info("🚨 Тюрьма Дурова запущена! Bot started successfully!")
    
    # Start the bot
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
