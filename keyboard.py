from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

start_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Прогноз для 2 точек"),
            KeyboardButton(text="Прогноз для нескольких точек"),
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    selective=True
)

weather_multiple_locations_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➖ Убрать город", callback_data="remove_city")],  # Кнопка для удаления города
            [InlineKeyboardButton(text="✅ Получить прогноз", callback_data="get_forecast")]
        ]
)

days_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 день", callback_data="1")],
            [InlineKeyboardButton(text="2 дня", callback_data="2")],
            [InlineKeyboardButton(text="3 дня", callback_data="3")],
            [InlineKeyboardButton(text="4 дня", callback_data="4")],
            [InlineKeyboardButton(text="5 дней", callback_data="5")],
        ]
    )