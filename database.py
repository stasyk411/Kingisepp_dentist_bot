import aiosqlite
from datetime import datetime

DB_PATH = "dentist_bot.db"

async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
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

        await db.execute("""
            CREATE TABLE IF NOT EXISTS blocked_days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_date DATE UNIQUE,
                reason TEXT,
                comment TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS working_hours (
                day TEXT PRIMARY KEY,
                start_hour TEXT,
                end_hour TEXT
            )
        """)

        await db.commit()

    await generate_future_slots()
    await fix_broken_bookings()

async def generate_future_slots(days_ahead: int = 30):
    async with aiosqlite.connect(DB_PATH) as db:
        from datetime import datetime, timedelta
        
        working_hours = await get_all_working_hours()
        
        if not working_hours:
            print("⚠️ Расписание не настроено. Слоты не созданы.")
            return
        
        await db.execute("""
            DELETE FROM slots 
            WHERE slot_date >= date('now') 
            AND status = 'free'
        """)
        
        day_map = {
            0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri"
        }
        
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day_offset in range(0, days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            weekday = current_date.weekday()
            date_str = current_date.strftime("%Y-%m-%d")
            
            day_code = day_map.get(weekday)
            if not day_code or day_code not in working_hours:
                continue
            
            start_hour = int(working_hours[day_code]['start'])
            end_hour = int(working_hours[day_code]['end'])
            
            for hour in range(start_hour, end_hour + 1):
                time_str = f"{hour:02d}:00"
                await db.execute("""
                    INSERT OR IGNORE INTO slots (slot_date, slot_time, status)
                    VALUES (?, ?, 'free')
                """, (date_str, time_str))
        
        await db.commit()
        print(f"✅ Созданы слоты на {days_ahead} дней вперёд по расписанию")

async def fix_broken_bookings():
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        await db.execute("""
            UPDATE slots 
            SET status = 'completed' 
            WHERE status = 'booked' AND slot_date < ?
        """, (today,))
        
        await db.execute("""
            UPDATE slots 
            SET status = 'free', patient_id = NULL 
            WHERE status = 'booked' AND patient_id IS NULL
        """)
        
        await db.commit()
        print("✅ Битые записи исправлены")

async def book_slot(slot_id: int, patient_id: int, selected_date: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("BEGIN TRANSACTION")
            
            cursor = await db.execute(
                "SELECT status FROM slots WHERE id = ?", 
                (slot_id,)
            )
            row = await cursor.fetchone()
            
            if not row or row[0] != 'free':
                await db.rollback()
                return False
            
            cursor = await db.execute("""
                SELECT id FROM slots 
                WHERE patient_id = ? AND status = 'booked'
            """, (patient_id,))
            existing = await cursor.fetchone()
            
            if existing:
                print(f"❌ У пациента уже есть активная запись (id={existing[0]})")
                await db.rollback()
                return False
            
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
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM patients WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def save_patient(telegram_id: int, name: str, phone: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO patients (telegram_id, name, phone)
            VALUES (?, ?, ?)
        """, (telegram_id, name, phone))
        await db.commit()

async def get_free_times(date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, slot_time 
            FROM slots 
            WHERE slot_date = ? AND status = 'free'
            ORDER BY slot_time
        """, (date_str,))
        return await cursor.fetchall()

# ============================================
# БЛОКИРОВКА ДНЕЙ
# ============================================

async def block_day(date_str: str, reason: str, comment: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO blocked_days (block_date, reason, comment)
            VALUES (?, ?, ?)
        """, (date_str, reason, comment))
        await db.commit()

async def unblock_day(date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blocked_days WHERE block_date = ?", (date_str,))
        await db.commit()

async def get_blocked_day(date_str: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT reason, comment FROM blocked_days WHERE block_date = ?",
            (date_str,)
        )
        row = await cursor.fetchone()
        return {"reason": row[0], "comment": row[1]} if row else None

async def get_all_blocked_days():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT block_date, reason, comment FROM blocked_days ORDER BY block_date")
        rows = await cursor.fetchall()
        return [{"date": row[0], "reason": row[1], "comment": row[2]} for row in rows]

# ============================================
# РАБОЧИЕ ЧАСЫ
# ============================================

async def save_working_hours(day: str, start_hour: str, end_hour: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO working_hours (day, start_hour, end_hour)
            VALUES (?, ?, ?)
        """, (day, start_hour, end_hour))
        await db.commit()

async def get_working_hours(day: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT start_hour, end_hour FROM working_hours WHERE day = ?",
            (day,)
        )
        row = await cursor.fetchone()
        if row:
            return {"start": row[0], "end": row[1]}
        return None

async def get_all_working_hours():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT day, start_hour, end_hour FROM working_hours")
        rows = await cursor.fetchall()
        result = {}
        for row in rows:
            result[row[0]] = {"start": row[1], "end": row[2]}
        return result

# ============================================
# НАПОМИНАНИЯ — ФИНАЛЬНАЯ ВЕРСИЯ (БЕЗ УСЛОВИЯ ПО ВРЕМЕНИ)
# ============================================

async def get_slots_for_reminder() -> list:
    """
    Возвращает ВСЕ слоты, которым ещё не отправили напоминание
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, patient_id, slot_date, slot_time 
            FROM slots 
            WHERE status = 'booked' 
            AND reminder_sent = 0
        """)
        rows = await cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "patient_id": row[1],
                "slot_date": row[2],
                "slot_time": row[3]
            })
        return result

async def mark_reminder_sent(slot_id: int):
    """Отмечает, что напоминание для слота отправлено"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE slots SET reminder_sent = 1 WHERE id = ?",
            (slot_id,)
        )
        await db.commit()

async def get_patient_telegram_by_slot(slot_id: int) -> int:
    """Возвращает telegram_id пациента по ID слота"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT patients.telegram_id 
            FROM slots 
            JOIN patients ON slots.patient_id = patients.id
            WHERE slots.id = ?
        """, (slot_id,))
        row = await cursor.fetchone()
        return row[0] if row else None