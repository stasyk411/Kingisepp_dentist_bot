from aiogram import Router, F
from aiogram.types import Message
from keyboards.patient_kb import patient_main_menu
from keyboards.admin_kb import admin_main_menu

router = Router()

@router.message(F.text == "/start")
async def cmd_start(message: Message, is_admin: bool):
    if is_admin:
        await message.answer("👩‍⚕️ Панель администратора\n\nВыберите действие в меню ниже:", reply_markup=admin_main_menu())
    else:
        await message.answer("👋 Добро пожаловать в бот записи к стоматологу!\n\nВыберите действие в меню ниже:", reply_markup=patient_main_menu())

@router.message(F.text == "❓ Контакты")
async def contacts(message: Message, is_admin: bool):
    kb = admin_main_menu() if is_admin else patient_main_menu()
    await message.answer(
        "👩‍⚕️ Врач: Голосовская Светлана Алексеевна\n"
        "📞 Телефон: +7 (911) 775-04-24\n"
        "📍 Адрес: Большая Советская улица, 8 (второй этаж)\n"
        "💰 Приём: платный",
        reply_markup=kb
    )

@router.message(F.text == "❓ Помощь")
async def help_cmd(message: Message, is_admin: bool):
    kb = admin_main_menu() if is_admin else patient_main_menu()
    await message.answer(
        "ℹ️ Как пользоваться ботом:\n\n"
        "1. Нажмите «Записаться»\n"
        "2. Выберите дату и время\n"
        "3. Подтвердите запись\n\n"
        "❌ Отменить можно за 24 часа до приёма\n\n"
        "👩‍⚕️ Врач: Голосовская Светлана Алексеевна\n"
        "📞 По вопросам: +7 (911) 775-04-24\n"
        "📍 Адрес: Большая Советская улица, 8 (второй этаж)",
        reply_markup=kb
    )

@router.message(F.text == "💳 Поддержать")
async def support(message: Message, is_admin: bool):
    kb = admin_main_menu() if is_admin else patient_main_menu()
    await message.answer(
        "💳 Номер телефона:+79052146265 \n\n"
        "Спасибо за поддержку! ❤️",
        reply_markup=kb
    )