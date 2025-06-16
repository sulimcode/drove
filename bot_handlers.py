"""
Bot handlers for Durov's Prison game
Handles all user interactions and bot commands
"""

import logging
from telegram import Update, Bot
from telegram.ext import ContextTypes
from database import (
    create_user, get_user, get_my_prisoners, get_random_prisoners,
    buy_prisoner, transfer_money, get_ownership_history, get_leaderboard,
    get_user_by_referral_code, update_user_info, send_prisoners_to_work,
    collect_work_rewards, get_work_status, buy_self_freedom, activate_shield,
    check_shield_status, get_db_connection, add_referral_points,
    get_sorted_prisoners, search_prisoners_by_username,
    admin_add_coins, admin_set_coins, admin_set_points, admin_get_all_users,
    admin_get_user_by_username
)
from keyboards import (
    get_main_menu, get_profile_keyboard, get_prisoners_keyboard,
    get_search_keyboard, get_transfer_keyboard, get_leaderboard_keyboard,
    get_back_keyboard, get_invite_keyboard, get_find_prisoner_menu_keyboard,
    get_search_results_keyboard, get_back_to_find_keyboard
)
from messages import *

logger = logging.getLogger(__name__)

# User states for conversation handling
user_states = {}

# Global bot instance for notifications
bot_instance = None

def set_bot_instance(bot):
    """Set the bot instance for notifications"""
    global bot_instance
    bot_instance = bot

async def send_notification(user_id: int, message: str):
    """Send notification to a user"""
    global bot_instance
    if bot_instance:
        try:
            await bot_instance.send_message(chat_id=user_id, text=message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to send notification to {user_id}: {e}")

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Check if it's a referral link
    referrer_id = None
    if context.args:
        referral_code = context.args[0]
        referrer = get_user_by_referral_code(referral_code)
        if referrer:
            referrer_id = referrer['telegram_id']
            logger.info(f"User {user.id} referred by {referrer_id}")
    
    # Update user info if they exist, or create new user
    existing_user = get_user(user.id)
    if existing_user:
        update_user_info(user.id, user.username, user.first_name)
        if referrer_id and not existing_user['owner_id']:
            # If user exists but has no owner, assign referrer as owner
            from database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET owner_id = ? WHERE telegram_id = ?', 
                         (referrer_id, user.id))
            conn.commit()
            
            # Send capture message to new user
            await update.message.reply_text(REFERRAL_CAPTURED_MESSAGE.format(
                referrer_name=referrer.get('username', 'Неизвестный')
            ))
            
            # Send notification to referrer
            captured_name = user.username or user.first_name or f"ID{user.id}"
            notification_text = REFERRAL_CAPTURED_NOTIFICATION.format(
                captured_user=captured_name
            )
            await send_notification(referrer_id, notification_text)
    else:
        create_user(user.id, user.username, user.first_name, referrer_id)
        if referrer_id:
            # Send capture message to new user
            await update.message.reply_text(REFERRAL_CAPTURED_MESSAGE.format(
                referrer_name=referrer.get('username', 'Неизвестный')
            ))
            
            # Send notification to referrer and award points
            captured_name = user.username or user.first_name or f"ID{user.id}"
            notification_text = REFERRAL_CAPTURED_NOTIFICATION.format(
                captured_user=captured_name
            )
            await send_notification(referrer_id, notification_text)
            
            # Award 1 point for successful referral
            add_referral_points(referrer_id)
    
    # Get user data for personalized message
    user_data = get_user(user.id)
    prisoners = get_my_prisoners(user.id)
    
    # Format owner info
    owner_info = ""
    if user_data and user_data['owner_id']:
        owner = get_user(user_data['owner_id'])
        if owner:
            owner_name = owner.get('username', f"ID{owner['telegram_id']}")
            owner_info = f"🧑‍💼 Владелец: @{owner_name}"
        else:
            owner_info = "🆓 Статус: Свободен"
    else:
        owner_info = "🆓 Статус: Свободен"
    
    # Format start message with user data
    start_text = START_MESSAGE.format(
        username=user.username or user.first_name or f"ID{user.id}",
        balance=user_data['balance'] if user_data else 300,
        points=round(user_data['points'], 2) if user_data else 0.0,
        price=user_data['price'] if user_data else 100,
        prisoners_count=len(prisoners),
        owner_info=owner_info
    )
    
    await update.message.reply_text(
        start_text,
        reply_markup=get_main_menu(),
        parse_mode='HTML'
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        HELP_MESSAGE,
        reply_markup=get_main_menu(),
        parse_mode='HTML'
    )

