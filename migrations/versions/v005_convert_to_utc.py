"""
v005 - Конвертация всех слотов из МСК в UTC
"""

class ConvertSlotsToUTC:
    def __init__(self):
        self.version = "005"
        self.description = "Перевод времени слотов из МСК в UTC"
    
    async def up(self, db):
        # 1. Создаём временную таблицу без данных
        await db.execute("""
            CREATE TABLE slots_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_date DATE,
                slot_time TEXT,
                patient_id INTEGER,
                status TEXT DEFAULT 'free',
                reminder_sent BOOLEAN DEFAULT 0,
                booked_at DATETIME,
                cancelled_by TEXT DEFAULT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)
        
        # 2. Копируем данные с конвертацией времени
        await db.execute("""
            INSERT INTO slots_new (
                id, slot_date, slot_time, patient_id, 
                status, reminder_sent, booked_at, cancelled_by
            )
            SELECT 
                id,
                slot_date,
                printf('%02d:%02d', 
                    CASE 
                        WHEN cast(substr(slot_time, 1, 2) as integer) - 3 < 0 
                        THEN cast(substr(slot_time, 1, 2) as integer) - 3 + 24
                        ELSE cast(substr(slot_time, 1, 2) as integer) - 3
                    END,
                    cast(substr(slot_time, 4, 2) as integer)
                ),
                patient_id,
                status,
                reminder_sent,
                datetime(booked_at, '-3 hours'),
                cancelled_by
            FROM slots
            ORDER BY id
        """)
        
        # 3. Удаляем старую таблицу
        await db.execute("DROP TABLE slots")
        
        # 4. Переименовываем новую
        await db.execute("ALTER TABLE slots_new RENAME TO slots")
        
        # 5. Восстанавливаем индексы
        await db.execute("CREATE UNIQUE INDEX idx_slots_date_time ON slots(slot_date, slot_time)")
        await db.execute("CREATE INDEX idx_slots_date ON slots(slot_date)")
        await db.execute("CREATE INDEX idx_slots_status ON slots(status)")
        
        print("✅ Слоты переведены из МСК в UTC (с сохранением уникальности)")
    
    async def down(self, db):
        # Откат: возвращаем время обратно в МСК
        await db.execute("""
            UPDATE slots 
            SET slot_time = 
                printf('%02d:%02d', 
                    CASE 
                        WHEN cast(substr(slot_time, 1, 2) as integer) + 3 >= 24 
                        THEN cast(substr(slot_time, 1, 2) as integer) + 3 - 24
                        ELSE cast(substr(slot_time, 1, 2) as integer) + 3
                    END,
                    cast(substr(slot_time, 4, 2) as integer)
                )
        """)
        
        await db.execute("""
            UPDATE slots 
            SET booked_at = datetime(booked_at, '+3 hours')
            WHERE booked_at IS NOT NULL
        """)
        
        print("⏪ Слоты возвращены в МСК")