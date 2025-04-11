import time

from aiogram import types, Bot
import os


async def save_photo(bot: Bot, photo: types.PhotoSize, prefix: str):
    """Сохраняет фото на диск и возвращает путь"""
    os.makedirs("photos", exist_ok=True)
    file = await bot.get_file(photo.file_id)
    ext = os.path.splitext(file.file_path)[1] or ".jpg"
    filename = f"{prefix}_{int(time.time())}{ext}"
    full_path = os.path.join("photos", filename)
    await bot.download_file(file.file_path, full_path)
    return full_path