async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - only for @ceosulim"""
    user = update.effective_user
    
    # Check if user is admin
    if user.username != 'ceosulim':
        await update.message.reply_text("❌ У вас нет прав доступа к этой команде!")
        return
    
    # Store admin state
    user_states[user.id] = 'admin_menu'
    
    admin_text = """
🛡️ <b>АДМИН ПАНЕЛЬ</b>

Доступные команды:
• /users - список всех пользователей
• /user @username - информация о пользователе
• /addcoins @username количество - добавить монеты
• /setcoins @username количество - установить количество монет
• /setpoints @username количество - установить количество очков

Или отправьте команду в формате:
<code>addcoins @username 1000</code>
<code>setcoins @username 5000</code>
<code>setpoints @username 100</code>
"""
    
    await update.message.reply_text(admin_text, parse_mode='HTML')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "main_menu":
        await show_main_menu(query)
    elif data == "my_profile":
        await show_my_profile(query)
    elif data == "invite_friend":
        await show_invite_link(query, context)
    elif data == "my_prisoners":
        await show_my_prisoners(query)
    elif data == "find_prisoner":
        await show_find_prisoner(query)
    elif data == "search_by_username":
        # Set user state to wait for username input
        user_states[user_id] = "waiting_username_search"
        await query.answer("Напишите имя пользователя для поиска", show_alert=True)
    elif data.startswith("sort_"):
        sort_type = data.split("_", 1)[1]
        await show_find_prisoner(query, sort_by=sort_type)
    elif data == "back_to_find":
        await show_find_prisoner(query)
    elif data == "balance_transfer":
        await show_balance_transfer(query)
    elif data == "leaderboard":
        await show_leaderboard_menu(query)
    elif data.startswith("view_profile_"):
        prisoner_id = int(data.split("_")[2])
        await show_prisoner_profile(query, prisoner_id)
    elif data.startswith("buy_prisoner_"):
        prisoner_id = int(data.split("_")[2])
        await buy_prisoner_action(query, prisoner_id)
    elif data.startswith("view_prisoner_"):
        prisoner_id = int(data.split("_")[2])
        await show_prisoner_details(query, prisoner_id)
    elif data.startswith("history_"):
        prisoner_id = int(data.split("_")[1])
        await show_ownership_history(query, prisoner_id)
    elif data.startswith("leaderboard_"):
        category = data.split("_")[1]
        await show_leaderboard(query, category)
    elif data == "transfer_money":
        user_states[user_id] = "waiting_transfer_amount"
        await query.edit_message_text(
            "💸 Введите сумму для перевода:",
            reply_markup=get_back_keyboard()
        )
    elif data == "refresh_search":
        await show_find_prisoner(query)
    elif data == "send_to_work":
        await send_prisoners_to_work_action(query)
    elif data == "collect_work_reward":
        await collect_work_reward_action(query)
    elif data == "work_status":
        await show_work_status(query)
    elif data.startswith("self_buyout_"):
        prisoner_id = int(data.split("_")[2])
        await self_buyout_action(query, prisoner_id)
    elif data.startswith("shield_"):
        prisoner_id = int(data.split("_")[1])
        await activate_shield_action(query, prisoner_id)
    elif data.startswith("upgrade_"):
        prisoner_id = int(data.split("_")[1])
        await upgrade_prisoner_action(query, prisoner_id)
    elif data == "price_analysis":
        await show_price_analysis(query)
    elif data == "back":
        await show_main_menu(query)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on user state"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == "waiting_username_search":
            # Search for prisoner by username
            search_term = text.strip().replace('@', '')
            del user_states[user_id]
            
            prisoners = search_prisoners_by_username(search_term, user_id)
            
            if not prisoners:
                await update.message.reply_text(
                    f"🔍 Игрок '@{search_term}' не найден или недоступен для покупки."
                )
            else:
                search_text = f"🔍 Результат поиска '{search_term}':\n\n"
                
                for prisoner in prisoners:
                    name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner['telegram_id']}"
                    owner_text = ""
                    if prisoner['owner_id']:
                        owner = get_user(prisoner['owner_id'])
                        owner_name = owner['username'] or owner['first_name'] or f"ID{owner['telegram_id']}"
                        owner_text = f" (владелец: @{owner_name})"
                    
                    search_text += f"👤 @{name} - {prisoner['price']} монет{owner_text}\n"
                
                await update.message.reply_text(
                    search_text,
                    reply_markup=get_search_results_keyboard(prisoners, None, search_term),
                    parse_mode='HTML'
                )
            return
        
        elif state == "waiting_transfer_amount":
            try:
                amount = int(text)
                if amount <= 0:
                    await update.message.reply_text("Сумма должна быть положительной!")
                    return
                
                user_states[user_id] = f"waiting_transfer_target_{amount}"
                await update.message.reply_text(
                    f"💰 Сумма: {amount} монет\n"
                    "👤 Теперь введите @username или ID получателя:"
                )
            except ValueError:
                await update.message.reply_text("Введите корректную сумму (число)!")
        
        elif state.startswith("waiting_transfer_target_"):
            amount = int(state.split("_")[3])
            target_input = text.strip()
            
            # Try to find target user
            target_user = None
            if target_input.startswith("@"):
                username = target_input[1:]
                from database import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
                row = cursor.fetchone()
                if row:
                    target_user = dict(row)
            else:
                try:
                    target_user_id = int(target_input)
                    target_user = get_user(target_user_id)
                except ValueError:
                    pass
            
            if not target_user:
                await update.message.reply_text("Пользователь не найден! Попробуйте еще раз.")
                return
            
            if target_user['telegram_id'] == user_id:
                await update.message.reply_text("Нельзя переводить самому себе!")
                return
            
            # Perform transfer
            success, message = transfer_money(user_id, target_user['telegram_id'], amount)
            await update.message.reply_text(
                message,
                reply_markup=get_main_menu()
            )
            
            # Send notification to recipient if transfer was successful
            if success:
                sender_user = get_user(user_id)
                recipient_user = get_user(target_user['telegram_id'])
                sender_name = sender_user['username'] or sender_user['first_name'] or f"ID{user_id}"
                
                notification_text = TRANSFER_RECEIVED_MESSAGE.format(
                    sender=sender_name,
                    amount=amount,
                    new_balance=recipient_user['balance']
                )
                await send_notification(target_user['telegram_id'], notification_text)
            
            del user_states[user_id]
    
    # Check for admin commands (only for @ceosulim)
    elif update.effective_user.username == 'ceosulim' and text.startswith('/'):
        await handle_admin_command(update, context)
    elif update.effective_user.username == 'ceosulim' and user_id in user_states and user_states[user_id] == 'admin_menu':
        await handle_admin_text_command(update, context)
    else:
        # Default response
        await update.message.reply_text(
            "Используй кнопки для навигации! 🎮",
            reply_markup=get_main_menu()
        )

async def show_main_menu(query):
    """Show main menu"""
    await query.edit_message_text(
        MAIN_MENU_MESSAGE,
        reply_markup=get_main_menu(),
        parse_mode='HTML'
    )

async def show_my_profile(query):
    """Show user's profile"""
    user_id = query.from_user.id
    user = get_user(user_id)
    
    if not user:
        await query.edit_message_text("Ошибка: профиль не найден!")
        return
    
    # Get owner info
    owner_info = ""
    if user['owner_id']:
        owner = get_user(user['owner_id'])
        owner_name = owner['username'] or owner['first_name'] or f"ID{owner['telegram_id']}"
        owner_info = f"🧑‍💼 Владелец: @{owner_name}"
    else:
        owner_info = "🆓 Свободен"
    
    # Get prisoner count
    prisoners = get_my_prisoners(user_id)
    prisoner_count = len(prisoners)
    
    profile_text = PROFILE_MESSAGE.format(
        username=user['username'] or user['first_name'] or f"ID{user_id}",
        balance=user['balance'],
        points=round(user['points'], 2),
        price=user['price'],
        owner=owner_info,
        prisoners=prisoner_count
    )
    
    await query.edit_message_text(
        profile_text,
        reply_markup=get_profile_keyboard(),
        parse_mode='HTML'
    )

