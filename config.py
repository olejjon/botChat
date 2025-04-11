import logging
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self._sync_admins()

    def _sync_admins(self):
        """Синхронизирует админов при запуске"""
        from database.crud import Database

        db = Database("support_bot.db")
        db.sync_admins(self.ADMINS)
        logging.info(f"Синхронизированы админы: {self.ADMINS}")

    @property
    def ADMINS(self):
        admins = os.getenv("ADMINS", "").split(",")
        return list(map(int, filter(None, admins)))

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL")
    DUTY_CHANNEL = os.getenv("DUTY_CHANNEL")
    PHOTOS_DIR = "photos"

    # Создаем папку для фото
    os.makedirs(PHOTOS_DIR, exist_ok=True)
