import logging
from aiogram import Bot, Dispatcher
from config import Config
from database.crud import Database

# Импортируем роутеры
from handlers import common, registration, tickets, status, admin_commands

from config import Config

# Принудительно инициализируем синхронизацию
config = Config()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher()
db = Database("support_bot.db")
db.sync_admins(Config().ADMINS)


# Регистрируем роутеры
dp.include_router(common.router)
dp.include_router(registration.router)
dp.include_router(tickets.router)
dp.include_router(status.router)
dp.include_router(admin_commands.router)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
