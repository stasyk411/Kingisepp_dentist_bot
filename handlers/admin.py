import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database import (
    DB_PATH, block_day, get_all_blocked_days,
    get_all_working_hours, get_working_hours,
    generate_future_slots  # ✅ Добавлен импорт
)
from keyboards.admin_kb import admin_main_menu
from keyboards.calendar_kb import create_calendar
from keyboards.inline_kb import days_keyboard, hours_start_keyboard, hours_end_keyboard

router = Router()

# -------------------- СУЩЕСТВУЮЩИЕ ХЕНДЛЕРЫ --------------------

@router.message(F.text == "📋 Сегодня")
async def today(message: Message, is_admin: bool):
    if not is_admin:
        return
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT s.slot_time, p.name, p.phone
            FROM slots s
            JOIN patients p ON s.patient_id = p.id
            WHERE s.slot_date = ? AND s.status = 'booked'
            ORDER BY s.slot_time
        """, (today_str,))
        appointments = await cursor.fetchall()
    
    if not appointments:
        await message.answer("📋 На сегодня записей нет.", reply_markup=admin_main_menu())
        return
    
    text = "📋 Записи на сегодня:\n\n"
    for time, name, phone in appointments:
        text += f"🕐 {time} — {name} {phone}\n"
    
    await message.answer(text, reply_markup=admin_main_menu())

@router.message(F.text == "📅 Завтра")
async def tomorrow(message: Message, is_admin: bool):
    if not is_admin:
        return
    
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT s.slot_time, p.name, p.phone
            FROM slots s
            JOIN patients p ON s.patient_id = p.id
            WHERE s.slot_date = ? AND s.status = 'booked'
            ORDER BY s.slot_time
        """, (tomorrow_str,))
        appointments = await cursor.fetchall()
    
    if not appointments:
        await message.answer("📅 На завтра записей нет.", reply_markup=admin_main_menu())
        return
    
    text = "📅 Записи на завтра:\n\n"
    for time, name, phone in appointments:
        text += f"🕐 {time} — {name} {phone}\n"
    
    await message.answer(text, reply_markup=admin_main_menu())

@router.message(F.text == "⛔ Отмена дня")
async def cancel_day_start(message: Message, is_admin: bool):
    if not is_admin:
        return
    
    # Получаем все заблокированные дни для подсветки в календаре
    blocked_days = await get_all_blocked_days()
    blocked_dict = {d["date"]: d["reason"] for d in blocked_days}
    
    now = datetime.now()
    await message.answer(
        "⛔ Выберите дату для отмены:", 
        reply_markup=create_calendar(now.year, now.month, blocked_dict)
    )

