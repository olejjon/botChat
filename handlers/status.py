import asyncio

from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InputMediaPhoto, FSInputFile, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.crud import Database
from config import Config
from utils.files import save_photo
from datetime import datetime
import os
import logging

from utils.keyboards import get_main_keyboard

router = Router()
db = Database("support_bot.db")


class CommentStates(StatesGroup):
    waiting_for_comment = State()


@router.message(F.text == "📋 Мои заявки")
async def handle_my_tickets_button(message: types.Message):
    """Обработчик кнопки 'Мои заявки'"""
    await cmd_status(message)


def format_status(status):
    status_map = {
        "open": "🟡 Открыта",
        "in_progress": "🟠 В работе",
        "resolved": "🟢 Решена",
        "closed": "🔴 Закрыта",
    }
    return status_map.get(status, status)


@router.message(Command("status"))
async def cmd_status(message: types.Message):
    user_id = message.from_user.id
    tickets = db.get_user_tickets(user_id)

    if not tickets:
        await message.answer(
            "У вас пока нет задач. Создайте первую с помощью /new",
            reply_markup=get_main_keyboard(),
        )
        return

    kb = InlineKeyboardBuilder()
    keybord(tickets, kb)

    await message.answer(
        "📋 Ваши задачи. Выберите для просмотра:", reply_markup=kb.as_markup()
    )


async def show_ticket_details(bot: Bot, chat_id: int, message_id: int, ticket_id: int):
    """Показывает детали заявки с фотографиями"""
    try:
        ticket = db.get_ticket_details(ticket_id)
        if not ticket:
            return False

        messages = db.get_ticket_messages(ticket_id)
        photos = db.get_ticket_photos(ticket_id)

        created_at = datetime.strptime(ticket["created_at"], "%Y-%m-%d %H:%M:%S")
        text = (
            f"🔍 <b>Задача #{ticket['ticket_id']}</b>\n"
            f"📌 Статус: {format_status(ticket['status'])}\n"
            f"📅 Создана: {created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"<b>Сообщения:</b>\n"
        )

        for msg in messages:
            if msg["text"]:
                text += f"• {msg['text']}\n"

        if photos:
            try:
                try:
                    await bot.delete_message(chat_id, message_id)
                except:
                    pass

                media = []
                first_photo = True

                for photo in photos:
                    photo_path = photo["file_path"]
                    if os.path.exists(photo_path):
                        if first_photo:
                            # Первое фото с текстом заявки
                            media.append(
                                InputMediaPhoto(
                                    media=FSInputFile(photo_path),
                                    caption=text,
                                    parse_mode="HTML",
                                )
                            )
                            first_photo = False
                        else:
                            media.append(InputMediaPhoto(media=FSInputFile(photo_path)))

                if media:
                    await bot.send_media_group(chat_id=chat_id, media=media)

                    kb = InlineKeyboardBuilder()
                    kb.button(
                        text="📝 Добавить комментарий",
                        callback_data=f"add_comment_{ticket_id}",
                    )
                    kb.button(text="⬅️ Назад к списку", callback_data="back_to_list")
                    kb.button(text="🏠 На главную", callback_data="back_to_main")
                    kb.adjust(2, 1)

                    await bot.send_message(
                        chat_id=chat_id,
                        text="Действия с заявкой:",
                        reply_markup=kb.as_markup(),
                    )
                    return True

            except Exception as e:
                logging.error(f"Ошибка отправки медиагруппы: {e}")

        kb = InlineKeyboardBuilder()
        kb.button(
            text="📝 Добавить комментарий", callback_data=f"add_comment_{ticket_id}"
        )
        kb.button(text="⬅️ Назад к списку", callback_data="back_to_list")
        kb.button(text="🏠 На главную", callback_data="back_to_main")
        kb.adjust(2, 1)

        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=kb.as_markup(),
                parse_mode="HTML",
            )
        except:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=kb.as_markup(),
                parse_mode="HTML",
            )

        return True

    except Exception as e:
        logging.error(f"Ошибка показа заявки: {e}")
        return False


