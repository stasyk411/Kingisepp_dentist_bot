"""
v002 - Добавление таблицы заблокированных дней
"""

import aiosqlite
from ..migration_manager import Migration

class AddBlockedDaysTable(Migration):
    def __init__(self):
        super().__init__("002", "Добавление таблицы заблокированных дней")
    
    async def up(self, db: aiosqlite.Connection) -> None:
        """Создать таблицу blocked_days"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blocked_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_date DATE UNIQUE,
                reason TEXT,
                comment TEXT
            )
        """)
        
        # Индекс для быстрого поиска
        await db.execute("CREATE INDEX IF NOT EXISTS idx_blocked_days_date ON blocked_days(block_date)")
    
    async def down(self, db: aiosqlite.Connection) -> None:
        """Удалить таблицу"""
        await db.execute("DROP TABLE IF EXISTS blocked_days")
