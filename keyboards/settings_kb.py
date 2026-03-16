from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.time_utils import format_offset

def settings_menu_keyboard(current_offset: int):
    """Главное меню настроек с текущим смещением"""
    offset_str = format_offset(current_offset)
    
    keyboard = [
        [InlineKeyboardButton(
            text=f"⏰ Сменить время (сейчас {offset_str})",
            callback_data="change_timezone"
        )],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_settings_keyboard():
    """Кнопка возврата в настройки"""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)