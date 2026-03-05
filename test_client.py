import asyncio
from datetime import datetime, timedelta
from database import get_free_times, get_blocked_day

async def test_client():
    print("=== ПРОВЕРКА КЛИЕНТА ===\n")
    
    # Дата для теста (завтра)
    test_date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Проверяем, не заблокирован ли день
    blocked = await get_blocked_day(test_date)
    if blocked:
        print(f"❌ День {test_date} ЗАБЛОКИРОВАН: {blocked['reason']}")
    else:
        print(f"✅ День {test_date} доступен")
        
        # Получаем свободные слоты
        free_times = await get_free_times(test_date)
        if free_times:
            times = [t[1] for t in free_times]
            print(f"📅 Свободные слоты на {test_date}: {', '.join(times)}")
        else:
            print(f"❌ Нет свободных слотов на {test_date}")

asyncio.run(test_client())