from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_time_keyboard(times: list):
    """Создает клавиатуру с доступным временем"""
    keyboard = []
    buttons = []
    
    # Создаем кнопки для каждого слота
    for slot_id, time_str in times:
        buttons.append(
            InlineKeyboardButton(
                text=time_str,
                callback_data=f"time_{slot_id}"
            )
        )
    
    # Добавляем кнопки по 3 в ряд
    for i in range(0, len(buttons), 3):
        row = buttons[i:i+3]
        keyboard.append(row)
    
    # Добавляем кнопку "Назад"
    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_calendar")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)