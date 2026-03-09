import asyncio
import logging
import aiosqlite  # ✅ добавить в начало файла
from datetime import datetime, timedelta  # ✅ ДОБАВЛЕНО
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db, DB_PATH  # ✅ ДОБАВЛЕН DB_PATH
from handlers import patient, admin, common
from middlewares.role_check import RoleCheckMiddleware
from scheduler.backup import send_backup
from scheduler.reminders import start_scheduler

logging.basicConfig(level=logging.INFO)

# ✅ НОВАЯ ФУНКЦИЯ: авто-сброс неявок каждый час
async def auto_release_no_shows():
    """Каждый час сбрасывает записи неявившихся клиентов"""
    while True:
        now = datetime.now()
        # Ждём до следующего часа
        next_run = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_seconds = (next_run - now).seconds
        await asyncio.sleep(wait_seconds)
        
        async with aiosqlite.connect(DB_PATH) as db:
            # Сбрасываем записи, время которых прошло больше часа назад
            await db.execute("""
                UPDATE slots 
                SET status = 'free', patient_id = NULL 
                WHERE status = 'booked' 
                AND datetime(slot_date || ' ' || slot_time) < datetime('now', '-1 hour')
            """)
            await db.commit()
            print(f"🕐 [{datetime.now().strftime('%H:%M')}] Сброшены неявки за прошедший час")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    scheduler = AsyncIOScheduler()
    
    # ✅ Добавляем еженедельный бэкап (воскресенье 20:00)
    if ADMIN_IDS:
        scheduler.add_job(
            send_backup,
            trigger='cron',
            day_of_week='sun',
            hour=20,
            minute=0,
            kwargs={'bot': bot, 'admin_id': ADMIN_IDS[0]}
        )
        logging.info("✅ Запланирован еженедельный бэкап (воскресенье 20:00)")
    
    # ✅ ЗАПУСК ПЛАНИРОВЩИКА НАПОМИНАНИЙ
    await start_scheduler()
    
    scheduler.start()
    dp["scheduler"] = scheduler

    # ✅ ЗАПУСК АВТО-СБРОСА НЕЯВОК
    asyncio.create_task(auto_release_no_shows())
    logging.info("✅ Запущен авто-сброс неявок (каждый час)")

    dp.message.middleware(RoleCheckMiddleware())
    dp.callback_query.middleware(RoleCheckMiddleware())

    dp.include_router(common.router)
    dp.include_router(patient.router)
    dp.include_router(admin.router)

    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())