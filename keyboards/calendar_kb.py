from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import calendar

def create_calendar(year: int = None, month: int = None, status_dict: dict = None, for_patient: bool = False):
    """
    Создает календарь с возможностью подсветки статусов дней
    :param year: год
    :param month: месяц
    :param status_dict: словарь {дата: статус/причина}
    :param for_patient: True для клиента, False для админа
    """
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month
    
    # Создаем пустую клавиатуру
    keyboard = []
    
    # Название месяца и года (одна строка)
    month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    keyboard.append([
        InlineKeyboardButton(
            text=f"{month_names[month-1]} {year}", 
            callback_data="ignore"
        )
    ])
    
    # Дни недели (одна строка)
    week_days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    week_row = []
    for day in week_days:
        week_row.append(InlineKeyboardButton(text=day, callback_data="ignore"))
    keyboard.append(week_row)
    
    # Календарная сетка (недели)
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                
                # Определяем эмодзи для кнопки
                emoji = ""
                if status_dict and date_str in status_dict:
                    reason = status_dict[date_str]
                    
                    if for_patient:
                        # Для клиента — понятные иконки
                        if reason == "Отпуск":
                            emoji = "🏖 "
                        elif reason == "Больничный":
                            emoji = "🤒 "
                        else:
                            emoji = "🚫 "  # на всякий случай
                    else:
                        # Для админа — просто замок (без разницы, какая причина)
                        emoji = "🔒 "
                
                # Для клиента: выходные СБ, ВС — добавляем ⚪
                if for_patient:
                    weekday_num = datetime.strptime(date_str, "%Y-%m-%d").weekday()
                    if weekday_num >= 5 and date_str not in status_dict:
                        emoji = "⚪ "
                
                week_row.append(
                    InlineKeyboardButton(
                        text=f"{emoji}{day}",
                        callback_data=f"date_{date_str}"
                    )
                )
        keyboard.append(week_row)
    
    # Кнопки навигации (одна строка)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    nav_row = [
        InlineKeyboardButton(text="◀️", callback_data=f"cal_{prev_year}_{prev_month}"),
        InlineKeyboardButton(text="❌", callback_data="cancel_booking"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal_{next_year}_{next_month}")
    ]
    keyboard.append(nav_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)