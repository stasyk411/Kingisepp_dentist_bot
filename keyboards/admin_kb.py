from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def admin_main_menu():
    kb = [
        [KeyboardButton(text="📋 Сегодня"), KeyboardButton(text="📅 Завтра")],
        [KeyboardButton(text="⛔ Отмена дня"), KeyboardButton(text="🔓 Освободить")],
        [KeyboardButton(text="💳 Поддержать")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
