import re

def clean_phone(phone: str) -> str:
    cleaned = re.sub(r'[^\d\+]', '', phone)
    if cleaned.startswith('8'):
        cleaned = '+7' + cleaned[1:]
    elif len(cleaned) == 10 and cleaned.isdigit():
        cleaned = '+7' + cleaned
    return cleaned

def is_valid_phone(phone: str) -> bool:
    digits = re.sub(r'\D', '', phone)
    return 10 <= len(digits) <= 12