async def show_invite_link(query, context):
    """Show referral invite link"""
    user_id = query.from_user.id
    user = get_user(user_id)
    
    if not user:
        await query.edit_message_text(
            "Ошибка: профиль не найден!",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Always use the known bot username to avoid API calls
    referral_link = f"https://t.me/durov_nobot?start={user['referral_code']}"
    invite_text = INVITE_MESSAGE.format(link=referral_link)
    
    await query.edit_message_text(
        invite_text,
        reply_markup=get_invite_keyboard(referral_link),
        parse_mode='HTML'
    )

async def show_my_prisoners(query):
    """Show user's prisoners"""
    user_id = query.from_user.id
    prisoners = get_my_prisoners(user_id)
    
    if not prisoners:
        await query.edit_message_text(
            "🏃‍♂️ У тебя пока нет заключённых!\n"
            "Используй ловушки или покупай других игроков.",
            reply_markup=get_back_keyboard()
        )
        return
    
    prisoners_text = f"👥 Твои заключённые ({len(prisoners)}):\n\n"
    
    for prisoner in prisoners:
        name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner['telegram_id']}"
        prisoners_text += f"👤 @{name} - {prisoner['price']} монет\n"
    
    await query.edit_message_text(
        prisoners_text,
        reply_markup=get_prisoners_keyboard(prisoners),
        parse_mode='HTML'
    )

