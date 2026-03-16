"""
Планировщик задач для бота
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from aiogram import Bot
from config import ADMIN_IDS
from scheduler.backup import send_backup

scheduler = AsyncIOScheduler()

def setup_scheduler(bot: Bot):
    """Настройка всех периодических задач"""
    
    # Бэкап по воскресеньям в 20:00
    scheduler.add_job(
        lambda: send_backup_to_all_admins(bot),
        CronTrigger(day_of_week='sun', hour=20, minute=0),
        id='weekly_backup'
    )
    
    scheduler.start()
    print("✅ Планировщик задач запущен")

async def send_backup_to_all_admins(bot: Bot):
    """Отправить бэкап всем админам"""
    for admin_id in ADMIN_IDS:
        await send_backup(bot, admin_id)
    print(f"✅ Бэкап отправлен всем админам {datetime.now()}")
