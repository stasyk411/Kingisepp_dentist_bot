from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_time_keyboard(times: list):
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for slot_id, time_str in times:
        buttons.append(InlineKeyboardButton(text=time_str, callback_data=f"time_{slot_id}"))
    
    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i+3])
    
    markup.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_calendar"))
    return markup