async def show_find_prisoner(query, sort_by=None, search_term=None):
    """Show prisoners to buy with sorting and search options"""
    user_id = query.from_user.id
    
    # Show search options menu if no specific action
    if not sort_by and not search_term:
        await query.edit_message_text(
            "🔍 <b>Поиск заключённых</b>\n\n"
            "Выберите способ поиска:",
            reply_markup=get_find_prisoner_menu_keyboard(),
            parse_mode='HTML'
        )
        return
    
    # Get prisoners based on search/sort criteria
    if search_term:
        prisoners = search_prisoners_by_username(search_term, user_id)
        search_text = f"🔍 Результат поиска '{search_term}':\n\n"
    else:
        prisoners = get_sorted_prisoners(sort_by, user_id)
        sort_names = {
            'price_asc': 'по цене (дешевые)',
            'price_desc': 'по цене (дорогие)',
            'random': 'случайные'
        }
        search_text = f"🔍 Заключённые {sort_names.get(sort_by, 'случайные')}:\n\n"
    
    if not prisoners:
        await query.edit_message_text(
            "🔍 Не найдено заключённых для покупки!",
            reply_markup=get_back_to_find_keyboard()
        )
        return
    
    for prisoner in prisoners:
        name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner['telegram_id']}"
        owner_text = ""
        if prisoner['owner_id']:
            owner = get_user(prisoner['owner_id'])
            owner_name = owner['username'] or owner['first_name'] or f"ID{owner['telegram_id']}"
            owner_text = f" (владелец: @{owner_name})"
        
        search_text += f"👤 @{name} - {prisoner['price']} монет{owner_text}\n"
    
    await query.edit_message_text(
        search_text,
        reply_markup=get_search_results_keyboard(prisoners, sort_by, search_term),
        parse_mode='HTML'
    )

