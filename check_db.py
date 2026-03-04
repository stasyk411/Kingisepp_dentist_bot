import sqlite3
import os

print("=== РАЗМЕР БАЗЫ ДАННЫХ ===")
db_size = os.path.getsize('dentist_bot.db') / 1024 / 1024
print(f"Общий размер БД: {db_size:.2f} МБ\n")

conn = sqlite3.connect('dentist_bot.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=== КОЛИЧЕСТВО ЗАПИСЕЙ В ТАБЛИЦАХ ===")
for table in tables:
    table_name = table[0]
    count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    print(f"{table_name}: {count} записей")

conn.close()