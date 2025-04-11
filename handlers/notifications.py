from aiogram import Bot
from database.crud import Database
import logging

db = Database("support_bot.db")


async def notify_status_change(
    bot: Bot, ticket_id: int, old_status: str, new_status: str
):
    try:
        user_id = db.get_user_by_ticket(ticket_id)
        if not user_id:
            return

        status_map = {
            "open": "🟡 Открыта",
            "in_progress": "🟠 В работе",
            "resolved": "🟢 Решена",
            "closed": "🔴 Закрыта",
        }

        await bot.send_message(
            chat_id=user_id,
            text=f"📢 Статус заявки #{ticket_id} изменен:\n"
            f"{status_map.get(old_status, old_status)} → "
            f"{status_map.get(new_status, new_status)}\n\n"
            f"Проверить: /status",
        )
    except Exception as e:
        logging.error(f"Ошибка уведомления: {e}")
