"""
v003 - Добавление таблицы рабочих часов
"""

import aiosqlite
from ..migration_manager import Migration

class AddWorkingHoursTable(Migration):
    def __init__(self):
        super().__init__("003", "Добавление таблицы рабочих часов")
    
    async def up(self, db: aiosqlite.Connection) -> None:
        """Создать таблицу working_hours"""
        await db.execute("""
            CREATE TABLE IF NOT EXISTS working_hours (
                day TEXT PRIMARY KEY,
                start_hour TEXT,
                end_hour TEXT
            )
        """)
        
        # Добавляем стандартные рабочие часы
        await db.execute("""
            INSERT OR IGNORE INTO working_hours (day, start_hour, end_hour) VALUES
            ('Понедельник', '10', '15'),
            ('Вторник', '10', '15'),
            ('Среда', '10', '15'),
            ('Четверг', '10', '15'),
            ('Пятница', '10', '15')
        """)
    
    async def down(self, db: aiosqlite.Connection) -> None:
        """Удалить таблицу"""
        await db.execute("DROP TABLE IF EXISTS working_hours")
