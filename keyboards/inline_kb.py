from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

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

def days_keyboard():
    """Клавиатура для выбора дня недели (настройки)"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки дней
    builder.button(text="ПН", callback_data="day_mon")
    builder.button(text="ВТ", callback_data="day_tue")
    builder.button(text="СР", callback_data="day_wed")
    builder.button(text="ЧТ", callback_data="day_thu")
    builder.button(text="ПТ", callback_data="day_fri")
    
    # Кнопка готово
    builder.button(text="✅ Готово", callback_data="settings_done")
    
    # Располагаем по 5 в ряд
    builder.adjust(5, 1)
    
    return builder.as_markup()

def hours_start_keyboard():
    """Клавиатура для выбора часа начала (8:00 - 20:00)"""
    builder = InlineKeyboardBuilder()
    
    # Часы с 8 до 20
    hours = ["08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"]
    
    for hour in hours:
        builder.button(text=f"{hour}:00", callback_data=f"hour_start_{hour}")
    
    # Кнопка назад
    builder.button(text="🔙 Назад", callback_data="back_to_days")
    
    # Располагаем по 4 в ряд
    builder.adjust(4, 4, 4, 1)
    
    return builder.as_markup()

def hours_end_keyboard(start_hour: str):
    """Клавиатура для выбора часа окончания (больше start_hour)"""
    builder = InlineKeyboardBuilder()
    
    start = int(start_hour)
    
    # Часы от start+1 до 21 (минимум +1 час работы)
    for hour in range(start + 1, 22):
        hour_str = f"{hour:02d}"
        builder.button(text=f"{hour_str}:00", callback_data=f"hour_end_{hour_str}")
    
    # Кнопка назад
    builder.button(text="🔙 Назад", callback_data="back_to_start")
    
    # Располагаем по 4 в ряд (без вычисления len, так как builder.buttons - генератор)
    builder.adjust(4, 4, 4, 4, 1)
    
    return builder.as_markup()

def back_to_days_keyboard():
    """Клавиатура только с кнопкой назад к дням"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 К выбору дня", callback_data="back_to_days")
    return builder.as_markup()