@router.callback_query(F.data.startswith("view_"))
async def view_ticket_details(callback: types.CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split("_")[1])
    await callback.answer()
    await show_ticket_details(
        bot=bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        ticket_id=ticket_id,
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    """Обработчик кнопки 'На главную'"""
    try:
        try:
            await callback.message.delete()
        except:
            pass

        await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard())

    except Exception as e:
        logging.error(f"Ошибка возврата на главную: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
    finally:
        await callback.answer()


@router.message(CommentStates.waiting_for_comment, F.text)
async def process_text_comment(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка текстового комментария с отправкой в чат поддержки"""
    data = await state.get_data()
    ticket_id = data.get("ticket_id")

    if not ticket_id:
        await message.answer("⚠️ Ошибка: не найдена заявка")
        await state.clear()
        return

    try:
        db.add_message_to_ticket(
            ticket_id=ticket_id, user_id=message.from_user.id, text=message.text
        )
        db.update_ticket_timestamp(ticket_id)

        await bot.send_message(
            chat_id=Config.SUPPORT_CHANNEL,
            text=f"Комментарий к задаче #{ticket_id}:\n{message.text}",
        )

        # 3. Удаляем сообщение с просьбой отправить комментарий
        await message.delete()

        confirm_msg = await message.answer(
            f"✅ Комментарий добавлен к заявке #{ticket_id}"
        )

        # 5. Обновляем просмотр заявки
        await show_ticket_details(
            bot=bot,
            chat_id=message.chat.id,
            message_id=confirm_msg.message_id,
            ticket_id=ticket_id,
        )

    except Exception as e:
        logging.error(f"Ошибка добавления комментария: {e}")
        await message.answer("⚠️ Не удалось добавить комментарий")
    finally:
        await state.clear()


@router.message(CommentStates.waiting_for_comment, F.photo)
async def process_photo_comment(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ticket_id = data.get("ticket_id")

    if not ticket_id:
        active_ticket = db.get_active_ticket(message.from_user.id)
        if active_ticket:
            ticket_id = active_ticket["ticket_id"]
            await state.update_data(ticket_id=ticket_id)
        else:
            await message.answer("⚠️ Нет активной заявки для добавления фото")
            await state.clear()
            return

    logging.info(f"Начало обработки фото для заявки #{ticket_id}")

    if not ticket_id:
        await message.answer("⚠️ Ошибка: не найдена заявка")
        await state.clear()
        return

    try:
        photo = message.photo[-1]
        photo_path = await save_photo(bot, photo, f"comment_{ticket_id}")

        ticket = db.get_ticket_details(ticket_id)
        user = db.get_user(message.from_user.id)

        if not ticket or not user:
            raise Exception("Не найдены данные заявки или пользователя")

        caption = message.caption or "Фото без описания"
        db.add_photo_to_ticket(ticket_id, photo_path)
        db.add_message_to_ticket(ticket_id, message.from_user.id, caption, photo_path)
        db.update_ticket_timestamp(ticket_id)

        support_text = (
            f"📸 Новое фото к задаче #{ticket_id}\n"
            f"От: {user['first_name']} {user['last_name']}\n"
            f"Компания: {user['company']}\n"
            f"Магазин: {user['market']}\n"
        )
        if caption != "Фото без описания":
            support_text += f"Комментарий: {caption}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                await bot.send_photo(
                    chat_id=Config.SUPPORT_CHANNEL,
                    photo=FSInputFile(photo_path),
                    caption=support_text,
                )
                logging.info(f"Фото отправлено в поддержку для заявки #{ticket_id}")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2)
                logging.warning(f"Попытка {attempt + 1} отправки фото: {e}")

        confirm_msg = await message.answer(f"✅ Фото добавлено к заявке #{ticket_id}")

        await show_ticket_details(
            bot=bot,
            chat_id=message.chat.id,
            message_id=confirm_msg.message_id,
            ticket_id=ticket_id,
        )

    except Exception as e:
        logging.error(f"Ошибка добавления фото: {str(e)}")
        await message.answer(f"⚠️ Ошибка: {str(e)}")
    finally:
        await state.clear()


@router.callback_query(F.data.startswith("add_comment_"))
async def add_comment_start(callback: types.CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.split("_")[2])
    await state.update_data(ticket_id=ticket_id)
    await state.set_state(CommentStates.waiting_for_comment)
    await callback.message.answer(
        "Отправьте ваш комментарий (текст или фото с подписью):",
        reply_markup=ReplyKeyboardRemove(),
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_list")
async def back_to_list_handler(callback: types.CallbackQuery):
    """Обработчик кнопки 'Назад к списку'"""
    try:
        await callback.message.delete()

        user_id = callback.from_user.id
        tickets = db.get_user_tickets(user_id)

        if not tickets:
            await callback.message.answer(
                "У вас пока нет задач. Создайте первую с помощью /new"
            )
            return

        kb = InlineKeyboardBuilder()
        keybord(tickets, kb)

        await callback.message.answer(
            "📋 Ваши задачи. Выберите для просмотра:", reply_markup=kb.as_markup()
        )

    except Exception as e:
        logging.error(f"Ошибка возврата к списку: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)
    finally:
        await callback.answer()


def keybord(tickets, kb):
    for ticket in tickets:
        created_at = datetime.strptime(ticket["created_at"], "%Y-%m-%d %H:%M:%S")
        kb.button(
            text=f"#{ticket['ticket_id']} - {created_at.strftime('%d.%m %H:%M')}",
            callback_data=f"view_{ticket['ticket_id']}",
        )
    kb.button(text="🏠 На главную", callback_data="back_to_main")
    kb.adjust(2, 1)