async def show_prisoner_profile(query, prisoner_id):
    """Show detailed prisoner profile"""
    prisoner = get_user(prisoner_id)
    
    if not prisoner:
        await query.edit_message_text("Заключённый не найден!")
        return
    
    # Get owner info
    owner_info = ""
    if prisoner['owner_id']:
        owner = get_user(prisoner['owner_id'])
        owner_name = owner['username'] or owner['first_name'] or f"ID{owner['telegram_id']}"
        owner_info = f"@{owner_name}"
    else:
        owner_info = "Свободен"
    
    # Get ownership history
    history = get_ownership_history(prisoner_id)
    history_text = "История: "
    if history:
        history_owners = []
        for h in history:
            if h['new_owner_username']:
                history_owners.append(f"@{h['new_owner_username']}")
            else:
                history_owners.append("Система")
        history_text += " ➝ ".join(history_owners)
    else:
        history_text += "Нет данных"
    
    name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner_id}"
    
    # Check shield status
    shield_status = check_shield_status(prisoner_id)
    shield_text = ""
    if shield_status['has_shield']:
        shield_text = f"\n🛡️ Защищён щитом ({shield_status['time_left']} ч.)"
    
    profile_text = PRISONER_PROFILE_MESSAGE.format(
        name=name,
        price=prisoner['price'],
        owner=owner_info,
        history=history_text
    ) + shield_text
    
    # Create keyboard with buy option if not owned by current user
    from keyboards import get_prisoner_profile_keyboard
    keyboard = get_prisoner_profile_keyboard(prisoner_id, query.from_user.id)
    
    await query.edit_message_text(
        profile_text,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

async def buy_prisoner_action(query, prisoner_id):
    """Handle prisoner purchase"""
    buyer_id = query.from_user.id
    success, message = buy_prisoner(buyer_id, prisoner_id)
    
    await query.edit_message_text(
        message,
        reply_markup=get_back_keyboard(),
        parse_mode='HTML'
    )

async def show_balance_transfer(query):
    """Show balance and transfer options"""
    user_id = query.from_user.id
    user = get_user(user_id)
    
    balance_text = f"💰 Твой баланс: {user['balance']} монет\n\n" \
                   "Выбери действие:"
    
    await query.edit_message_text(
        balance_text,
        reply_markup=get_transfer_keyboard()
    )

async def show_leaderboard_menu(query):
    """Show leaderboard category selection"""
    await query.edit_message_text(
        "🏆 Выбери категорию рейтинга:",
        reply_markup=get_leaderboard_keyboard()
    )

async def show_leaderboard(query, category):
    """Show leaderboard for specific category"""
    leaders = get_leaderboard(category)
    
    if category == 'prisoners':
        title = "🏆 Топ по количеству заключённых:"
        format_func = lambda x: f"{x.get('prisoner_count', 0)} заключённых"
    elif category == 'balance':
        title = "🏆 Топ по балансу:"
        format_func = lambda x: f"{x['balance']} монет"
    elif category == 'value':
        title = "🏆 Топ по стоимости заключённых:"
        format_func = lambda x: f"{x.get('total_value', 0)} монет"
    
    leaderboard_text = f"{title}\n\n"
    
    for i, leader in enumerate(leaders, 1):
        name = leader['username'] or leader['first_name'] or f"ID{leader['telegram_id']}"
        emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard_text += f"{emoji} @{name} - {format_func(leader)}\n"
    
    await query.edit_message_text(
        leaderboard_text,
        reply_markup=get_back_keyboard(),
        parse_mode='HTML'
    )

async def show_ownership_history(query, prisoner_id):
    """Show ownership history for prisoner"""
    history = get_ownership_history(prisoner_id)
    prisoner = get_user(prisoner_id)
    
    name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner_id}"
    
    if not history:
        history_text = f"📚 История владения @{name}:\n\nНет данных об истории."
    else:
        history_text = f"📚 История владения @{name}:\n\n"
        for h in history:
            old_owner = h['old_owner_username'] or "Система"
            new_owner = h['new_owner_username'] or "Неизвестно"
            price_text = f" за {h['price']} монет" if h['price'] > 0 else ""
            history_text += f"@{old_owner} ➝ @{new_owner}{price_text}\n"
    
    await query.edit_message_text(
        history_text,
        reply_markup=get_back_keyboard(),
        parse_mode='HTML'
    )

