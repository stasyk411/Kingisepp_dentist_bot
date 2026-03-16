import os
from datetime import datetime
from aiogram import Bot
from aiogram.types import FSInputFile  # ✅ правильный импорт для файлов

# Путь к базе данных
DB_PATH = "dentist_bot.db"

async def send_backup(bot: Bot, admin_id: int):
    """Отправляет бэкап базы данных админу"""
    try:
        # Проверяем, что файл существует
        if not os.path.exists(DB_PATH):
            await bot.send_message(admin_id, "❌ Файл базы данных не найден")
            return
        
        # Получаем размер файла
        size_mb = os.path.getsize(DB_PATH) / 1024 / 1024
        
        # ✅ ИСПРАВЛЕНИЕ: используем FSInputFile вместо открытия файла
        document = FSInputFile(
            path=DB_PATH,
            filename=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        
        # Отправляем файл
        await bot.send_document(
            chat_id=admin_id,
            document=document,
            caption=f"📦 Бэкап базы данных\n"
                    f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    f"💾 Размер: {size_mb:.2f} МБ"
        )
        
        print(f"✅ Бэкап отправлен {datetime.now()}")
        
    except Exception as e:
        error_msg = f"❌ Ошибка при отправке бэкапа: {e}"
        print(error_msg)
        try:
            await bot.send_message(admin_id, error_msg)
        except:
            pass