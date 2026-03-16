"""
Утилиты для работы с временем и часовыми поясами
"""
from datetime import datetime, timedelta
import pytz
import re

UTC = pytz.UTC

def parse_user_time(time_str: str):
    """
    Парсит время из строки HH:MM → datetime.time
    Валидация: только цифры, двоеточие, разумные пределы
    """
    if not time_str:
        return None
    
    # Убираем пробелы
    time_str = time_str.strip()
    
    # Проверяем формат регуляркой
    if not re.match(r'^([0-9]{1,2}):([0-9]{1,2})$', time_str):
        return None
    
    try:
        t = datetime.strptime(time_str, "%H:%M").time()
        
        # Дополнительная страховка
        if t.hour < 0 or t.hour > 23 or t.minute < 0 or t.minute > 59:
            return None
        
        return t
    except:
        return None

def get_current_utc() -> datetime:
    """Текущее время в UTC"""
    return datetime.now(UTC)

def format_offset(offset: int) -> str:
    """Форматирует сдвиг в UTC+03:00"""
    sign = "+" if offset >= 0 else "-"
    return f"UTC{sign}{abs(offset):02d}:00"

def utc_to_local(utc_dt: datetime, offset: int) -> datetime:
    """Конвертирует UTC в местное время по сдвигу"""
    return utc_dt + timedelta(hours=offset)

def local_to_utc(local_dt: datetime, offset: int) -> datetime:
    """Конвертирует местное время в UTC"""
    return local_dt - timedelta(hours=offset)

def calculate_offset_from_time(user_time_str: str) -> int:
    """
    Вычисляет сдвиг пользователя от UTC на основе введённого времени
    Учитывает переход через полночь
    """
    user_time = parse_user_time(user_time_str)
    if not user_time:
        return None
    
    utc_now = get_current_utc()
    
    # Создаём datetime с временем пользователя (в тот же день, что и UTC)
    user_dt = utc_now.replace(
        hour=user_time.hour,
        minute=user_time.minute,
        second=0,
        microsecond=0
    )
    
    # Считаем разницу в часах
    diff_hours = (user_dt - utc_now).total_seconds() / 3600
    
    # Корректируем переход через полночь
    if diff_hours > 12:
        diff_hours -= 24
    elif diff_hours < -12:
        diff_hours += 24
    
    return round(diff_hours)