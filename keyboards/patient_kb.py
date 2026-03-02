from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def patient_main_menu():
    kb = [
        [KeyboardButton(text="📝 Записаться"), KeyboardButton(text="📅 Мои записи")],
        [KeyboardButton(text="❓ Контакты"), KeyboardButton(text="❓ Помощь")],
        [KeyboardButton(text="💳 Поддержать")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
