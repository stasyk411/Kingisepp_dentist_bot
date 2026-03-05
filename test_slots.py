from datetime import datetime, timedelta
import sqlite3
from datetime import datetime

print("=== ПРОВЕРКА БАЗЫ ДАННЫХ ===\n")

conn = sqlite3.connect('dentist_bot.db')

# 1. Настройки расписания
cur = conn.execute("SELECT * FROM working_hours")
wh = cur.fetchall()
print("📋 ТЕКУЩЕЕ РАСПИСАНИЕ:")
for row in wh:
    print(f"   {row[0]}: {row[1]}:00 — {row[2]}:00")

print()

# 2. Слоты на завтра
tomorrow = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).strftime("%Y-%m-%d")
cur = conn.execute("SELECT slot_time FROM slots WHERE slot_date = ? ORDER BY slot_time", (tomorrow,))
slots = cur.fetchall()
print(f"📅 СЛОТЫ НА {tomorrow}:")
if slots:
    times = [s[0] for s in slots]
    print(f"   Найдено: {len(times)} слотов")
    print(f"   Часы: {', '.join(times)}")
else:
    print("   ❌ НЕТ СЛОТОВ")

print()

# 3. Всего слотов в БД
cur = conn.execute("SELECT COUNT(*) FROM slots")
total = cur.fetchone()[0]
print(f"📊 ВСЕГО СЛОТОВ В БД: {total}")

conn.close()