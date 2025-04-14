from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from database.crud import Database

router = Router()
db = Database("support_bot.db")


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start с полной логикой"""
    user_id = message.from_user.id

    user = db.get_user(user_id)

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="/new - Новая заявка"))
    builder.add(KeyboardButton(text="/status - Мои заявки"))

    if user:
        builder.add(KeyboardButton(text="/renew - Обновить данные"))

        await message.answer(
            f"Добрый день, {user['first_name']}!\n"
            "Вы уже зарегистрированы в системе поддержки IT4Retail.",
            reply_markup=builder.as_markup(resize_keyboard=True),
        )

        await message.answer(
            "Вы можете:\n"
            "- Создать новую заявку (/new)\n"
            "- Проверить статус текущих заявок (/status)\n"
            "- Обновить свои данные (/renew)\n\n"
            "Что вас интересует?",
            reply_markup=builder.as_markup(resize_keyboard=True),
        )
    else:
        builder.add(KeyboardButton(text="/renew - Зарегистрироваться"))

        await message.answer(
            "Добро пожаловать в систему поддержки IT4Retail!",
            reply_markup=builder.as_markup(resize_keyboard=True),
        )

        await message.answer(
            "Для начала работы необходимо зарегистрироваться.\n\n"
            "Пожалуйста:\n"
            "1. Нажмите /renew для регистрации\n"
            "2. Следуйте инструкциям бота\n"
            "3. После регистрации вы сможете создавать заявки",
            reply_markup=builder.as_markup(resize_keyboard=True),
        )

    await state.clear()