@router.callback_query(F.data.startswith("date_"))
async def cancel_day_confirm(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    date_str = callback.data.split("_")[1]
    
    # Проверяем, есть ли уже блокировка
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT reason FROM blocked_days WHERE block_date = ?",
            (date_str,)
        )
        existing = await cursor.fetchone()
        if existing:
            # Даем возможность снять блокировку
            kb = InlineKeyboardBuilder()
            kb.button(text="🔓 Снять блокировку", callback_data=f"unblock_{date_str}")
            kb.button(text="🔙 Назад", callback_data="back_to_admin")
            kb.adjust(1)
            
            await callback.message.edit_text(
                f"⚠️ День {date_str} уже заблокирован.\n"
                f"Причина: {existing[0]}\n\n"
                f"Что делаем?",
                reply_markup=kb.as_markup()
            )
            return
    
    # Проверяем записи на этот день
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT s.slot_time, p.name, p.phone
            FROM slots s
            JOIN patients p ON s.patient_id = p.id
            WHERE s.slot_date = ? AND s.status = 'booked'
            ORDER BY s.slot_time
        """, (date_str,))
        patients = await cursor.fetchall()
    
    if not patients:
        # Если записей нет — сразу выбираем причину
        await ask_reason(callback, date_str)
        return
    
    # Если есть записи — показываем список и просим подтверждение
    patients_list = "\n".join([f"  • {time} — {name} {phone}" for time, name, phone in patients])
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, отменить день", callback_data=f"confirm_cancel_{date_str}")
    kb.button(text="❌ Нет, вернуться", callback_data="back_to_admin")
    kb.adjust(1)
    
    await callback.message.edit_text(
        f"⚠️ <b>ВНИМАНИЕ!</b>\n\n"
        f"Вы собираетесь отменить день {date_str}.\n\n"
        f"Записано пациентов: {len(patients)}\n"
        f"{patients_list}\n\n"
        f"❌ Автоматические уведомления НЕ отправляются.\n"
        f"📞 Вы должны обзвонить этих пациентов самостоятельно.\n\n"
        f"Подтвердите действие:",
        reply_markup=kb.as_markup()
    )

async def ask_reason(callback: CallbackQuery, date_str: str):
    """Спрашивает причину блокировки"""
    kb = InlineKeyboardBuilder()
    kb.button(text="🏖 Отпуск", callback_data=f"reason_vacation_{date_str}")
    kb.button(text="🤒 Больничный", callback_data=f"reason_sick_{date_str}")
    kb.button(text="📅 Выходной", callback_data=f"reason_dayoff_{date_str}")
    kb.button(text="🔙 Отмена", callback_data="back_to_admin")
    kb.adjust(1)
    
    await callback.message.edit_text(
        f"📅 {date_str}\n\n"
        f"Выберите причину блокировки:",
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data.startswith("reason_"))
async def save_reason(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    parts = callback.data.split("_")
    reason_type = parts[1]
    date_str = parts[2]
    
    # Определяем причину
    if reason_type == "vacation":
        reason_text = "Отпуск"
    elif reason_type == "sick":
        reason_text = "Больничный"
    elif reason_type == "dayoff":
        reason_text = "Выходной"
    else:
        reason_text = "Другое"
    
    # Сохраняем в blocked_days
    await block_day(date_str, reason_text, "")
    
    # Обновляем статус в slots
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE slots 
            SET status='blocked', patient_id=NULL, cancelled_by='doctor' 
            WHERE slot_date = ?
        """, (date_str,))
        await db.commit()
    
    await callback.message.edit_text(
        f"✅ День {date_str} заблокирован.\n"
        f"Причина: {reason_text}"
    )

