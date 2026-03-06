"""
ТЕСТ ДЛЯ ПРОВЕРКИ НАПОМИНАНИЙ
Запуск: python test_reminder.py

Проверяет:
1. Поиск слотов для напоминания
2. Отправку тестового напоминания
3. Работу планировщика
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from database import (
    get_slots_for_reminder,
    mark_reminder_sent,
    get_patient_telegram_by_slot,
    book_slot,
    save_patient,
    get_patient_id,
    DB_PATH
)
from scheduler.reminders import check_and_send_reminders
from config import ADMIN_IDS

# ============================================
# 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def setup_test_data():
    """Создаёт тестовые данные в БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Очищаем тестовые данные
    cursor.execute("DELETE FROM patients WHERE telegram_id = 999999")
    cursor.execute("DELETE FROM slots WHERE slot_date = '2026-03-07'")
    
    # Создаём тестового пациента
    cursor.execute("""
        INSERT OR REPLACE INTO patients (telegram_id, name, phone)
        VALUES (999999, 'Тест Пациент', '+79999999999')
    """)
    
    # Получаем его ID
    cursor.execute("SELECT id FROM patients WHERE telegram_id = 999999")
    patient_id = cursor.fetchone()[0]
    
    # Создаём тестовый слот с booked_at 24 часа назад
    booked_at = (datetime.now() - timedelta(hours=24, seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT OR REPLACE INTO slots 
        (slot_date, slot_time, patient_id, status, reminder_sent, booked_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "2026-03-07",
        "15:00",
        patient_id,
        "booked",
        0,
        booked_at
    ))
    
    conn.commit()
    conn.close()
    
    print("✅ Тестовые данные созданы")
    print(f"   Пациент ID: {patient_id}, Telegram: 999999")
    print("   Слот: 2026-03-07 15:00 (забронирован 24 часа назад)")

def cleanup_test_data():
    """Удаляет тестовые данные"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM patients WHERE telegram_id = 999999")
    cursor.execute("DELETE FROM slots WHERE slot_date = '2026-03-07'")
    conn.commit()
    conn.close()
    print("🧹 Тестовые данные очищены")

# ============================================
# 2. ТЕСТЫ
# ============================================

async def test_get_slots():
    """Тест 1: Поиск слотов для напоминания"""
    print("\n🔍 ТЕСТ 1: Поиск слотов для напоминания")
    
    slots = await get_slots_for_reminder()
    
    if slots:
        print(f"✅ Найдено {len(slots)} слотов")
        for slot in slots:
            print(f"   - Слот {slot['id']}: {slot['slot_date']} {slot['slot_time']}")
    else:
        print("❌ Слоты не найдены")
    
    return slots

async def test_get_telegram():
    """Тест 2: Получение telegram_id по слоту"""
    print("\n🔍 ТЕСТ 2: Получение telegram_id пациента")
    
    # Получаем ID тестового слота
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM slots WHERE slot_date = '2026-03-07'")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("❌ Тестовый слот не найден")
        return None
    
    slot_id = row[0]
    telegram_id = await get_patient_telegram_by_slot(slot_id)
    
    if telegram_id:
        print(f"✅ Telegram ID найден: {telegram_id}")
    else:
        print("❌ Telegram ID не найден")
    
    return telegram_id

async def test_mark_sent():
    """Тест 3: Отметка о отправке"""
    print("\n🔍 ТЕСТ 3: Отметка напоминания как отправленного")
    
    # Получаем ID тестового слота
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM slots WHERE slot_date = '2026-03-07'")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("❌ Тестовый слот не найден")
        return
    
    slot_id = row[0]
    await mark_reminder_sent(slot_id)
    
    # Проверяем что отметилось
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT reminder_sent FROM slots WHERE id = ?", (slot_id,))
    sent = cursor.fetchone()[0]
    conn.close()
    
    if sent == 1:
        print("✅ Напоминание отмечено как отправленное")
    else:
        print("❌ Ошибка: reminder_sent = {sent}")

async def test_check_reminders():
    """Тест 4: Запуск планировщика"""
    print("\n🔍 ТЕСТ 4: Запуск проверки напоминаний")
    
    await check_and_send_reminders()
    print("✅ Проверка завершена")

async def test_full_cycle():
    """Тест 5: Полный цикл (создание → поиск → отправка → отметка)"""
    print("\n🔍 ТЕСТ 5: ПОЛНЫЙ ЦИКЛ НАПОМИНАНИЙ")
    print("=" * 50)
    
    # Создаём тестовые данные
    setup_test_data()
    
    # Ждём 1 секунду
    await asyncio.sleep(1)
    
    # Ищем слоты
    slots = await get_slots_for_reminder()
    
    if not slots:
        print("❌ Слоты не найдены. Проверь booked_at")
        cleanup_test_data()
        return False
    
    print(f"✅ Найдено слотов: {len(slots)}")
    
    # Проверяем каждого
    for slot in slots:
        print(f"\n   Слот {slot['id']}: {slot['slot_date']} {slot['slot_time']}")
        
        # Получаем telegram
        telegram_id = await get_patient_telegram_by_slot(slot['id'])
        print(f"   Telegram ID: {telegram_id}")
        
        if telegram_id == 999999:
            print("   ✅ Данные совпадают")
        else:
            print(f"   ❌ Ожидалось 999999, получено {telegram_id}")
    
    # Отмечаем как отправленные
    for slot in slots:
        await mark_reminder_sent(slot['id'])
    
    # Проверяем что отметились
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for slot in slots:
        cursor.execute("SELECT reminder_sent FROM slots WHERE id = ?", (slot['id'],))
        sent = cursor.fetchone()[0]
        if sent == 1:
            print(f"✅ Слот {slot['id']} отмечен")
        else:
            print(f"❌ Слот {slot['id']} НЕ отмечен")
    conn.close()
    
    # Очищаем тестовые данные
    cleanup_test_data()
    
    print("\n" + "=" * 50)
    print("✅ ПОЛНЫЙ ЦИКЛ ЗАВЕРШЕН")
    return True

# ============================================
# 3. ЗАПУСК ТЕСТОВ
# ============================================

async def run_all_tests():
    """Запускает все тесты по порядку"""
    print("🧪 ЗАПУСК ТЕСТОВ НАПОМИНАНИЙ")
    print("=" * 50)
    
    # Создаём тестовые данные
    setup_test_data()
    await asyncio.sleep(1)
    
    # Тест 1
    slots = await test_get_slots()
    
    # Тест 2
    await test_get_telegram()
    
    # Тест 3
    await test_mark_sent()
    
    # Тест 4
    await test_check_reminders()
    
    # Очищаем
    cleanup_test_data()
    
    print("\n" + "=" * 50)
    print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")

if __name__ == "__main__":
    print("🐍 ТЕСТОВЫЙ ФАЙЛ ДЛЯ НАПОМИНАНИЙ")
    print("Возможные команды:")
    print("  1. python test_reminder.py          # полный цикл")
    print("  2. python test_reminder.py setup    # только создать тестовые данные")
    print("  3. python test_reminder.py check    # только проверить напоминания")
    print("  4. python test_reminder.py clean    # очистить тестовые данные")
    print("=" * 50)
    
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "setup":
            setup_test_data()
        elif cmd == "check":
            asyncio.run(check_and_send_reminders())
        elif cmd == "clean":
            cleanup_test_data()
        elif cmd == "full":
            asyncio.run(test_full_cycle())
    else:
        # Запускаем полный тест
        asyncio.run(test_full_cycle())