import asyncio
import logging
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db
from handlers import patient, admin, common
from middlewares.role_check import RoleCheckMiddleware
from scheduler.backup import send_backup
from scheduler.reminders import start_scheduler  # ✅ ИСПРАВЛЕНО

logging.basicConfig(level=logging.INFO)

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

    dp.message.middleware(RoleCheckMiddleware())
    dp.callback_query.middleware(RoleCheckMiddleware())

    dp.include_router(common.router)
    dp.include_router(patient.router)
    dp.include_router(admin.router)

    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())