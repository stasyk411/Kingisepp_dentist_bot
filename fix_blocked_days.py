import sqlite3

DB_PATH = "dentist_bot.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Исправляем vacation -> Отпуск
cursor.execute("UPDATE blocked_days SET reason = 'Отпуск' WHERE reason = 'vacation'")
print(f"Исправлено {cursor.rowcount} записей: vacation -> Отпуск")

# Исправляем sick -> Больничный
cursor.execute("UPDATE blocked_days SET reason = 'Больничный' WHERE reason = 'sick'")
print(f"Исправлено {cursor.rowcount} записей: sick -> Больничный")

# Исправляем другие возможные варианты (если есть)
cursor.execute("UPDATE blocked_days SET reason = 'Отпуск' WHERE reason = 'Отпуск'")
cursor.execute("UPDATE blocked_days SET reason = 'Больничный' WHERE reason = 'Больничный'")

conn.commit()
conn.close()

print("✅ Все записи приведены к единому формату.")