@router.callback_query(F.data.startswith("confirm_cancel_"))
async def cancel_day_execute(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    date_str = callback.data.split("_")[2]
    
    # Переходим к выбору причины
    await ask_reason(callback, date_str)

@router.callback_query(F.data.startswith("unblock_"))
async def unblock_day(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    date_str = callback.data.split("_")[1]
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Удаляем из blocked_days
        await db.execute("DELETE FROM blocked_days WHERE block_date = ?", (date_str,))
        # Возвращаем статус слотов в 'free'
        await db.execute("""
            UPDATE slots 
            SET status='free', patient_id=NULL, cancelled_by=NULL 
            WHERE slot_date = ?
        """, (date_str,))
        await db.commit()
    
    await callback.message.edit_text(
        f"✅ Блокировка снята с {date_str}.\n"
        f"День снова доступен для записи."
    )

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery, is_admin: bool):
    await callback.message.delete()
    await callback.message.answer("👩‍⚕️ Панель администратора", reply_markup=admin_main_menu())

# -------------------- НОВЫЕ ХЕНДЛЕРЫ НАСТРОЕК --------------------

# Словарь для хранения временных данных настройки (в реальном проекте лучше использовать FSM)
user_settings = {}

@router.message(F.text == "⚙️ Настройки")
async def settings_start(message: Message, is_admin: bool):
    if not is_admin:
        return
    
    # Получаем текущие настройки из БД
    settings = await get_all_working_hours()
    
    # Формируем текст с текущим расписанием (красиво с эмодзи)
    days_ru = {"mon": "ПН", "tue": "ВТ", "wed": "СР", "thu": "ЧТ", "fri": "ПТ"}
    text = "⚙️ <b>Текущее расписание</b>\n\n"
    
    for day_code, day_name in days_ru.items():
        if day_code in settings:
            text += f"✅ {day_name}: {settings[day_code]['start']}:00 — {settings[day_code]['end']}:00\n"
        else:
            text += f"❌ {day_name}: <i>не настроено</i>\n"
    
    text += "\nВыберите день для настройки:"
    
    await message.answer(text, reply_markup=days_keyboard())

@router.callback_query(F.data.startswith("day_"))
async def select_day(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    day = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    # Сохраняем выбранный день
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]["day"] = day
    
    # Получаем текущее название дня
    days_ru = {
        "mon": "Понедельник",
        "tue": "Вторник",
        "wed": "Среда",
        "thu": "Четверг",
        "fri": "Пятница"
    }
    day_name = days_ru.get(day, day)
    
    # Проверяем, есть ли уже настройки для этого дня
    existing = await get_working_hours(day)
    
    if existing:
        # Если день уже настроен — показываем текущие часы и кнопку изменения
        kb = InlineKeyboardBuilder()
        kb.button(text="🔄 Изменить", callback_data=f"edit_day_{day}")
        kb.button(text="🔙 Назад", callback_data="back_to_days")
        kb.adjust(1)
        
        await callback.message.edit_text(
            f"⚙️ {day_name}\n"
            f"Текущие часы: {existing['start']}:00 — {existing['end']}:00\n\n"
            f"Что делаем?",
            reply_markup=kb.as_markup()
        )
    else:
        # Если не настроен — сразу к выбору часов
        await callback.message.edit_text(
            f"⚙️ {day_name}\n\n"
            f"Выберите время начала работы:",
            reply_markup=hours_start_keyboard()
        )

@router.callback_query(F.data.startswith("edit_day_"))
async def edit_day(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    day = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    # Сохраняем выбранный день (для изменения)
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]["day"] = day
    
    # Получаем название дня
    days_ru = {
        "mon": "Понедельник",
        "tue": "Вторник",
        "wed": "Среда",
        "thu": "Четверг",
        "fri": "Пятница"
    }
    day_name = days_ru.get(day, day)
    
    await callback.message.edit_text(
        f"⚙️ {day_name} (изменение)\n\n"
        f"Выберите новое время начала работы:",
        reply_markup=hours_start_keyboard()
    )

@router.callback_query(F.data.startswith("hour_start_"))
async def select_start_hour(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    hour = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    # Сохраняем выбранный час начала
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]["start"] = hour
    
    # Получаем название дня
    day = user_settings[user_id].get("day", "")
    days_ru = {
        "mon": "Понедельник",
        "tue": "Вторник",
        "wed": "Среда",
        "thu": "Четверг",
        "fri": "Пятница"
    }
    day_name = days_ru.get(day, day)
    
    await callback.message.edit_text(
        f"⚙️ {day_name}\n"
        f"Начало: {hour}:00\n\n"
        f"Выберите время окончания работы:",
        reply_markup=hours_end_keyboard(hour)
    )

@router.callback_query(F.data.startswith("hour_end_"))
async def select_end_hour(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    hour = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    # Сохраняем выбранный час окончания
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]["end"] = hour
    
    # Получаем данные
    day = user_settings[user_id].get("day", "")
    start = user_settings[user_id].get("start", "")
    
    # Сохраняем в БД (таблица уже существует в database.py)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO working_hours (day, start_hour, end_hour)
            VALUES (?, ?, ?)
        """, (day, start, hour))
        await db.commit()
    
    # ✅ Генерируем слоты заново после изменения расписания
    await generate_future_slots()
    
    # Получаем название дня
    days_ru = {
        "mon": "Понедельник",
        "tue": "Вторник",
        "wed": "Среда",
        "thu": "Четверг",
        "fri": "Пятница"
    }
    day_name = days_ru.get(day, day)
    
    await callback.message.edit_text(
        f"✅ {day_name}: {start}:00 — {hour}:00\n\n"
        f"Настройка сохранена.",
        reply_markup=days_keyboard()
    )
    
    # Очищаем временные данные
    if user_id in user_settings:
        del user_settings[user_id]

@router.callback_query(F.data == "back_to_days")
async def back_to_days(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    # Получаем обновленные настройки
    settings = await get_all_working_hours()
    
    # Формируем текст с текущим расписанием
    days_ru = {"mon": "ПН", "tue": "ВТ", "wed": "СР", "thu": "ЧТ", "fri": "ПТ"}
    text = "⚙️ <b>Текущее расписание</b>\n\n"
    
    for day_code, day_name in days_ru.items():
        if day_code in settings:
            text += f"✅ {day_name}: {settings[day_code]['start']}:00 — {settings[day_code]['end']}:00\n"
        else:
            text += f"❌ {day_name}: <i>не настроено</i>\n"
    
    text += "\nВыберите день для настройки:"
    
    await callback.message.edit_text(text, reply_markup=days_keyboard())

@router.callback_query(F.data == "settings_done")
async def settings_done(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    await callback.message.delete()
    await callback.message.answer("👩‍⚕️ Панель администратора", reply_markup=admin_main_menu())

# Удаляем старый хендлер "🔓 Освободить" (больше не нужен)