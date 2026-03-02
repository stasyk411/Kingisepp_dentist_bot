import asyncio
import logging
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from database import init_db
from handlers import patient, admin, common
from middlewares.role_check import RoleCheckMiddleware

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    scheduler = AsyncIOScheduler()
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
