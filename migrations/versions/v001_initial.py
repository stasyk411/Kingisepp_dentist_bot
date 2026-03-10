"""
v001 - Создание начальных таблиц
"""

import aiosqlite
from ..migration_manager import Migration

class CreateInitialTables(Migration):
    def __init__(self):
        super().__init__("001", "Создание начальных таблиц patients и slots")
    
    async def up(self, db: aiosqlite.Connection) -> None:
        """Создать таблицы patients и slots"""
        
        # Таблица пациентов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                name TEXT,
                phone TEXT,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица слотов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_date DATE,
                slot_time TEXT,
                patient_id INTEGER,
                status TEXT DEFAULT 'free',
                reminder_sent BOOLEAN DEFAULT 0,
                booked_at DATETIME,
                cancelled_by TEXT DEFAULT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                UNIQUE(slot_date, slot_time)
            )
        """)
        
        # Индексы для производительности
        await db.execute("CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(slot_date)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_slots_status ON slots(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_patients_telegram ON patients(telegram_id)")
    
    async def down(self, db: aiosqlite.Connection) -> None:
        """Удалить таблицы"""
        await db.execute("DROP TABLE IF EXISTS slots")
        await db.execute("DROP TABLE IF EXISTS patients")
