from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
import os
import asyncio
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
import requests
from main import Weather, Location
from aiogram.enums.parse_mode import ParseMode
from dotenv import load_dotenv
from pathlib import Path
import keyboard
from queue import Queue
from threading import Thread
import threading
from bots_app import app, start_dash_app
import time
import json

env_path = Path("venv") / ".env"
load_dotenv(dotenv_path=env_path)

ACCUWEATHER_API_KEY = os.getenv('ACCUWEATHER_API_KEY')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
TG_TOKEN = os.getenv('TG_TOKEN')

bot = Bot(token=TG_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
location = Location(accuweather_api_key=ACCUWEATHER_API_KEY, yandex_api_key=YANDEX_API_KEY)
weather = Weather(accuweather_api_key=ACCUWEATHER_API_KEY)

data_queue = Queue()

weather_data_app = None
forecast_days_app = 1
cities_coordinates_app = []

class WeatherState(StatesGroup):
    start = State()
    end = State()
    days = State()

class WeatherMultipleLocationsState(StatesGroup):
    cities = State()
    days = State()


def save_forecast_to_json(city_coordinates, weather_data, forecast_days, filename="weather_forecast.json"):
    data = {
        "city_coordinates": city_coordinates,
        "weather": weather_data,
        "forecast_days": forecast_days
    }

    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Данные успешно сохранены в файл {filename}")
    except Exception as e:
        print(f"Ошибка при сохранении данных в файл: {e}")

def run_dash_app():
    try:
        start_dash_app()  # Запускаем Dash приложение
    except Exception as e:
        print(f"Ошибка при запуске Dash приложения: {str(e)}")

# Команда /start
@router.message(Command(commands=["start"]))
async def send_welcome(message: types.Message):
    await message.answer(
        "Привет! Я бот для погоды. Отправьте /help, чтобы узнать, чем я могу Вам помочь.",
        reply_markup=keyboard.start_kb
    )

# Обработка нажатия на кнопку "Прогноз для 2 точек"
@router.message(F.text == "Прогноз для 2 точек")
async def send_weather_command(message: types.Message, state: FSMContext):
    await message.answer("Введите начальную точку маршрута:")
    await state.set_state(WeatherState.start)

# Обработка нажатия на кнопку "Прогноз для нескольких точек"
@router.message(F.text == "Прогноз для нескольких точек")
async def send_weather_multiple_locations_command(message: types.Message, state: FSMContext):
    await message.answer("Введите город, для которого хотите получить прогноз:")
    await state.set_state(WeatherMultipleLocationsState.cities)

# Обработка ввода города
@router.message(WeatherMultipleLocationsState.cities)
async def process_multiple_cities(message: types.Message, state: FSMContext):
    # Получаем данные из состояния, если они есть
    data = await state.get_data()
    cities = data.get("cities", [])

    cities.append(message.text.strip())

    await state.update_data(cities=cities)

    await message.answer(f"Города для прогноза: {', '.join(cities)}", reply_markup=keyboard.weather_multiple_locations_kb)

# Обработка нажатия на кнопку "Добавить город"
@router.callback_query(F.data == "add_city", WeatherMultipleLocationsState.cities)
async def add_city(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer("Введите следующий город:")

# Обработка нажатия на кнопку "Убрать город"
@router.callback_query(F.data == "remove_city", WeatherMultipleLocationsState.cities)
async def remove_city(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    data = await state.get_data()
    cities = data.get("cities", [])

    if not cities:
        await callback_query.message.answer("Список городов пуст.")
        return

    removed_city = cities.pop()

    await state.update_data(cities=cities)

    if cities:
        city_list = ', '.join(cities)
    else:
        city_list = "Список городов пуст."

    await callback_query.message.answer(f"Города для прогноза: {city_list}", reply_markup=keyboard.weather_multiple_locations_kb)

# Обработка нажатия на кнопку "Получить прогноз"
@router.callback_query(F.data == "get_forecast", WeatherMultipleLocationsState.cities)
async def get_weather_for_multiple_cities(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    data = await state.get_data()
    cities = data.get("cities", [])

    if not cities:
        await callback_query.message.answer("Список городов пуст. Пожалуйста, добавьте хотя бы один город.")
        return


    await callback_query.message.answer("На сколько дней предоставить прогноз?", reply_markup=keyboard.days_kb)
    await state.set_state(WeatherMultipleLocationsState.days)

@router.callback_query(F.data.isdigit(), WeatherMultipleLocationsState.days)
async def process_number_of_days(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.delete()
    await callback_query.message.answer("Подготавливаем прогноз, пожалуйста, ожидайте...")

    days = int(callback_query.data)
    data = await state.get_data()
    cities = data.get("cities", [])

    forecast_text = "<pre>Прогноз погоды для следующих городов на {days} дней:\n\n".format(days=days)
    forecast_text += "Город        | Дата       | Мин. Темп. (°C) | Макс. Темп. (°C) | Ветер (км/ч) | Осадки (%) | Описание\n"
    forecast_text += "----------------------------------------------------------------------\n"

    cities_coordinates = []
    weather_data = {}

    for city in cities:
        lat, lon = location.get_coordinates(city)
        location_key = location.get_location_key(lat, lon)

        if not location_key:
            forecast_text += f"{city: <12} | Не удалось получить данные\n"
            continue

        forecast_data = weather.get_forecast_data(location_key, days)
        # print('-------CITY--------')
        # print(city, '---', type(city))
        weather_data[city] = {
            "forecast": forecast_data,
            "latitude": lat,
            "longitude": lon,
        }
        cities_coordinates.append({"city": city, "lat": lat, "lon": lon})

        if not forecast_data:
            forecast_text += f"{city: <12} | Не удалось получить прогноз\n"
            continue

        for day in forecast_data["DailyForecasts"][:days]:
            date = day["Date"][:10]
            min_temp = day["Temperature"]["Minimum"]["Value"]
            max_temp = day["Temperature"]["Maximum"]["Value"]
            description = day["Day"]["IconPhrase"]
            wind_speed = day["Day"]["Wind"]["Speed"]["Value"]
            precipitation_prob = day["Day"]["PrecipitationProbability"]

            forecast_text += f"{city: <12} | {date} | {min_temp: <14} | {max_temp: <14} | {wind_speed: <12} | {precipitation_prob: <10} | {description: <8}\n"

    forecast_text += "</pre>"

    save_forecast_to_json(cities_coordinates, weather_data, days)
    time.sleep(1)
    dash_thread = threading.Thread(target=run_dash_app)
    dash_thread.daemon = True  # Поток завершится, когда завершится основной процесс
    dash_thread.start()  # Запускаем поток с Dash приложением

    # await callback_query.message.answer(
    #     "🌤️ <b>Прогноз погоды на несколько дней</b> доступен в интерактивной панели, "
    #     "где вы можете просматривать данные в виде графиков, таблиц и карты! 📊🗺️\n\n"
    #     "👉 Для получения подробного прогноза погоды для выбранных городов, пожалуйста, "
    #     'перейдите по <a href="http://localhost:8050"><b>этой ссылке</b></a>.',
    #     parse_mode=ParseMode.HTML
    # )
    text = f"Для получения подробного и интерактивного прогноза погоды для выбранных городов, пожалуйста, перейдите по этой <a href='http://127.0.0.1:8050/'>ссылке</a>."
    await callback_query.message.answer(text, parse_mode=ParseMode.HTML)
    await callback_query.message.answer(forecast_text, parse_mode=ParseMode.HTML)
    await state.clear()




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

    await message.answer(
        "На сколько дней предоставить прогноз?", reply_markup=keyboard.days_kb
    )
    await state.set_state(WeatherState.days)


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
    forecast_text += "Дата       | Мин. Темп. (°C) | Макс. Темп. (°C) | Ветер (км/ч) | Осадки (%) | Описание\n"
    forecast_text += "--------------------------------------------------------------------------\n"

    forecast_text += f"\nПрогноз для города {start_city}:\n"
    for day in start_forecast["DailyForecasts"][:days]:
        date = day["Date"][:10]
        min_temp = day["Temperature"]["Minimum"]["Value"]
        max_temp = day["Temperature"]["Maximum"]["Value"]
        description = day["Day"]["IconPhrase"]
        wind_speed = day["Day"]["Wind"]["Speed"]["Value"]  # Получаем скорость ветра
        precipitation_prob = day["Day"]["PrecipitationProbability"]

        forecast_text += f"{date: <10} | {min_temp: <14} | {max_temp: <14} | {wind_speed: <12} | {precipitation_prob: <10} | {description: <8}\n"

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