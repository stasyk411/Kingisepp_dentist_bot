import aiosqlite
from datetime import datetime, timedelta
from utils.logger import logger

DB_PATH = "dentist_bot.db"

async def init_db():
    """Инициализация базы данных с миграциями"""
    from migrations.runner import run_migrations
    
    # Запускаем миграции
    await run_migrations(DB_PATH)
    
    # Создаем слоты на 30 дней вперед по расписанию
    await generate_future_slots()
    await fix_broken_bookings()

async def generate_future_slots(days_ahead: int = 30):
    """Генерация слотов на указанное количество дней вперед по расписанию"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем рабочие часы из настроек
        working_hours = await get_all_working_hours()
        
        if not working_hours:
            logger.warning("Расписание не настроено. Слоты не созданы.")
            return
        
        # Удаляем старые свободные слоты
        await db.execute("""
            DELETE FROM slots 
            WHERE slot_date >= date('now') 
            AND status = 'free'
        """)
        
        # Маппинг дней недели
        day_map = {
            0: "mon",  # понедельник
            1: "tue",  # вторник
            2: "wed",  # среда
            3: "thu",  # четверг
            4: "fri"   # пятница
        }
        
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day_offset in range(0, days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            weekday = current_date.weekday()
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Проверяем, есть ли настройки для этого дня недели
            day_code = day_map.get(weekday)
            if not day_code or day_code not in working_hours:
                continue
            
            # Создаем слоты согласно расписанию
            start_hour = int(working_hours[day_code]['start'])
            end_hour = int(working_hours[day_code]['end'])
            
            for hour in range(start_hour, end_hour + 1):
                time_str = f"{hour:02d}:00"
                await db.execute("""
                    INSERT OR IGNORE INTO slots (slot_date, slot_time, status)
                    VALUES (?, ?, 'free')
                """, (date_str, time_str))
        
        await db.commit()
        logger.success(f"Созданы слоты на {days_ahead} дней вперёд по расписанию")

async def fix_broken_bookings():
    """Исправляет битые записи"""
    async with aiosqlite.connect(DB_PATH) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Помечаем прошедшие записи как completed
        await db.execute("""
            UPDATE slots 
            SET status = 'completed' 
            WHERE status = 'booked' AND slot_date < ?
        """, (today,))
        
        # Очищаем слоты без patient_id
        await db.execute("""
            UPDATE slots 
            SET status = 'free', patient_id = NULL 
            WHERE status = 'booked' AND patient_id IS NULL
        """)
        
        await db.commit()
        logger.success("Битые записи исправлены")

async def book_slot(slot_id: int, patient_id: int, selected_date: str) -> bool:
    """Бронирует слот для пациента"""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("BEGIN TRANSACTION")
            
            # Проверяем, свободен ли слот
            cursor = await db.execute(
                "SELECT status FROM slots WHERE id = ?", 
                (slot_id,)
            )
            row = await cursor.fetchone()
            
            if not row or row[0] != 'free':
                await db.rollback()
                return False
            
            # Проверяем, нет ли у пациента будущей записи
            cursor = await db.execute("""
                SELECT id FROM slots 
                WHERE patient_id = ? AND status = 'booked'
                AND slot_date >= date('now')
            """, (patient_id,))
            existing = await cursor.fetchone()
            
            if existing:
                logger.warning(
                    "У пациента уже есть активная запись", 
                    extra={
                        "patient_id": patient_id, 
                        "existing_slot_id": existing[0]
                    }
                )
                await db.rollback()
                return False
            
            # Бронируем слот
            await db.execute("""
                UPDATE slots 
                SET status='booked', patient_id=?, booked_at=CURRENT_TIMESTAMP 
                WHERE id=?
            """, (patient_id, slot_id))
            
            await db.commit()
            logger.info(
                "Слот забронирован", 
                extra={"slot_id": slot_id, "patient_id": patient_id}
            )
            return True
            
        except Exception as e:
            logger.error(
                "Ошибка при бронировании слота", 
                extra={
                    "error": str(e), 
                    "slot_id": slot_id, 
                    "patient_id": patient_id
                }
            )
            await db.rollback()
            return False

async def cancel_slot(slot_id: int, patient_id: int) -> bool:
    """Отменяет запись на слот"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, что слот принадлежит пациенту
        cursor = await db.execute(
            "SELECT status FROM slots WHERE id = ? AND patient_id = ?",
            (slot_id, patient_id)
        )
        if not await cursor.fetchone():
            return False
        
        # Отменяем запись
        await db.execute("""
            UPDATE slots 
            SET status='free', patient_id=NULL, cancelled_by='patient'
            WHERE id=?
        """, (slot_id,))
        await db.commit()
        
        logger.info(
            "Запись отменена", 
            extra={"slot_id": slot_id, "patient_id": patient_id}
        )
        return True

