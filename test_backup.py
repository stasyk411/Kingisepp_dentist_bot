import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from bot import bot
from scheduler import send_backup_to_all_admins

async def main():
    print("🚀 Запуск тестового бэкапа...")
    await send_backup_to_all_admins(bot)
    print("✅ Команда выполнена")

if __name__ == "__main__":
    asyncio.run(main())
