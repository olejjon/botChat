from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardRemove, FSInputFile, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder


from database.crud import Database
from config import Config
from handlers.status import CommentStates, process_photo_comment
from utils.files import save_photo
from utils.keyboards import get_main_keyboard
import logging

router = Router()
db = Database("support_bot.db")


class NewTicketStates(StatesGroup):
    waiting_for_description = State()
    waiting_for_photo = State()


@router.message(F.text == "📝 Новая заявка")
async def handle_new_ticket_button(message: types.Message, state: FSMContext):
    """Обработчик кнопки 'Новая заявка'"""
    await cmd_new(message, state)


@router.message(Command("new"))
async def cmd_new(message: types.Message, state: FSMContext):
    """Начало создания новой заявки"""
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return

    # Добавляем кнопку "Отмена" рядом с текстовым запросом
    cancel_button = KeyboardButton(text="❌ Отмена")
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[cancel_button]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "Опишите вашу проблему или вопрос:", reply_markup = keyboard
    )
    await state.set_state(NewTicketStates.waiting_for_description)


@router.message(NewTicketStates.waiting_for_description)
async def process_ticket_description(message: types.Message, state: FSMContext):
    """Обработка описания проблемы"""
    if message.photo:
        await message.answer("Пожалуйста, сначала опишите проблему текстом.")
        return

    await state.update_data(description=message.text)

    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Пропустить"))
    builder.add(KeyboardButton(text="❌ Отмена"))
    await message.answer(
        "Хотите прикрепить фото к заявке? Отправьте фото или нажмите 'Пропустить'",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )
    await state.set_state(NewTicketStates.waiting_for_photo)


@router.message(NewTicketStates.waiting_for_photo, F.photo)
async def process_ticket_photo(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = message.from_user.id
    description = data["description"]
    photo = message.photo[-1]

    ticket_id = db.create_ticket(user_id)

    try:
        photo_path = await save_photo(bot, photo, ticket_id)
        db.add_photo_to_ticket(ticket_id, photo_path)

        user = db.get_user(user_id)

        support_message = (
            f"Новая задача #{ticket_id}\n"
            f"От: {user['first_name']} {user['last_name']}\n"
            f"Компания: {user['company']}\n"
            f"Магазин: {user['market']}\n\n"
            f"Описание: {description}"
        )

        await bot.send_photo(
            chat_id=Config.SUPPORT_CHANNEL,
            photo=FSInputFile(photo_path),
            caption=support_message,
        )

        await message.answer(
            f"✅ Задача #{ticket_id} создана!\nПроверить статус: /status",
            reply_markup=get_main_keyboard(),
        )
    except Exception as e:
        logging.error(f"Ошибка создания заявки: {e}")
        await message.answer(
            "⚠️ Не удалось создать заявку. Попробуйте позже.",
            reply_markup=get_main_keyboard(),
        )
    finally:
        await state.clear()


@router.message(NewTicketStates.waiting_for_photo, F.text == "Пропустить")
async def skip_photo_attachment(message: types.Message, state: FSMContext, bot: Bot):
    """Пропуск прикрепления фото"""
    data = await state.get_data()
    user_id = message.from_user.id
    description = data["description"]

    ticket_id = db.create_ticket(user_id)
    db.add_message_to_ticket(ticket_id, user_id, description)

    user = db.get_user(user_id)

    support_message = (
        f"Новая задача #{ticket_id}\n"
        f"От: {user['first_name']} {user['last_name']}\n"
        f"Компания: {user['company']}\n"
        f"Магазин: {user['market']}\n\n"
        f"Описание: {description}"
    )

    await bot.send_message(chat_id=Config.SUPPORT_CHANNEL, text=support_message)

    await message.answer(
        f"✅ Задача #{ticket_id} создана!\nПроверить статус: /status",
        reply_markup=get_main_keyboard(),
    )
    await state.clear()


@router.message(F.photo)
async def handle_photo_message(message: types.Message, bot: Bot, state: FSMContext):
    """Обработчик фото - определяет контекст (новая заявка или комментарий)"""
    current_state = await state.get_state()

    if current_state == CommentStates.waiting_for_comment:
        await process_photo_comment(message, state, bot)
        return

    if current_state == NewTicketStates.waiting_for_photo:
        await process_ticket_photo(message, state, bot)
        return

    user_id = message.from_user.id
    active_ticket = db.get_active_ticket(user_id)

    if active_ticket:
        await process_photo_comment(message, state, bot)
    else:
        await message.answer("⚠️ Сначала создайте заявку командой /new")


@router.message(NewTicketStates.waiting_for_description, F.text == "❌ Отмена")
async def cancel_ticket_creation(message: types.Message, state: FSMContext):
    """Обработка отмены создания заявки"""
    await message.answer(
        "Создание заявки отменено.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()


@router.message(NewTicketStates.waiting_for_photo, F.text == "❌ Отмена")
async def cancel_photo_attachment(message: types.Message, state: FSMContext):
    """Отмена прикрепления фото (и всей заявки)"""
    await message.answer(
        "Создание заявки отменено.",
        reply_markup=get_main_keyboard()
    )
    await state.clear()