async def get_patient_id(telegram_id: int) -> int:
    """Получает ID пациента по telegram_id"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM patients WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def save_patient(telegram_id: int, name: str, phone: str = None):
    """Сохраняет или обновляет данные пациента"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO patients (telegram_id, name, phone)
            VALUES (?, ?, ?)
        """, (telegram_id, name, phone))
        await db.commit()
        
        logger.info(
            "Пациент сохранен", 
            extra={"telegram_id": telegram_id, "name": name}
        )

async def get_free_times(date_str: str):
    """Возвращает свободные слоты на дату"""
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
    """Блокирует день"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO blocked_days (block_date, reason, comment)
            VALUES (?, ?, ?)
        """, (date_str, reason, comment))
        await db.commit()
        logger.info("День заблокирован", extra={"date": date_str, "reason": reason})

async def unblock_day(date_str: str):
    """Разблокирует день"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blocked_days WHERE block_date = ?", (date_str,))
        await db.commit()
        logger.info("День разблокирован", extra={"date": date_str})

async def get_blocked_day(date_str: str):
    """Получает информацию о заблокированном дне"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT reason, comment FROM blocked_days WHERE block_date = ?",
            (date_str,)
        )
        row = await cursor.fetchone()
        return {"reason": row[0], "comment": row[1]} if row else None

async def get_all_blocked_days():
    """Получает все заблокированные дни"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT block_date, reason, comment 
            FROM blocked_days 
            ORDER BY block_date
        """)
        rows = await cursor.fetchall()
        return [{"date": row[0], "reason": row[1], "comment": row[2]} for row in rows]

# ============================================
# РАБОЧИЕ ЧАСЫ
# ============================================

async def save_working_hours(day: str, start_hour: str, end_hour: str):
    """Сохраняет рабочие часы для дня недели"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO working_hours (day, start_hour, end_hour)
            VALUES (?, ?, ?)
        """, (day, start_hour, end_hour))
        await db.commit()
        logger.info("Рабочие часы сохранены", extra={"day": day, "start": start_hour, "end": end_hour})

async def get_working_hours(day: str):
    """Получает рабочие часы для дня недели"""
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
    """Получает все рабочие часы"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT day, start_hour, end_hour FROM working_hours")
        rows = await cursor.fetchall()
        result = {}
        for row in rows:
            result[row[0]] = {"start": row[1], "end": row[2]}
        return result

# ============================================
# НАПОМИНАНИЯ — ЗА 24 ЧАСА
# ============================================

async def get_slots_for_reminder() -> list:
    """
    Возвращает слоты, для которых нужно отправить напоминание:
    - статус 'booked'
    - reminder_sent = 0
    - до начала приёма осталось ровно 24 часа (±5 минут)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, patient_id, slot_date, slot_time 
            FROM slots 
            WHERE status = 'booked' 
            AND reminder_sent = 0
            AND datetime(slot_date || ' ' || slot_time, '-24 hours') 
                BETWEEN datetime('now', '-5 minutes') 
                AND datetime('now', '+5 minutes')
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
        logger.debug("Напоминание отмечено как отправленное", extra={"slot_id": slot_id})

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