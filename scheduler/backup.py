import os
import aiosqlite
from datetime import datetime
from aiogram import Bot

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
        
        # Отправляем файл
        with open(DB_PATH, 'rb') as db_file:
            await bot.send_document(
                admin_id,
                db_file,
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