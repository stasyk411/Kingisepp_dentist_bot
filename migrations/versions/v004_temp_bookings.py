"""
v004 - Добавление таблицы временных блокировок слотов
"""

import aiosqlite
from ..migration_manager import Migration

class AddTempBookingsTable(Migration):
    def __init__(self):
        super().__init__("004", "Добавление таблицы временных блокировок слотов")
    
    async def up(self, db: aiosqlite.Connection) -> None:
        """Создать таблицу temp_bookings"""
        
        # Таблица временных блокировок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS temp_bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_date TEXT NOT NULL,
                slot_time TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Индексы для скорости
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_temp_bookings_date_time 
            ON temp_bookings(slot_date, slot_time)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_temp_bookings_expires_at 
            ON temp_bookings(expires_at)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_temp_bookings_user_id 
            ON temp_bookings(user_id)
        """)
        
        print("✅ Таблица temp_bookings создана")
    
    async def down(self, db: aiosqlite.Connection) -> None:
        """Удалить таблицу temp_bookings"""
        await db.execute("DROP TABLE IF EXISTS temp_bookings")
        print("⏪ Таблица temp_bookings удалена")