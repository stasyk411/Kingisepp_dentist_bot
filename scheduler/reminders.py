"""
Планировщик задач для Telegram бота
Отправляет напоминания пациентам за 24 часа до записи
"""

import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from database import (
    get_slots_for_reminder,
    mark_reminder_sent,
    get_patient_telegram_by_slot
)
from config import BOT_TOKEN, ADMIN_IDS
from aiogram import Bot

# Инициализация бота для отправки сообщений
bot = Bot(token=BOT_TOKEN)

# Создаём планировщик
scheduler = AsyncIOScheduler()

async def send_reminder(slot_id: int, patient_id: int, slot_date: str, slot_time: str):
    """Отправляет напоминание конкретному пациенту"""
    try:
        # Получаем telegram_id пациента
        telegram_id = await get_patient_telegram_by_slot(slot_id)
        
        if not telegram_id:
            print(f"❌ Не найден telegram_id для слота {slot_id}")
            return
        
        # Формируем сообщение
        text = (
            f"🔔 НАПОМИНАНИЕ\n\n"
            f"У вас запись к стоматологу:\n"
            f"📅 {slot_date}\n"
            f"⏰ {slot_time}\n\n"
            f"Пожалуйста, не опаздывайте!"
        )
        
        # Отправляем
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode="HTML"
        )
        
        # Отмечаем что напоминание отправлено
        await mark_reminder_sent(slot_id)
        print(f"✅ Напоминание отправлено: слот {slot_id} -> {telegram_id}")
        
    except Exception as e:
        print(f"❌ Ошибка при отправке напоминания: {e}")

async def check_and_send_reminders():
    """Проверяет и отправляет напоминания (запускается каждую минуту)"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Проверка напоминаний...")
    
    # Получаем слоты для напоминания
    slots = await get_slots_for_reminder()
    
    if not slots:
        return
    
    print(f"🔔 Найдено {len(slots)} слотов для напоминания")
    
    # Отправляем напоминания
    for slot in slots:
        await send_reminder(
            slot_id=slot["id"],
            patient_id=slot["patient_id"],
            slot_date=slot["slot_date"],
            slot_time=slot["slot_time"]
        )

async def start_scheduler():
    """Запускает планировщик"""
    # Проверяем каждую минуту
    scheduler.add_job(
        check_and_send_reminders,
        IntervalTrigger(minutes=1),
        id="check_reminders",
        replace_existing=True
    )
    
    # Ежедневный бэкап в 23:00
    scheduler.add_job(
        send_daily_backup,
        CronTrigger(hour=23, minute=0),
        id="daily_backup",
        replace_existing=True
    )
    
    scheduler.start()
    print("✅ Планировщик запущен")

async def send_daily_backup():
    """Отправляет ежедневный бэкап БД админу"""
    try:
        from database import DB_PATH
        
        for admin_id in ADMIN_IDS:
            with open(DB_PATH, 'rb') as db_file:
                await bot.send_document(
                    chat_id=admin_id,
                    document=db_file,
                    caption=f"📦 Бэкап БД за {datetime.now().strftime('%Y-%m-%d')}"
                )
        print(f"✅ Бэкап отправлен админам {ADMIN_IDS}")
    except Exception as e:
        print(f"❌ Ошибка бэкапа: {e}")

# Для тестирования вручную
async def test_reminder():
    """Тестовая функция для проверки напоминаний"""
    print("🧪 Тест напоминаний...")
    await check_and_send_reminders()

if __name__ == "__main__":
    # Для ручного теста
    asyncio.run(test_reminder())