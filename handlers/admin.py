import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database import DB_PATH, block_day, get_all_blocked_days
from keyboards.admin_kb import admin_main_menu
from keyboards.calendar_kb import create_calendar

router = Router()

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
            await callback.message.edit_text(
                f"⚠️ День {date_str} уже заблокирован.\n"
                f"Причина: {existing[0]}"
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
    kb.button(text="🛠 Ремонт", callback_data=f"reason_repair_{date_str}")
    kb.button(text="📅 Выходной", callback_data=f"reason_dayoff_{date_str}")
    kb.button(text="❌ Отмена", callback_data="back_to_admin")
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
    
    # Маппинг причин
    reason_map = {
        "vacation": "Отпуск",
        "sick": "Больничный",
        "repair": "Ремонт",
        "dayoff": "Выходной"
    }
    reason_text = reason_map.get(reason_type, "Другое")
    
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

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery, is_admin: bool):
    await callback.message.delete()
    await callback.message.answer("👩‍⚕️ Панель администратора", reply_markup=admin_main_menu())

@router.message(F.text == "🔓 Освободить")
async def free_slot(message: Message, is_admin: bool):
    if not is_admin:
        return
    await message.answer("🔓 Функция освобождения слота в разработке.", reply_markup=admin_main_menu())