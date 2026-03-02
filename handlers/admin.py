import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database import DB_PATH
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
    await message.answer("⛔ Выберите дату для отмены:", reply_markup=create_calendar())

@router.callback_query(F.data.startswith("date_"))
async def cancel_day_confirm(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    date_str = callback.data.split("_")[1]
    
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
        await callback.message.edit_text(f"✅ День {date_str} отменен (записей не было).")
        return
    
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

@router.callback_query(F.data.startswith("confirm_cancel_"))
async def cancel_day_execute(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        return
    
    date_str = callback.data.split("_")[2]
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE slots SET status='free', patient_id=NULL, cancelled_by='doctor' WHERE slot_date = ?", (date_str,))
        await db.commit()
    
    await callback.message.edit_text(f"✅ День {date_str} отменен.\n📞 Не забудьте обзвонить пациентов.")

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery, is_admin: bool):
    await callback.message.delete()
    await callback.message.answer("👩‍⚕️ Панель администратора", reply_markup=admin_main_menu())

@router.message(F.text == "🔓 Освободить")
async def free_slot(message: Message, is_admin: bool):
    if not is_admin:
        return
    await message.answer("🔓 Функция освобождения слота в разработке.", reply_markup=admin_main_menu())
