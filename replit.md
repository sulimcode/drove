# Durov's Prison Bot

## Overview

This is a Telegram bot implementation of a prison-themed social game called "Durov's Prison" (Тюрьма Дурова), based on the mechanics of "SLAVERY 2.0". Players become prisoners who can buy, sell, and manage other player-prisoners while earning virtual currency through an economic system with hourly income generation.

The bot is built using Python with the `python-telegram-bot` library and uses SQLite for data persistence. It features a complete game economy with user profiles, prisoner ownership, money transfers, referral systems, work mechanics, and leaderboards.

## System Architecture

### Backend Architecture
- **Framework**: Python-based Telegram bot using `python-telegram-bot` library
- **Database**: SQLite with thread-local connections for concurrent access
- **Scheduler**: APScheduler for background tasks (hourly income, market updates)
- **Game Logic**: Modular design with separated concerns for database, game mechanics, and bot handlers

### Key Design Patterns
- **Handler Pattern**: Separate handlers for different bot interactions (commands, callbacks, messages)
- **Repository Pattern**: Database operations abstracted into dedicated functions
- **State Management**: User conversation states tracked in memory
- **Notification System**: Global bot instance for sending notifications to users

## Key Components

### 1. Database Layer (`database.py`)
- **User Management**: Create, retrieve, and update user profiles
- **Ownership System**: Track prisoner ownership and history
- **Economic System**: Handle balance transfers, purchases, and income generation
- **Referral System**: Manage referral codes and relationships
- **Work System**: Track prisoner work status and rewards
- **Shield System**: Implement protection mechanics for valuable prisoners

### 2. Bot Handlers (`bot_handlers.py`)
- **Command Handlers**: Process `/start` and `/help` commands
- **Callback Handlers**: Handle inline keyboard button presses
- **Message Handlers**: Process text input during conversations
- **State Management**: Track user conversation states for multi-step operations

### 3. Game Logic (`game_logic.py`)
- **Economic Calculations**: Price increases, hourly income, empire valuations
- **Game Constants**: Starting balances, price multipliers, income ranges
- **Business Rules**: Purchase validation, transfer fees, market mechanics

### 4. User Interface (`keyboards.py`, `messages.py`)
- **Keyboard Layouts**: Inline keyboards for different game sections
- **Message Templates**: Localized Russian text for all bot responses
- **Dynamic Content**: Context-aware button generation based on game state

### 5. Background Scheduler (`scheduler.py`)
- **Hourly Income**: Automatic income generation for prisoner owners
- **Market Updates**: Periodic price fluctuations and statistics updates
- **Maintenance Tasks**: Database cleanup and optimization

## Data Flow

### User Registration Flow
1. User starts bot with `/start` command
2. System checks for referral code in start parameter
3. New user created with default balance (300 coins) and price (100 coins)
4. If referral exists, user automatically becomes prisoner of referrer
5. Welcome message displayed with main menu

### Purchase Flow
1. User searches for prisoners via "Find Prisoner" menu
2. Random prisoners displayed with current prices
3. User selects prisoner to purchase
4. System validates sufficient balance and ownership rules
5. Transaction processed: balance deducted, ownership transferred, price increased
6. Notifications sent to relevant parties

### Income Generation Flow
1. Scheduler runs hourly income generation
2. System calculates income for each prisoner owner (1-3 coins per prisoner per hour)
3. Balances updated in database
4. Optional notifications sent to users about income

## External Dependencies

### Core Dependencies
- **python-telegram-bot (v20.8)**: Telegram Bot API wrapper
- **apscheduler (v3.11.0)**: Background task scheduling
- **sqlite3**: Built-in Python database (no external dependency)

### System Dependencies
- **Python 3.11+**: Runtime environment
- **Threading**: Concurrent request handling
- **Logging**: Application monitoring and debugging

## Deployment Strategy

### Replit Deployment
- **Configuration**: Defined in `.replit` file with Python 3.11 module
- **Workflow**: Automated installation of dependencies and bot startup
- **Command**: `pip install python-telegram-bot apscheduler && python main.py`

### Database Strategy
- **File-based SQLite**: `durov_prison.db` stored in project directory
- **Thread-safe Access**: Thread-local connections for concurrent operations
- **Auto-initialization**: Database schema created on first run

### Bot Token Management
- **Primary**: Hardcoded token in `main.py` for reliability
- **Fallback**: Environment variable `TELEGRAM_BOT_TOKEN`
- **Security Note**: Token should be moved to environment variables in production

### Scaling Considerations
- **Current Limitations**: Single-instance deployment, file-based database
- **Future Improvements**: Could migrate to PostgreSQL for better concurrency
- **Monitoring**: Comprehensive logging system for debugging and performance tracking

## Recent Changes
- June 16, 2025: **CRITICAL FIXES APPLIED** - Resolved major functionality issues:
  - Fixed admin commands not working due to incorrect handler registration in main.py
  - Added regex-based filter for proper admin text command recognition
  - Improved admin command processing with better error handling and logging
  - Fixed user purchase functionality with enhanced logging for debugging
  - Added safety checks to prevent null pointer exceptions in bot handlers
  - All admin functions (addcoins, setcoins, setpoints, /users, /user) now working correctly
  - User purchase system fully operational with proper transaction processing
- June 16, 2025: Added advanced search and sorting functionality to prisoner finder
- Implemented prisoner search by username/first name with partial matching
- Added price-based sorting (ascending/descending) and random selection options
- Created dedicated search menu with intuitive navigation
- Enhanced user experience with search state management and result display
- Integrated search results with existing prisoner profile system
- Added comprehensive keyboard layouts for search operations
- June 16, 2025: Complete database reset performed - all test users and data cleared for fresh start with real players only
- June 16, 2025: Implemented comprehensive admin system for @ceosulim with following features:
  - Admin-only /admin command with full user management interface
  - Database functions: admin_add_coins, admin_set_coins, admin_set_points, admin_get_all_users, admin_get_user_by_username
  - Admin commands: /users (list all users), /user @username (view specific user), addcoins/setcoins/setpoints (modify user data)
  - Added 5,000,000 coins to @ceosulim account (total balance: 10,000,302 coins)
  - Integrated admin handlers into main bot application with proper command routing

## Changelog
- June 16, 2025. Initial setup
- June 16, 2025. Dynamic pricing system implementation

## User Preferences

Preferred communication style: Simple, everyday language.