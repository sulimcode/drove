"""
Keyboard layouts for Durov's Prison bot
Contains all inline keyboard definitions
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict

def get_main_menu():
    """Get main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("📄 Мой профиль", callback_data="my_profile"),
            InlineKeyboardButton("🔗 Пригласить друга", callback_data="invite_friend")
        ],
        [
            InlineKeyboardButton("🧑‍💼 Мои заключённые", callback_data="my_prisoners"),
            InlineKeyboardButton("🔍 Найти заключённого", callback_data="find_prisoner")
        ],
        [
            InlineKeyboardButton("💸 Баланс / Перевести", callback_data="balance_transfer"),
            InlineKeyboardButton("🏆 Топ игроков", callback_data="leaderboard")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_profile_keyboard():
    """Get profile view keyboard"""
    keyboard = [
        [InlineKeyboardButton("📊 Анализ цены", callback_data="price_analysis")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_prisoners_keyboard(prisoners: List[Dict]):
    """Get keyboard for prisoners list"""
    keyboard = []
    
    # Add work management buttons if there are prisoners
    if prisoners:
        keyboard.append([
            InlineKeyboardButton("🏭 Отправить на работу", callback_data="send_to_work"),
            InlineKeyboardButton("💰 Собрать награду", callback_data="collect_work_reward")
        ])
        keyboard.append([InlineKeyboardButton("📊 Статус работы", callback_data="work_status")])
    
    # Add prisoner buttons (max 3 per row)
    for i in range(0, len(prisoners), 3):
        row = []
        for j in range(i, min(i + 3, len(prisoners))):
            prisoner = prisoners[j]
            name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner['telegram_id']}"
            row.append(InlineKeyboardButton(
                f"👤 @{name[:10]}", 
                callback_data=f"view_prisoner_{prisoner['telegram_id']}"
            ))
        keyboard.append(row)
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def get_search_keyboard(prisoners: List[Dict]):
    """Get keyboard for prisoner search results"""
    keyboard = []
    
    # Add prisoner buttons with buy option
    for prisoner in prisoners:
        name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner['telegram_id']}"
        keyboard.append([
            InlineKeyboardButton(
                f"👁 @{name[:15]}", 
                callback_data=f"view_profile_{prisoner['telegram_id']}"
            ),
            InlineKeyboardButton(
                f"💰 {prisoner['price']}", 
                callback_data=f"buy_prisoner_{prisoner['telegram_id']}"
            )
        ])
    
    # Add refresh and back buttons
    keyboard.append([
        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_search"),
        InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_prisoner_profile_keyboard(prisoner_id: int, viewer_id: int):
    """Get keyboard for prisoner profile view"""
    from database import get_user
    
    prisoner = get_user(prisoner_id)
    keyboard = []
    
    # If viewer owns this prisoner, show shield and upgrade buttons
    if prisoner['owner_id'] == viewer_id:
        from database import get_prisoner_upgrade_info
        
        shield_cost = int(prisoner['price'] * 0.35)
        upgrade_info = get_prisoner_upgrade_info(prisoner_id)
        upgrade_cost = upgrade_info['next_cost']
        
        keyboard.append([
            InlineKeyboardButton(f"🛡️ Щит за {shield_cost} монет", callback_data=f"shield_{prisoner_id}"),
            InlineKeyboardButton(f"⬆️ Улучшить за {upgrade_cost} монет", callback_data=f"upgrade_{prisoner_id}")
        ])
    
    # If this is the user's own profile and they are owned by someone, show self-buyout
    if prisoner_id == viewer_id and prisoner['owner_id']:
        keyboard.append([
            InlineKeyboardButton(f"🆓 Выкупить свободу за {prisoner['price']} монет", callback_data=f"self_buyout_{prisoner_id}")
        ])
    
    # Add buy button if not owned by viewer and not viewing own profile
    if prisoner['owner_id'] != viewer_id and prisoner_id != viewer_id:
        keyboard.append([
            InlineKeyboardButton(
                f"💰 Купить за {prisoner['price']} монет", 
                callback_data=f"buy_prisoner_{prisoner_id}"
            )
        ])
    
    # Add history button
    keyboard.append([
        InlineKeyboardButton("📚 История", callback_data=f"history_{prisoner_id}")
    ])
    
    # Add back button
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="back")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_transfer_keyboard():
    """Get transfer/balance keyboard"""
    keyboard = [
        [InlineKeyboardButton("💸 Перевести монеты", callback_data="transfer_money")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_leaderboard_keyboard():
    """Get leaderboard category selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("👥 По заключённым", callback_data="leaderboard_prisoners"),
            InlineKeyboardButton("💰 По балансу", callback_data="leaderboard_balance")
        ],
        [
            InlineKeyboardButton("💎 По стоимости", callback_data="leaderboard_value"),
            InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    """Get simple back button keyboard"""
    keyboard = [
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_invite_keyboard(referral_link):
    """Get keyboard for invite link with share button"""
    from urllib.parse import quote
    share_text = quote("🪤 Попался! Заходи в Тюрьму Дурова и начинай зарабатывать!")
    share_url = f"https://t.me/share/url?url={quote(referral_link)}&text={share_text}"
    
    keyboard = [
        [InlineKeyboardButton("📤 Отправить в чат", url=share_url)],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action_data: str):
    """Get confirmation keyboard for actions"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action_data}"),
            InlineKeyboardButton("❌ Нет", callback_data="back")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_find_prisoner_menu_keyboard():
    """Get keyboard for prisoner search options"""
    keyboard = [
        [
            InlineKeyboardButton("💰 По цене (дешевые)", callback_data="sort_price_asc"),
            InlineKeyboardButton("💎 По цене (дорогие)", callback_data="sort_price_desc")
        ],
        [
            InlineKeyboardButton("🔍 Поиск по имени", callback_data="search_by_username"),
            InlineKeyboardButton("🎲 Случайные", callback_data="sort_random")
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_search_results_keyboard(prisoners: List[Dict], sort_by=None, search_term=None):
    """Get keyboard for search results with prisoner selection"""
    keyboard = []
    
    # Add prisoner selection buttons
    for prisoner in prisoners:
        name = prisoner['username'] or prisoner['first_name'] or f"ID{prisoner['telegram_id']}"
        keyboard.append([
            InlineKeyboardButton(f"👤 @{name} - {prisoner['price']} монет", 
                               callback_data=f"prisoner_profile_{prisoner['telegram_id']}")
        ])
    
    # Add navigation buttons
    nav_buttons = []
    if search_term:
        nav_buttons.append(InlineKeyboardButton("🔍 Новый поиск", callback_data="search_by_username"))
    else:
        nav_buttons.append(InlineKeyboardButton("🔄 Обновить", callback_data=f"sort_{sort_by}" if sort_by else "sort_random"))
    
    nav_buttons.append(InlineKeyboardButton("🔙 К поиску", callback_data="back_to_find"))
    
    keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def get_back_to_find_keyboard():
    """Get keyboard to return to prisoner search"""
    keyboard = [
        [
            InlineKeyboardButton("🔙 К поиску", callback_data="back_to_find"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
