from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from database.crud import Database
from config import Config
import logging

router = Router()
db = Database("support_bot.db")


async def verify_admin(message: Message) -> bool:
    """Проверяет и синхронизирует права администратора"""
    user_id = message.from_user.id

    # Проверяем наличие в списке ADMINS из .env
    if user_id in Config().ADMINS:
        # Если есть в .env, но нет в БД - добавляем
        if not db.is_admin(user_id):
            db.add_admin(user_id)
            logging.info(f"Обновлены права админа для {user_id}")
        return True

    # Проверяем наличие прав в БД
    return db.is_admin(user_id)


async def change_status(message: Message, ticket_id: int, new_status: str, bot: Bot):
    """Общая функция изменения статуса с проверкой прав"""
    if not db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав для изменения статуса")
        return

    try:
        if not db.ticket_exists(ticket_id):
            await message.reply(f"❌ Заявка #{ticket_id} не найдена")
            return

        old_status = db.get_ticket_details(ticket_id)["status"]
        db.update_ticket_status(ticket_id, new_status, bot)

        status_names = {
            "open": "открыта",
            "in_progress": "в работе",
            "resolved": "решена",
            "closed": "закрыта",
        }
        await message.reply(
            f"✅ Заявка #{ticket_id} помечена как {status_names[new_status]}"
        )
    except Exception as e:
        logging.error(f"Ошибка изменения статуса: {e}")
        await message.reply("⚠️ Не удалось изменить статус")


@router.message(Command("ticket"))
async def handle_ticket_command(message: Message):
    """Просмотр информации о заявке"""
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply("ℹ️ Используйте: /ticket [номер_заявки]")
            return

        ticket_id = int(args[1])
        ticket = db.get_ticket_details(ticket_id)

        if not ticket:
            await message.reply(f"❌ Заявка #{ticket_id} не найдена")
            return

        user = db.get_user(ticket["user_id"])
        status_map = {
            "open": "🟡 Открыта",
            "in_progress": "🟠 В работе",
            "resolved": "🟢 Решена",
            "closed": "🔴 Закрыта",
        }

        response = (
            f"📌 Заявка #{ticket_id}\n"
            f"👤 Пользователь: {user['first_name']} {user['last_name']}\n"
            f"🔄 Статус: {status_map.get(ticket['status'], ticket['status'])}\n"
            f"📅 Создана: {ticket['created_at']}\n"
        )

        if db.is_admin(message.from_user.id):
            response += "\n⚙️ Команды:\n"
            response += f"/open_{ticket_id}\n/progress_{ticket_id}\n"
            response += f"/resolve_{ticket_id}\n/close_{ticket_id}"

        await message.reply(response)
    except Exception as e:
        await message.reply(f"⚠️ Ошибка: {str(e)}")


# Обработчики команд изменения статуса
@router.message(F.text.startswith("/open_"))
async def set_open_status(message: Message, bot: Bot):
    try:
        ticket_id = int(message.text.split("_")[1])
        await change_status(message, ticket_id, "open", bot)
    except (IndexError, ValueError):
        pass


@router.message(F.text.startswith("/progress_"))
async def set_progress_status(message: Message, bot: Bot):
    try:
        ticket_id = int(message.text.split("_")[1])
        await change_status(message, ticket_id, "in_progress", bot)
    except (IndexError, ValueError):
        pass


@router.message(F.text.startswith("/resolve_"))
async def set_resolved_status(message: Message, bot: Bot):
    try:
        ticket_id = int(message.text.split("_")[1])
        await change_status(message, ticket_id, "resolved", bot)
    except (IndexError, ValueError):
        pass


@router.message(F.text.startswith("/close_"))
async def set_closed_status(message: Message, bot: Bot):
    try:
        ticket_id = int(message.text.split("_")[1])
        await change_status(message, ticket_id, "closed", bot)
    except (IndexError, ValueError):
        pass


@router.message(Command("add_admin"))
async def add_admin_command(message: Message):
    """Добавление нового администратора (только для существующих админов)"""
    if not db.is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав на эту операцию")
        return

    try:
        new_admin_id = int(message.text.split()[1])
        db.add_admin(new_admin_id)
        await message.reply(f"✅ Пользователь {new_admin_id} добавлен в админы")
    except Exception as e:
        await message.reply(f"⚠️ Ошибка: {str(e)}")
