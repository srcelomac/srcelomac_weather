from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
import os
import asyncio
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
import requests
from config import TG_TOKEN, ACCUWEATHER_API_KEY, YANDEX_API_KEY
from main import Weather, Location
from aiogram.enums.parse_mode import ParseMode

bot = Bot(token=TG_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
location = Location(accuweather_api_key=ACCUWEATHER_API_KEY, yandex_api_key=YANDEX_API_KEY)
weather = Weather(accuweather_api_key=ACCUWEATHER_API_KEY)


class WeatherState(StatesGroup):
    start = State()
    end = State()
    days = State()


# Команда /start
@router.message(Command(commands=["start"]))
async def send_welcome(message: types.Message):
    await message.answer(
        "Привет! Я бот для погоды. Отправьте /help, чтобы узнать, чем я могу Вам помочь."
    )


# Команда /help
@router.message(Command(commands=["help"]))
async def send_help(message: types.Message):
    await message.answer(
        "Я могу предоставить прогноз погоды для вашего маршрута.\n"
        "Если хочешь узнать прогноз, то используй команду /weather.\n"
        "Список доступных команд:\n"
        "/start - Приветственное сообщение\n"
        "/help - Список команд\n"
        "/weather - Запрос прогноза погоды"
    )


# Команда /weather
@router.message(Command(commands=["weather"]))
async def get_weather_route(message: types.Message, state: FSMContext):
    await message.answer("Введите начальную точку маршрута:")
    await state.set_state(WeatherState.start)


@router.message(WeatherState.start)
async def process_start_point(message: types.Message, state: FSMContext):
    await state.update_data(start=message.text)
    await message.answer("Введите конечную точку маршрута:")
    await state.set_state(WeatherState.end)


@router.message(WeatherState.end)
async def process_end_point(message: types.Message, state: FSMContext):
    await state.update_data(end=message.text)

    days_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 день", callback_data="1")],
            [InlineKeyboardButton(text="2 дня", callback_data="2")],
            [InlineKeyboardButton(text="3 дня", callback_data="3")],
            [InlineKeyboardButton(text="4 дня", callback_data="4")],
            [InlineKeyboardButton(text="5 дней", callback_data="5")],
        ]
    )
    await message.answer(
        "На сколько дней предоставить прогноз?", reply_markup=days_keyboard
    )
    await state.set_state(WeatherState.days)


# Обработка выбора временного интервала
@router.callback_query(F.data.isdigit(), WeatherState.days)
async def process_number_of_days(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.delete()
    await callback_query.message.answer(
        "Подготавливаем прогноз, пожалуйста ожидайте"
    )
    days = int(callback_query.data)

    data = await state.get_data()
    start_city = data["start"]
    end_city = data["end"]

    start_lat, start_lon = location.get_coordinates(start_city)
    start_key = location.get_location_key(start_lat, start_lon)

    end_lat, end_lon = location.get_coordinates(end_city)
    end_key = location.get_location_key(end_lat, end_lon)

    if not start_key:
        await callback_query.message.answer(
            "Не удалось начальный город. Пожалуйста, проверьте ввод и попробуйте снова."
        )
        await state.clear()
        return

    if not end_key:
        await callback_query.message.answer(
            "Не удалось конечный город. Пожалуйста, проверьте ввод и попробуйте снова."
        )
        await state.clear()
        return

    start_forecast = weather.get_forecast_data(start_key, days)
    end_forecast = weather.get_forecast_data(end_key, days)

    if not start_forecast:
        await callback_query.message.answer(
            "Не удалось получить прогноз погоды для начального города."
        )
        await state.clear()
        return

    if not end_forecast:
        await callback_query.message.answer(
            "Не удалось получить прогноз погоды для конечного города."
        )
        await state.clear()
        return

    forecast_text = f"<pre>Прогноз для маршрута {start_city} - {end_city} на {days} дней:\n\n"
    forecast_text += "Дата       | Мин. Темп. (°C) | Макс. Темп. (°C) | Описание | Ветер (км/ч) | Осадки (%)\n"
    forecast_text += "--------------------------------------------------------------------------\n"

    forecast_text += f"\nПрогноз для города {start_city}:\n"
    for day in start_forecast["DailyForecasts"][:days]:
        date = day["Date"][:10]
        min_temp = day["Temperature"]["Minimum"]["Value"]
        max_temp = day["Temperature"]["Maximum"]["Value"]
        description = day["Day"]["IconPhrase"]
        wind_speed = day["Day"]["Wind"]["Speed"]["Value"]  # Получаем скорость ветра
        precipitation_prob = day["Day"]["PrecipitationProbability"]

        forecast_text += f"{date: <10} | {min_temp: <14} | {max_temp: <14} | {description: <8} | {wind_speed: <12} | {precipitation_prob: <10}\n"

    forecast_text += "\n--------------------------------------------------------------------------\n"

    forecast_text += f"\nПрогноз для города {end_city}:\n"
    for day in end_forecast["DailyForecasts"][:days]:
        date = day["Date"][:10]
        min_temp = day["Temperature"]["Minimum"]["Value"]
        max_temp = day["Temperature"]["Maximum"]["Value"]
        description = day["Day"]["IconPhrase"]
        wind_speed = day["Day"]["Wind"]["Speed"]["Value"]
        precipitation_prob = day["Day"]["PrecipitationProbability"]

        forecast_text += f"{date: <10} | {min_temp: <14} | {max_temp: <14} | {wind_speed: <12} | {precipitation_prob: <10} | {description: <8}\n"

    forecast_text += "</pre>"

    await callback_query.message.answer(forecast_text, parse_mode=ParseMode.HTML)
    await state.clear()


async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())