async def show_prisoner_details(query, prisoner_id):
    """Show prisoner details from prisoners list"""
    await show_prisoner_profile(query, prisoner_id)

# Referral handler (for direct referral links)
async def referral_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle referral links"""
    await start_handler(update, context)

async def send_prisoners_to_work_action(query):
    """Handle sending prisoners to work"""
    user_id = query.from_user.id
    
    success, message, workers_count = send_prisoners_to_work(user_id)
    
    if success:
        # Refresh prisoners list to show updated status
        prisoners = get_my_prisoners(user_id)
        await query.edit_message_text(
            message,
            reply_markup=get_prisoners_keyboard(prisoners),
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(
            message,
            reply_markup=get_prisoners_keyboard(get_my_prisoners(user_id)),
            parse_mode='HTML'
        )

async def collect_work_reward_action(query):
    """Handle collecting work rewards"""
    user_id = query.from_user.id
    
    success, message, reward = collect_work_rewards(user_id)
    
    if success:
        # Update user data and show new balance
        user = get_user(user_id)
        updated_message = message + f"\n\n💰 Текущий баланс: {user['balance']} монет"
    else:
        updated_message = message
    
    # Refresh prisoners list
    prisoners = get_my_prisoners(user_id)
    await query.edit_message_text(
        updated_message,
        reply_markup=get_prisoners_keyboard(prisoners),
        parse_mode='HTML'
    )

async def show_work_status(query):
    """Show work status for user's prisoners"""
    user_id = query.from_user.id
    
    status = get_work_status(user_id)
    
    if not status['has_active_jobs']:
        status_text = "🔴 Нет активных заданий\nОтправь заключённых на работу!"
    else:
        if status['ready_to_collect'] > 0:
            status_text = f"🟢 {status['ready_to_collect']} готовы к сбору!\n💰 Собери награду!"
        else:
            status_text = "🟡 Все ещё работают...\n⏳ Подожди завершения!"
    
    work_status_text = WORK_STATUS_MESSAGE.format(
        workers_count=status['workers_count'],
        total_expected=status['total_expected'],
        ready_count=status['ready_to_collect'],
        working_count=status['still_working'],
        status_text=status_text
    )
    
    prisoners = get_my_prisoners(user_id)
    await query.edit_message_text(
        work_status_text,
        reply_markup=get_prisoners_keyboard(prisoners),
        parse_mode='HTML'
    )

