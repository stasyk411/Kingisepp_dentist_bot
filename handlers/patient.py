import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from database import (
    DB_PATH, book_slot, cancel_slot, save_patient, get_patient_id, 
    get_free_times, get_blocked_day, get_all_blocked_days,
    create_temp_booking, check_temp_booking, get_user_temp_booking, delete_temp_booking
)
from keyboards.patient_kb import patient_main_menu
from keyboards.calendar_kb import create_calendar
from keyboards.inline_kb import create_time_keyboard, create_confirmation_keyboard
from utils.validators import clean_phone, is_valid_phone

router = Router()

class BookingStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_phone = State()
    waiting_for_confirmation = State()  # Новый state для подтверждения

@router.message(F.text == "📝 Записаться")
async def start_booking(message: Message, state: FSMContext):
    # Получаем ID пациента
    patient_id = await get_patient_id(message.from_user.id)
    
    if patient_id:
        # Проверяем, есть ли у него активная запись
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                SELECT slot_date, slot_time FROM slots 
                WHERE patient_id = ? AND status = 'booked'
            """, (patient_id,))
            existing = await cursor.fetchone()
            
            if existing:
                date_str, time_str = existing
                await message.answer(
                    f"📅 У вас уже есть запись:\n"
                    f"🗓 {date_str} в {time_str}\n\n"
                    f"Вы можете отменить её в «Мои записи».",
                    reply_markup=patient_main_menu()
                )
                return
    
    # Получаем все заблокированные дни для подсветки в календаре
    blocked_days = await get_all_blocked_days()
    blocked_dict = {d["date"]: d["reason"] for d in blocked_days}
    
    # Если активной записи нет — показываем календарь
    await message.answer(
        "Выберите дату:", 
        reply_markup=create_calendar(
            datetime.now().year, 
            datetime.now().month, 
            blocked_dict,
            for_patient=True
        )
    )
    await state.set_state(BookingStates.waiting_for_date)

@router.callback_query(BookingStates.waiting_for_date, F.data.startswith("cal_"))
async def calendar_navigation(callback: CallbackQuery):
    _, year, month = callback.data.split("_")
    
    # Получаем обновленные заблокированные дни
    blocked_days = await get_all_blocked_days()
    blocked_dict = {d["date"]: d["reason"] for d in blocked_days}
    
    await callback.message.edit_text(
        "Выберите дату:", 
        reply_markup=create_calendar(int(year), int(month), blocked_dict, for_patient=True)
    )

@router.callback_query(BookingStates.waiting_for_date, F.data == "cancel_booking")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Запись отменена", reply_markup=patient_main_menu())

@router.callback_query(BookingStates.waiting_for_date, F.data.startswith("date_"))
async def date_selected(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]
    
    # ✅ Проверяем, не заблокирован ли день
    blocked = await get_blocked_day(date_str)
    if blocked:
        # Показываем причину блокировки
        reason_map = {
            "Отпуск": "🏖 Врач в отпуске",
            "Больничный": "🤒 Врач на больничном",
            "Ремонт": "🛠 Ведутся технические работы",
            "Выходной": "📅 Выходной день"
        }
        message_text = reason_map.get(blocked["reason"], f"🚫 {blocked['reason']}")
        
        await callback.message.answer(
            f"{message_text}\n"
            f"Пожалуйста, выберите другую дату."
        )
        await callback.answer()
        return
    
    await state.update_data(selected_date=date_str)

    # Получаем свободные слоты
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
    
    # Получаем дату и время слота
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT slot_date, slot_time FROM slots WHERE id = ?", 
            (slot_id,)
        )
        row = await cursor.fetchone()
        if not row:
            await callback.message.answer("❌ Ошибка: слот не найден")
            await callback.answer()
            return
        
        slot_date, slot_time = row
    
    # Проверяем, не заблокирован ли слот временно
    is_temp_booked = await check_temp_booking(slot_date, slot_time)
    if is_temp_booked:
        await callback.message.answer(
            "❌ К сожалению, это время только что выбрал другой пациент.\n"
            "Пожалуйста, выберите другое время."
        )
        await callback.answer()
        return
    
    # Создаем временную блокировку на 10 минут
    temp_id = await create_temp_booking(
        slot_date, 
        slot_time, 
        callback.from_user.id, 
        minutes=10
    )
    
    if not temp_id:
        await callback.message.answer(
            "❌ Ошибка при бронировании времени.\n"
            "Попробуйте ещё раз."
        )
        await callback.answer()
        return
    
    # Сохраняем данные
    await state.update_data(
        slot_id=slot_id,
        slot_date=slot_date,
        slot_time=slot_time,
        temp_id=temp_id
    )
    
    # Проверяем, есть ли телефон у пациента
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT phone FROM patients WHERE telegram_id = ?", 
            (callback.from_user.id,)
        )
        patient = await cursor.fetchone()
    
    # Показываем экран подтверждения с таймером
    expires_at = datetime.now() + timedelta(minutes=10)
    time_str = expires_at.strftime("%H:%M:%S")
    
    if patient and patient[0]:
        # Телефон есть - сразу показываем подтверждение
        await callback.message.edit_text(
            f"📅 {slot_date} в {slot_time}\n\n"
            f"⏳ Время на подтверждение: до {time_str}\n\n"
            f"Подтвердите запись:",
            reply_markup=create_confirmation_keyboard()
        )
        await state.set_state(BookingStates.waiting_for_confirmation)
    else:
        # Телефона нет - сначала просим телефон
        await callback.message.edit_text(
            f"📅 {slot_date} в {slot_time}\n\n"
            f"📱 Введите ваш номер телефона для связи\n"
            f"(например: +79001234567)\n\n"
            f"⏳ Время на подтверждение: до {time_str}",
            reply_markup=None
        )
        await state.set_state(BookingStates.waiting_for_phone)

@router.callback_query(BookingStates.waiting_for_time, F.data == "back_to_calendar")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext):
    # Получаем обновленные заблокированные дни
    blocked_days = await get_all_blocked_days()
    blocked_dict = {d["date"]: d["reason"] for d in blocked_days}
    
    await callback.message.edit_text(
        "Выберите дату:", 
        reply_markup=create_calendar(
            datetime.now().year, 
            datetime.now().month, 
            blocked_dict,
            for_patient=True
        )
    )
    await state.set_state(BookingStates.waiting_for_date)

@router.message(BookingStates.waiting_for_phone)
async def phone_entered(message: Message, state: FSMContext):
    phone = clean_phone(message.text)

    if not is_valid_phone(phone):
        await message.answer("❌ Некорректный номер. Попробуйте ещё раз:")
        return

    await save_patient(message.from_user.id, message.from_user.full_name, phone)
    
    # После сохранения телефона показываем подтверждение
    data = await state.get_data()
    slot_date = data.get("slot_date")
    slot_time = data.get("slot_time")
    
    # Проверяем, активна ли еще временная блокировка
    temp_booking = await get_user_temp_booking(message.from_user.id)
    if not temp_booking:
        await message.answer(
            "❌ Время на подтверждение истекло.\n"
            "Пожалуйста, запишитесь заново.",
            reply_markup=patient_main_menu()
        )
        await state.clear()
        return
    
    expires_at = datetime.fromisoformat(temp_booking['expires_at'])
    time_str = expires_at.strftime("%H:%M:%S")
    
    await message.answer(
        f"📅 {slot_date} в {slot_time}\n\n"
        f"⏳ Время на подтверждение: до {time_str}\n\n"
        f"Подтвердите запись:",
        reply_markup=create_confirmation_keyboard()
    )
    await state.set_state(BookingStates.waiting_for_confirmation)

@router.callback_query(BookingStates.waiting_for_confirmation, F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    slot_id = data["slot_id"]
    selected_date = data["selected_date"]
    
    # Проверяем, активна ли временная блокировка
    temp_booking = await get_user_temp_booking(callback.from_user.id)
    if not temp_booking:
        await callback.message.edit_text(
            "❌ Время на подтверждение истекло.\n"
            "Пожалуйста, запишитесь заново.",
            reply_markup=None
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=patient_main_menu()
        )
        await state.clear()
        return
    
    # Дополнительная проверка на блокировку дня
    blocked = await get_blocked_day(selected_date)
    if blocked:
        reason_map = {
            "Отпуск": "🏖 Врач в отпуске",
            "Больничный": "🤒 Врач на больничном",
            "Ремонт": "🛠 Ведутся технические работы",
            "Выходной": "📅 Выходной день"
        }
        message_text = reason_map.get(blocked["reason"], f"🚫 {blocked['reason']}")
        
        await callback.message.edit_text(
            f"{message_text}\n"
            f"Пожалуйста, выберите другую дату.",
            reply_markup=None
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=patient_main_menu()
        )
        await state.clear()
        return
    
    # Проверяем время записи (не менее 3 часов)
    slot_time = data.get("slot_time")
    appointment_time = datetime.strptime(f"{selected_date} {slot_time}", "%Y-%m-%d %H:%M")
    now = datetime.now()
    
    if appointment_time - now < timedelta(hours=3):
        await callback.message.edit_text(
            "❌ Запись возможна не позднее чем за 3 часа до приёма.\n"
            "Пожалуйста, выберите другое время.",
            reply_markup=None
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=patient_main_menu()
        )
        await state.clear()
        return
    
    patient_id = await get_patient_id(callback.from_user.id)
    
    if not patient_id:
        await callback.message.edit_text(
            "❌ Ошибка: пациент не найден", 
            reply_markup=None
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=patient_main_menu()
        )
        await state.clear()
        return
    
    # Бронируем слот
    success = await book_slot(slot_id, patient_id, selected_date)
    
    if success:
        # Удаляем временную блокировку
        await delete_temp_booking(temp_booking['slot_date'], temp_booking['slot_time'])
        
        await callback.message.edit_text(
            "✅ Вы успешно записаны!\n\n"
            "🔔 Напоминание придет за 24 часа.\n\n"
            "❌ Отменить можно в «Мои записи»",
            reply_markup=None
        )
        await callback.message.answer(
            "Главное меню:",
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
        
        await callback.message.edit_text(
            error_msg,
            reply_markup=None
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=patient_main_menu()
        )
    
    await state.clear()

@router.callback_query(BookingStates.waiting_for_confirmation, F.data == "cancel_confirmation")
async def cancel_confirmation(callback: CallbackQuery, state: FSMContext):
    # Удаляем временную блокировку
    temp_booking = await get_user_temp_booking(callback.from_user.id)
    if temp_booking:
        await delete_temp_booking(temp_booking['slot_date'], temp_booking['slot_time'])
    
    # Убираем клавиатуру из редактируемого сообщения
    await callback.message.edit_text(
        "❌ Запись отменена.\n"
        "Если передумаете - запишитесь снова.",
        reply_markup=None  # ← ВАЖНО: убираем клавиатуру
    )
    
    # Отправляем новое сообщение с главным меню
    await callback.message.answer(
        "Главное меню:",
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
    # Проверяем, что после cancel_ идёт число (ID слота), а не текст
    parts = callback.data.split("_")
    if len(parts) != 2 or not parts[1].isdigit():
        # Это не отмена записи, а что-то другое (например, cancel_confirmation)
        await callback.answer()
        return
    
    slot_id = int(parts[1])

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
        
        patient_id = await get_patient_id(callback.from_user.id)
        if patient_id != slot_patient_id:
            await callback.message.answer("❌ Это не ваша запись")
            await callback.answer()
            return

    success = await cancel_slot(slot_id, patient_id)

    if success:
        await callback.message.answer("✅ Запись отменена. Слот освобожден.")
        await callback.message.delete()
        await callback.answer()
    else:
        await callback.message.answer("❌ Ошибка при отмене")
        await callback.answer()