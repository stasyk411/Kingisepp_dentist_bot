import aiosqlite
from datetime import datetime

DB_PATH = "dentist_bot.db"

async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        # ✅ Включаем авто-очистку (постепенное сжатие)
        await db.execute("PRAGMA auto_vacuum = INCREMENTAL")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                name TEXT,
                phone TEXT,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

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

        # ✅ НОВАЯ ТАБЛИЦА: заблокированные дни с причинами
        await db.execute("""
            CREATE TABLE IF NOT EXISTS blocked_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_date DATE UNIQUE,
                reason TEXT,
                comment TEXT
            )
        """)

        await db.commit()

    await generate_test_slots()
    await fix_broken_bookings()

async def generate_test_slots():
    """Генерация тестовых слотов"""
    async with aiosqlite.connect(DB_PATH) as db:
        from datetime import datetime, timedelta
        
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day in range(0, 15):
            current_date = start_date + timedelta(days=day)
            date_str = current_date.strftime("%Y-%m-%d")
            
            if current_date.weekday() >= 5:
                continue
            
            for hour in range(10, 15):
                time_str = f"{hour:02d}:00"
                await db.execute("""
                    INSERT OR IGNORE INTO slots (slot_date, slot_time, status)
                    VALUES (?, ?, 'free')
                """, (date_str, time_str))
        
        await db.commit()

async def fix_broken_bookings():
    """Исправляет битые записи при запуске"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Завершаем старые записи (дата прошла)
        today = datetime.now().strftime("%Y-%m-%d")
        await db.execute("""
            UPDATE slots 
            SET status = 'completed' 
            WHERE status = 'booked' AND slot_date < ?
        """, (today,))
        
        # 2. Чиним записи без patient_id (если такие есть)
        await db.execute("""
            UPDATE slots 
            SET status = 'free', patient_id = NULL 
            WHERE status = 'booked' AND patient_id IS NULL
        """)
        
        await db.commit()
        print("✅ Битые записи исправлены")

async def book_slot(slot_id: int, patient_id: int, selected_date: str) -> bool:
    """Атомарное бронирование слота с транзакцией"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("BEGIN TRANSACTION")
            
            # Проверяем, что слот свободен
            cursor = await db.execute(
                "SELECT status FROM slots WHERE id = ?", 
                (slot_id,)
            )
            row = await cursor.fetchone()
            
            if not row or row[0] != 'free':
                await db.rollback()
                return False
            
            # ПРОВЕРКА: есть ли у пациента другая активная запись (на любую дату)
            cursor = await db.execute("""
                SELECT id FROM slots 
                WHERE patient_id = ? AND status = 'booked'
            """, (patient_id,))
            existing = await cursor.fetchone()
            
            if existing:
                print(f"❌ У пациента уже есть активная запись (id={existing[0]})")
                await db.rollback()
                return False
            
            # Бронируем
            await db.execute("""
                UPDATE slots 
                SET status='booked', patient_id=?, booked_at=CURRENT_TIMESTAMP 
                WHERE id=?
            """, (patient_id, slot_id))
            
            await db.commit()
            return True
        except Exception as e:
            print(f"Ошибка: {e}")
            await db.rollback()
            return False

async def cancel_slot(slot_id: int, patient_id: int) -> bool:
    """Отмена записи пациентом"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT status FROM slots WHERE id = ? AND patient_id = ?",
            (slot_id, patient_id)
        )
        if not await cursor.fetchone():
            return False
        
        await db.execute("""
            UPDATE slots 
            SET status='free', patient_id=NULL, cancelled_by='patient'
            WHERE id=?
        """, (slot_id,))
        await db.commit()
        return True

async def get_patient_id(telegram_id: int) -> int:
    """Получить ID пациента по telegram_id"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM patients WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def save_patient(telegram_id: int, name: str, phone: str = None):
    """Сохранить или обновить данные пациента"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO patients (telegram_id, name, phone)
            VALUES (?, ?, ?)
        """, (telegram_id, name, phone))
        await db.commit()

async def get_free_times(date_str: str):
    """Получить свободные слоты на дату"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, slot_time 
            FROM slots 
            WHERE slot_date = ? AND status = 'free'
            ORDER BY slot_time
        """, (date_str,))
        return await cursor.fetchall()

# ✅ НОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАБЛОКИРОВАННЫМИ ДНЯМИ

async def block_day(date_str: str, reason: str, comment: str = ""):
    """Заблокировать день с указанием причины"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO blocked_days (block_date, reason, comment)
            VALUES (?, ?, ?)
        """, (date_str, reason, comment))
        await db.commit()

async def unblock_day(date_str: str):
    """Разблокировать день"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blocked_days WHERE block_date = ?", (date_str,))
        await db.commit()

async def get_blocked_day(date_str: str):
    """Получить информацию о заблокированном дне"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT reason, comment FROM blocked_days WHERE block_date = ?",
            (date_str,)
        )
        row = await cursor.fetchone()
        return {"reason": row[0], "comment": row[1]} if row else None

async def get_all_blocked_days():
    """Получить все заблокированные дни"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT block_date, reason, comment FROM blocked_days ORDER BY block_date")
        rows = await cursor.fetchall()
        return [{"date": row[0], "reason": row[1], "comment": row[2]} for row in rows]