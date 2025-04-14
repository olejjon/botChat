from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from database.crud import Database
from config import Config
from utils.keyboards import get_main_keyboard
import logging


router = Router()
db = Database("support_bot.db")


class RegistrationStates(StatesGroup):
    first_name = State()
    last_name = State()
    company = State()
    market = State()
    phone = State()
    confirm = State()


@router.message(Command("renew"))
async def cmd_renew(message: types.Message, state: FSMContext):
    """Начало процесса регистрации/обновления данных"""
    await message.answer("Введите ваше имя:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(RegistrationStates.first_name)


@router.message(RegistrationStates.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    """Обработка имени"""
    await state.update_data(first_name=message.text)
    await message.answer("Введите вашу фамилию:")
    await state.set_state(RegistrationStates.last_name)


@router.message(RegistrationStates.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    """Обработка фамилии"""
    await state.update_data(last_name=message.text)
    await message.answer("Введите название вашей компании:")
    await state.set_state(RegistrationStates.company)


@router.message(RegistrationStates.company)
async def process_company(message: types.Message, state: FSMContext):
    """Обработка названия компании"""
    await state.update_data(company=message.text)
    await message.answer("Введите ваш магазин/маркет:")
    await state.set_state(RegistrationStates.market)


@router.message(RegistrationStates.market)
async def process_market(message: types.Message, state: FSMContext):
    """Обработка магазина/маркета"""
    await state.update_data(market=message.text)
    await message.answer("Введите ваш телефон для связи:")
    await state.set_state(RegistrationStates.phone)


@router.message(RegistrationStates.phone)
async def process_phone(message: types.Message, state: FSMContext):
    """Обработка телефона и подтверждение данных"""
    await state.update_data(phone=message.text)
    data = await state.get_data()

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Да"))
    builder.add(KeyboardButton(text="Нет"))

    await message.answer(
        f"Проверьте ваши данные:\n\n"
        f"Имя: {data['first_name']}\n"
        f"Фамилия: {data['last_name']}\n"
        f"Компания: {data['company']}\n"
        f"Магазин: {data['market']}\n"
        f"Телефон: {data['phone']}\n\n"
        f"Все верно?",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )
    await state.set_state(RegistrationStates.confirm)


@router.message(RegistrationStates.confirm)
async def process_confirmation(message: types.Message, state: FSMContext):
    """Обработка подтверждения данных"""
    if message.text.lower() == "да":
        data = await state.get_data()

        db.cursor.execute(
            "INSERT OR REPLACE INTO users "
            "(user_id, first_name, last_name, company, phone, market) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                message.from_user.id,
                data["first_name"],
                data["last_name"],
                data["company"],
                data["phone"],
                data["market"],
            ),
        )
        db.conn.commit()

        admin_message = (
            f"Новый пользователь:\n"
            f"Имя: {data['first_name']} {data['last_name']}\n"
            f"Компания: {data['company']}\n"
            f"Магазин: {data['market']}\n"
            f"Телефон: {data['phone']}\n\n"
            f"Подтвердить: http://172.23.23.0/admin/confirm?user_id={message.from_user.id}"
        )

        try:
            await message.bot.send_message(
                chat_id=Config.DUTY_CHANNEL, text=admin_message
            )
        except Exception as e:
            logging.error(f"Ошибка отправки в канал дежурства: {e}")

        await message.answer(
            "Регистрация завершена! Теперь вы можете создать обращение.",
            reply_markup=get_main_keyboard(),
        )
    else:
        await message.answer(
            "Давайте начнем регистрацию заново. Введите ваше имя:",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.set_state(RegistrationStates.first_name)

    await state.clear()
