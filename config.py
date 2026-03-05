import os
from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw_value: str) -> list[int]:
    """Безопасно парсит список ID админов из переменной окружения ADMIN_IDS."""
    if not raw_value:
        return []

    admin_ids: list[int] = []
    for item in raw_value.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        try:
            admin_ids.append(int(cleaned))
        except ValueError:
            # Пропускаем невалидные значения вместо падения приложения.
            continue
    return admin_ids


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
