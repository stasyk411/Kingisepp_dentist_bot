import asyncio
import aiosqlite
from database import get_all_working_hours, get_all_blocked_days

async def test_admin():
    print("=== ПРОВЕРКА АДМИНКИ ===\n")
    
    # Настройки расписания
    wh = await get_all_working_hours()
    print("📋 НАСТРОЙКИ РАСПИСАНИЯ:")
    if wh:
        for day, hours in wh.items():
            print(f"   {day}: {hours['start']}:00 — {hours['end']}:00")
    else:
        print("   ❌ Расписание не настроено")
    
    print()
    
    # Заблокированные дни
    blocked = await get_all_blocked_days()
    print("🔒 ЗАБЛОКИРОВАННЫЕ ДНИ:")
    if blocked:
        for day in blocked:
            print(f"   {day['date']}: {day['reason']}")
    else:
        print("   ✅ Нет заблокированных дней")

asyncio.run(test_admin())