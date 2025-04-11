from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает основную клавиатуру меню"""
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(text="📝 Новая заявка"), KeyboardButton(text="📋 Мои заявки")
    )
    builder.row(
        KeyboardButton(text="🔄 Обновить свои данные"),
    )

    return builder.as_markup(resize_keyboard=True)