async def self_buyout_action(query, prisoner_id):
    """Handle self-buyout action"""
    user_id = query.from_user.id
    
    # Only allow users to buy their own freedom
    if user_id != prisoner_id:
        await query.answer("❌ Ты можешь выкупить только свою свободу!", show_alert=True)
        return
    
    success, message = buy_self_freedom(user_id)
    
    if success:
        # Send notification to former owner
        user = get_user(user_id)
        if user:
            # Find former owner from transaction history
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT old_owner_id FROM ownership_history 
                WHERE prisoner_id = ? AND new_owner_id IS NULL 
                ORDER BY created_at DESC LIMIT 1
            ''', (user_id,))
            
            former_owner_result = cursor.fetchone()
            if former_owner_result:
                former_owner_id = former_owner_result[0]
                prisoner_name = user['username'] or user['first_name'] or f"ID{user_id}"
                notification_message = f"🆓 Твой заключённый @{prisoner_name} выкупил свою свободу!"
                await send_notification(former_owner_id, notification_message)
        
        await query.edit_message_text(
            message,
            reply_markup=get_main_menu(),
            parse_mode='HTML'
        )
    else:
        await query.answer(message, show_alert=True)

async def activate_shield_action(query, prisoner_id):
    """Handle shield activation"""
    user_id = query.from_user.id
    
    success, message = activate_shield(user_id, prisoner_id)
    
    if success:
        # Send notification to prisoner about shield activation
        prisoner = get_user(prisoner_id)
        if prisoner:
            prisoner_name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner_id}"
            shield_message = f"🛡️ Твой владелец активировал защитный щит! Ты защищён на 24 часа."
            await send_notification(prisoner_id, shield_message)
        
        await query.answer("🛡️ Защитный щит активирован!", show_alert=True)
        # Refresh prisoner profile to show updated information
        await show_prisoner_profile(query, prisoner_id)
    else:
        await query.answer(message, show_alert=True)

async def show_price_analysis(query):
    """Show detailed price analysis for user"""
    from game_logic import GameLogic
    from database import get_db_connection
    
    user_id = query.from_user.id
    user = get_user(user_id)
    
    if not user:
        await query.edit_message_text(
            "Ошибка: профиль не найден!",
            reply_markup=get_back_keyboard()
        )
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate individual price factors
    base_price = user['price']
    liquidity_mult = GameLogic._calculate_liquidity_multiplier(user_id, cursor)
    stability_mult = GameLogic._calculate_income_stability_multiplier(user_id, cursor)
    empire_mult = GameLogic._calculate_empire_multiplier(user_id, cursor)
    profit_mult = GameLogic._calculate_profit_multiplier(user_id, cursor)
    
    # Get trading statistics
    cursor.execute('''
        SELECT COUNT(*) as trades, AVG(price) as avg_price, MAX(price) as max_price
        FROM ownership_history 
        WHERE prisoner_id = ? AND timestamp > datetime('now', '-30 days')
    ''', (user_id,))
    trade_stats = cursor.fetchone()
    
    # Get income statistics  
    cursor.execute('''
        SELECT COUNT(*) as income_days, AVG(amount) as avg_income
        FROM income_log 
        WHERE user_id = ? AND timestamp > datetime('now', '-7 days')
    ''', (user_id,))
    income_stats = cursor.fetchone()
    
    # Get prisoner empire info with upgrades
    from database import get_prisoner_upgrade_info, get_profit_statistics
    
    prisoners = get_my_prisoners(user_id)
    prisoner_count = len(prisoners)
    avg_prisoner_value = sum(p['price'] for p in prisoners) / prisoner_count if prisoner_count > 0 else 0
    
    # Calculate upgrade investments
    total_upgrades = sum(get_prisoner_upgrade_info(p['telegram_id'])['total_invested'] for p in prisoners)
    avg_upgrade_investment = total_upgrades / prisoner_count if prisoner_count > 0 else 0
    
    # Get profit stats
    profit_stats = get_profit_statistics(user_id)
    
    analysis_text = f"""📊 <b>Анализ стоимости игрока</b>

👤 <b>Текущая цена:</b> {base_price} монет

🔍 <b>Факторы ценообразования:</b>

📈 <b>История торговли (×{liquidity_mult:.2f}):</b>
• Сделок за месяц: {trade_stats[0] if trade_stats else 0}
• Средняя цена: {int(trade_stats[1]) if trade_stats and trade_stats[1] else 0} монет
• Максимальная цена: {int(trade_stats[2]) if trade_stats and trade_stats[2] else 0} монет

💰 <b>Стабильность дохода (×{stability_mult:.2f}):</b>
• Дней с доходом: {income_stats[0] if income_stats else 0}
• Средний доход: {int(income_stats[1]) if income_stats and income_stats[1] else 0} монет/день

🏛️ <b>Империя заключённых (×{empire_mult:.2f}):</b>
• Количество заключённых: {prisoner_count}
• Средняя стоимость: {int(avg_prisoner_value)} монет
• Вложено в улучшения: {int(avg_upgrade_investment)} монет

💼 <b>Прибыльность (×{profit_mult:.2f}):</b>
• Приносит прибыли: {profit_stats['avg_generated']} монет/день
• Получает дохода: {profit_stats['avg_received']} монет/день
• Чистая прибыль: {profit_stats['net_profit']} монет

🎯 <b>Итоговый множитель:</b> ×{liquidity_mult * stability_mult * empire_mult * profit_mult:.2f}

💡 <b>Как повысить цену:</b>
• Покупайте и продавайте чаще (ликвидность)
• Получайте стабильный доход каждый день
• Собирайте и улучшайте дорогих заключённых
• Увеличивайте прибыльность для владельца
• Активно участвуйте в торговле"""

    await query.edit_message_text(
        analysis_text,
        reply_markup=get_back_keyboard(),
        parse_mode='HTML'
    )

async def upgrade_prisoner_action(query, prisoner_id):
    """Handle prisoner upgrade action"""
    from database import upgrade_prisoner
    
    user_id = query.from_user.id
    
    success, message = upgrade_prisoner(user_id, prisoner_id)
    
    if success:
        await query.answer("🎯 Заключённый успешно улучшен!", show_alert=True)
        # Refresh prisoner profile to show updated information
        await show_prisoner_details(query, prisoner_id)
    else:
        await query.answer(message, show_alert=True)

async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin slash commands"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == '/users':
        users = admin_get_all_users()
        if not users:
            await update.message.reply_text("База данных пуста.")
            return
        
        response = "👥 <b>Все пользователи:</b>\n\n"
        for i, user in enumerate(users[:20]):  # Show first 20 users
            name = user['username'] or user['first_name'] or f"ID{user['telegram_id']}"
            response += f"{i+1}. @{name}\n"
            response += f"   💰 Монеты: {user['balance']}\n"
            response += f"   ⭐ Очки: {user['points']:.2f}\n"
            response += f"   🏷️ Цена: {user['price']}\n"
            response += f"   👥 Заключенных: {user['prisoner_count']}\n\n"
        
        if len(users) > 20:
            response += f"... и еще {len(users) - 20} пользователей"
        
        await update.message.reply_text(response, parse_mode='HTML')
    
    elif text.startswith('/user '):
        username = text[6:].strip().replace('@', '')
        user = admin_get_user_by_username(username)
        
        if not user:
            await update.message.reply_text(f"Пользователь @{username} не найден.")
            return
        
        name = user['username'] or user['first_name'] or f"ID{user['telegram_id']}"
        owner_name = user['owner_username'] or "Свободен"
        
        response = f"👤 <b>Информация о @{name}</b>\n\n"
        response += f"🆔 ID: {user['telegram_id']}\n"
        response += f"💰 Монеты: {user['balance']}\n"
        response += f"⭐ Очки: {user['points']:.2f}\n"
        response += f"🏷️ Цена: {user['price']}\n"
        response += f"👑 Владелец: {owner_name}\n"
        response += f"👥 Заключенных: {user['prisoner_count']}\n"
        response += f"📅 Создан: {user['created_at'][:10]}"
        
        await update.message.reply_text(response, parse_mode='HTML')

async def handle_admin_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin text commands"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    try:
        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text("Неверный формат. Используйте: addcoins @username количество")
            return
        
        command = parts[0].lower()
        username = parts[1].replace('@', '')
        
        if command in ['addcoins', 'setcoins']:
            amount = int(parts[2])
            user = admin_get_user_by_username(username)
            
            if not user:
                await update.message.reply_text(f"Пользователь @{username} не найден.")
                return
            
            if command == 'addcoins':
                success = admin_add_coins(user['telegram_id'], amount)
                action = "добавлено"
            else:
                success = admin_set_coins(user['telegram_id'], amount)
                action = "установлено"
            
            if success:
                await update.message.reply_text(f"✅ Пользователю @{username} {action} {amount} монет.")
            else:
                await update.message.reply_text("❌ Ошибка при изменении баланса.")
        
        elif command == 'setpoints':
            amount = float(parts[2])
            user = admin_get_user_by_username(username)
            
            if not user:
                await update.message.reply_text(f"Пользователь @{username} не найден.")
                return
            
            success = admin_set_points(user['telegram_id'], amount)
            
            if success:
                await update.message.reply_text(f"✅ Пользователю @{username} установлено {amount} очков.")
            else:
                await update.message.reply_text("❌ Ошибка при изменении очков.")
        
        else:
            await update.message.reply_text("Неизвестная команда. Доступны: addcoins, setcoins, setpoints")
    
    except (ValueError, IndexError):
        await update.message.reply_text("Неверный формат команды.")
    
    # Clear admin state
    if user_id in user_states:
        del user_states[user_id]
