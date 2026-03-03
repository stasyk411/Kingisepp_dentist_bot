import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from database import DB_PATH, book_slot, cancel_slot, save_patient, get_patient_id, get_free_times
from keyboards.patient_kb import patient_main_menu
from keyboards.calendar_kb import create_calendar
from keyboards.inline_kb import create_time_keyboard
from utils.validators import clean_phone, is_valid_phone

router = Router()

class BookingStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_phone = State()

@router.message(F.text == "📝 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await message.answer("Выберите дату:", reply_markup=create_calendar())
    await state.set_state(BookingStates.waiting_for_date)

@router.callback_query(BookingStates.waiting_for_date, F.data.startswith("cal_"))
async def calendar_navigation(callback: CallbackQuery):
    _, year, month = callback.data.split("_")
    await callback.message.edit_text("Выберите дату:", reply_markup=create_calendar(int(year), int(month)))

@router.callback_query(BookingStates.waiting_for_date, F.data == "cancel_booking")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Запись отменена", reply_markup=patient_main_menu())

@router.callback_query(BookingStates.waiting_for_date, F.data.startswith("date_"))
async def date_selected(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]
    await state.update_data(selected_date=date_str)

    free_times = await get_free_times(date_str)

    if not free_times:
        await callback.message.answer(
            "❌ На эту дату нет свободных слотов.\n"
            "Попробуйте выбрать другую дату."
        )
        return

    await callback.message.edit_text(
        f"📅 {date_str}\n\nВыберите время:", 
        reply_markup=create_time_keyboard(free_times)
    )
    await state.set_state(BookingStates.waiting_for_time)

@router.callback_query(BookingStates.waiting_for_time, F.data.startswith("time_"))
async def time_selected(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split("_")[1])
    await state.update_data(slot_id=slot_id)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT phone FROM patients WHERE telegram_id = ?", 
            (callback.from_user.id,)
        )
        patient = await cursor.fetchone()

    if patient and patient[0]:
        await confirm_booking(callback, state)
    else:
        await callback.message.edit_text(
            "📱 Введите ваш номер телефона для связи\n"
            "(например: +79001234567)", 
            reply_markup=None
        )
        await state.set_state(BookingStates.waiting_for_phone)

@router.callback_query(BookingStates.waiting_for_time, F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Выберите дату:", reply_markup=create_calendar())
    await state.set_state(BookingStates.waiting_for_date)

@router.message(BookingStates.waiting_for_phone)
async def phone_entered(message: Message, state: FSMContext):
    phone = clean_phone(message.text)

    if not is_valid_phone(phone):
        await message.answer("❌ Некорректный номер. Попробуйте ещё раз:")
        return

    await save_patient(message.from_user.id, message.from_user.full_name, phone)
    await confirm_booking(message, state)

async def confirm_booking(event, state: FSMContext):
    data = await state.get_data()
    slot_id = data["slot_id"]
    selected_date = data["selected_date"]
    
    # ПОЛУЧАЕМ ВРЕМЯ СЛОТА ИЗ БАЗЫ
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT slot_time FROM slots WHERE id = ?", 
            (slot_id,)
        )
        row = await cursor.fetchone()
        if not row:
            await event.answer("❌ Ошибка: слот не найден", reply_markup=patient_main_menu())
            await state.clear()
            return
        
        slot_time = row[0]
    
    # ПРОВЕРЯЕМ, ЧТО ДО ПРИЁМА > 3 ЧАСОВ
    appointment_time = datetime.strptime(f"{selected_date} {slot_time}", "%Y-%m-%d %H:%M")
    now = datetime.now()
    
    if appointment_time - now < timedelta(hours=3):
        await event.answer(
            "❌ Запись возможна не позднее чем за 3 часа до приёма.\n"
            "Пожалуйста, выберите другое время.",
            reply_markup=patient_main_menu()
        )
        await state.clear()
        return
    
    # ПОЛУЧАЕМ ID ПАЦИЕНТА
    patient_id = await get_patient_id(event.from_user.id)
    
    if not patient_id:
        await event.answer("❌ Ошибка: пациент не найден", reply_markup=patient_main_menu())
        await state.clear()
        return
    
    # БРОНИРУЕМ СЛОТ
    success = await book_slot(slot_id, patient_id, selected_date)
    
    if success:
        await event.answer(
            "✅ Вы успешно записаны!\n\n"
            "🔔 Напоминание придет за 24 часа.\n\n"
            "❌ Отменить можно в «Мои записи»",
            reply_markup=patient_main_menu()
        )
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT status FROM slots WHERE id = ?", 
                (slot_id,)
            )
            row = await cursor.fetchone()
            if row and row[0] == 'free':
                error_msg = "❌ У вас уже есть запись на этот день.\nПроверьте в «Мои записи»."
            else:
                error_msg = "❌ К сожалению, это время только что заняли.\nПопробуйте выбрать другое."
        
        await event.answer(
            error_msg,
            reply_markup=patient_main_menu()
        )
    
    await state.clear()

@router.message(F.text == "📅 Мои записи")
async def my_appointments(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT s.id, s.slot_date, s.slot_time
            FROM slots s
            JOIN patients p ON s.patient_id = p.id
            WHERE p.telegram_id = ? AND s.status = 'booked' AND s.slot_date >= date('now')
            ORDER BY s.slot_date, s.slot_time
        """, (message.from_user.id,))
        appointments = await cursor.fetchall()

    if not appointments:
        await message.answer("📅 У вас нет предстоящих записей.", reply_markup=patient_main_menu())
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    for slot_id, date, time in appointments:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{slot_id}")]
        ])
        await message.answer(f"📅 {date} в {time}", reply_markup=kb)

@router.callback_query(F.data.startswith("cancel_"))
async def cancel_appointment(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[1])

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT slot_date, slot_time, patient_id FROM slots WHERE id = ?", 
            (slot_id,)
        )
        row = await cursor.fetchone()

        if not row:
            await callback.message.answer("❌ Запись не найдена")
            await callback.answer()
            return

        date_str, time_str, slot_patient_id = row
        
        # Проверяем, что это его запись
        patient_id = await get_patient_id(callback.from_user.id)
        if patient_id != slot_patient_id:
            await callback.message.answer("❌ Это не ваша запись")
            await callback.answer()
            return
        
        appointment_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        if appointment_time - datetime.now() < timedelta(hours=24):
            await callback.message.answer(
                "❌ Отменить можно не позднее чем за 24 часа до приема.\n"
                f"Позвоните врачу: +7 (911) 775-04-24"
            )
            await callback.answer()
            return

    success = await cancel_slot(slot_id, patient_id)

    if success:
        await callback.message.edit_text("✅ Запись отменена. Слот освобожден.")
        await callback.answer("✅ Отменено")
    else:
        await callback.message.answer("❌ Ошибка при отмене")
        await callback.answer()