"""
Обработчик настроек пользователя
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_user_offset, save_user_offset
from keyboards.patient_kb import patient_main_menu
from keyboards.settings_kb import settings_menu_keyboard, back_to_settings_keyboard
from utils.time_utils import format_offset, parse_user_time, calculate_offset_from_time

router = Router()

class TimezoneStates(StatesGroup):
    waiting_for_time = State()

@router.message(F.text == "🌍 Часовой пояс")
async def show_settings(message: Message):
    """Показывает текущие настройки"""
    offset = await get_user_offset(message.from_user.id)
    offset_str = format_offset(offset)
    
    await message.answer(
        f"⚙️ Настройки\n\n"
        f"⏱ Текущее смещение: {offset_str}\n\n"
        f"Хочешь поменять — нажми «⏰ Сменить время».",
        reply_markup=settings_menu_keyboard(offset)
    )

@router.callback_query(F.data == "change_timezone")
async def change_timezone_start(callback: CallbackQuery, state: FSMContext):
    """Начинаем процесс смены часового пояса"""
    await callback.message.edit_text(
        "⏰ Напиши текущее местное время (как на телефоне) в формате HH:MM\n"
        "Пример: 21:15\n\n"
        "Я подстрою напоминания под твой часовой пояс.",
        reply_markup=back_to_settings_keyboard()
    )
    await state.set_state(TimezoneStates.waiting_for_time)
    await callback.answer()

@router.message(TimezoneStates.waiting_for_time)
async def process_time_input(message: Message, state: FSMContext):
    """Обрабатывает введённое время"""
    # Вычисляем сдвиг
    offset = calculate_offset_from_time(message.text)
    
    if offset is None:
        await message.answer(
            "❌ Неправильный формат. Введи время как ЧЧ:ММ\n"
            "Например: 21:15"
        )
        return
    
    # Сохраняем
    await save_user_offset(message.from_user.id, offset)
    
    offset_str = format_offset(offset)
    
    await message.answer(
        f"✅ Готово. Теперь твой часовой пояс: {offset_str}\n"
        f"Напоминания будут приходить по твоему местному времени."
    )
    
    # Возвращаемся в меню настроек
    await show_settings(message)
    await state.clear()

@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню настроек"""
    await state.clear()
    await show_settings(callback.message)
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=patient_main_menu()
    )
    await callback.answer()