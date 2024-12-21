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
import re

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

def is_coordinates(text: str) -> bool:
    pattern = r'^-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?$'
    return bool(re.match(pattern, text.strip()))

def run_dash_app():
    try:
        start_dash_app()
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
    if is_coordinates(message.text):
        # Генерация уникального названия для точки
        data = await state.get_data()
        cities = data.get("cities", [])
        coordinates = data.get("coordinates", [])

        point_name = f"Точка №{len(cities) + len(coordinates) + 1}"

        # Разделяем координаты
        start_lat, start_lon = map(float, message.text.split(","))

        # Добавляем точку и её координаты
        cities.append(point_name)
        coordinates.append((start_lat, start_lon))

        # Обновляем состояние
        await state.update_data(cities=cities, coordinates=coordinates)

        await message.answer(f"Города для прогноза: {', '.join(cities)}",
                             reply_markup=keyboard.weather_multiple_locations_kb)
    elif any(char.isdigit() for char in message.text):
        await message.answer(
            "Название города не может содержать цифры. Пожалуйста, введите правильное название города.")
        return
    else:
        # Добавление города в список
        data = await state.get_data()
        cities = data.get("cities", [])
        coordinates = data.get("coordinates", [])

        cities.append(message.text.strip())
        coordinates.append((None, None))

        # Обновляем состояние
        await state.update_data(cities=cities)
        await state.update_data(coordinates=coordinates)

        await message.answer(f"Города для прогноза: {', '.join(cities)}",
                             reply_markup=keyboard.weather_multiple_locations_kb)


# Обработка нажатия на кнопку "Убрать город"
@router.callback_query(F.data == "remove_city", WeatherMultipleLocationsState.cities)
async def remove_city(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    data = await state.get_data()
    cities = data.get("cities", [])
    coordinates = data.get("coordinates", [])
    print('-------------COORDINATES-------------')
    print(coordinates)

    if not cities:
        await callback_query.message.answer("Список городов пуст.")
        return

    removed_city = cities.pop()
    await state.update_data(cities=cities)

    removed_coordinates = coordinates.pop()
    await state.update_data(cities=coordinates)

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
    coordinates = data.get("coordinates", [])

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
    coordinates = data.get("coordinates", [])

    forecast_text = "<pre>Прогноз погоды для следующих городов на {days} дней:\n\n".format(days=days)
    forecast_text += "Дата       | Мин. Темп. (°C) | Макс. Темп. (°C) | Ветер (км/ч) | Осадки (%) | Описание\n"
    forecast_text += "----------------------------------------------------------------------\n"

    cities_coordinates = []
    weather_data = {}

    for city, (coord_lat, coord_lon) in zip(cities, coordinates):
        if coord_lat and coord_lon:
            lat, lon = coord_lat, coord_lon
        else:
            lat, lon = location.get_coordinates(city)

        try:
            location_key = location.get_location_key(lat, lon)
        except Exception as e:
            await callback_query.message.answer(str(e), parse_mode=ParseMode.HTML)
            await state.clear()
            return

        if not location_key:
            forecast_text += f"{city: <12} | Не удалось получить данные\n"
            continue

        try:
            forecast_data = weather.get_forecast_data(location_key, days)
        except Exception as e:
            await callback_query.message.answer(str(e), parse_mode=ParseMode.HTML)
            await state.clear()
            return


        # print('---------TEST---------')
        # print(('Ошибка' in str(forecast_data)))
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

        forecast_text += f"\nПрогноз для города {city}:\n"
        for day in forecast_data["DailyForecasts"][:days]:
            date = day["Date"][:10]
            min_temp = day["Temperature"]["Minimum"]["Value"]
            max_temp = day["Temperature"]["Maximum"]["Value"]
            description = day["Day"]["IconPhrase"]
            wind_speed = day["Day"]["Wind"]["Speed"]["Value"]
            precipitation_prob = day["Day"]["PrecipitationProbability"]

            forecast_text += f"{date} | {min_temp: <14} | {max_temp: <14} | {wind_speed: <12} | {precipitation_prob: <10} | {description: <8}\n"

    forecast_text += "</pre>"

    try:
        save_forecast_to_json(cities_coordinates, weather_data, days)
        #time.sleep(1)
        dash_thread = threading.Thread(target=run_dash_app)
        dash_thread.daemon = True
        dash_thread.start()
    except Exception as e:
        await callback_query.message.answer(f"Ошибка при запуске приложения: {str(e)}", parse_mode=ParseMode.HTML)
        await state.clear()
        return

    text = f"Для получения подробного и интерактивного прогноза погоды для выбранных городов, пожалуйста, перейдите по <a href='http://127.0.0.1:8050/'>ссылке</a>."
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
        "/weather - Запрос прогноза погоды (2 точки маршрута)"
    )


# Команда /weather
@router.message(Command(commands=["weather"]))
async def get_weather_route(message: types.Message, state: FSMContext):
    await message.answer("Введите начальную точку маршрута:")
    await state.set_state(WeatherState.start)


@router.message(WeatherState.start)
async def process_start_point(message: types.Message, state: FSMContext):
    if is_coordinates(message.text):
        start_lat, start_lon = map(float, message.text.split(","))
        await state.update_data(start='Начальная точка', start_lat=start_lat, start_lon=start_lon)
        await message.answer("Конечная точка маршрута (введите город или координаты):")
    elif any(char.isdigit() for char in message.text):
        await message.answer(
            "Название города не может содержать цифры. Пожалуйста, введите правильное название города.")
        return
    else:
        await state.update_data(start=message.text)
        await message.answer("Конечная точка маршрута (введите город или координаты):")

    await state.set_state(WeatherState.end)


@router.message(WeatherState.end)
async def process_end_point(message: types.Message, state: FSMContext):
    if is_coordinates(message.text):
        end_lat, end_lon = map(float, message.text.split(","))
        await state.update_data(end='Конечная точка', end_lat=end_lat, end_lon=end_lon)
        await message.answer("На сколько дней предоставить прогноз?", reply_markup=keyboard.days_kb)
    elif any(char.isdigit() for char in message.text):
        await message.answer(
            "Название города не может содержать цифры. Пожалуйста, введите правильное название города.")
        return
    else:
        await state.update_data(end=message.text)
        await message.answer("На сколько дней предоставить прогноз?", reply_markup=keyboard.days_kb)

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
    start_city = data.get("start")
    end_city = data.get("end")
    start_lat = data.get("start_lat")
    start_lon = data.get("start_lon")
    end_lat = data.get("end_lat")
    end_lon = data.get("end_lon")

    if start_lat and start_lon:
        pass
    else:
        start_lat, start_lon = location.get_coordinates(start_city)

    try:
        start_key = location.get_location_key(start_lat, start_lon)
    except Exception as e:
        await callback_query.message.answer(f"Стартовый город: {str(e)}", parse_mode=ParseMode.HTML)
        await state.clear()
        return


    if end_lat and end_lon:
        pass
    else:
        end_lat, end_lon = location.get_coordinates(end_city)

    try:
        end_key = location.get_location_key(end_lat, end_lon)
    except Exception as e:
        await callback_query.message.answer(f"Конечный город: {str(e)}", parse_mode=ParseMode.HTML)
        await state.clear()
        return

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

    try:
        start_forecast = weather.get_forecast_data(start_key, days)
    except Exception as e:
        await callback_query.message.answer(f"Стартовый город: {str(e)}", parse_mode=ParseMode.HTML)
        await state.clear()
        return
    try:
        end_forecast = weather.get_forecast_data(end_key, days)
    except Exception as e:
        await callback_query.message.answer(f"Конечный город: {str(e)}", parse_mode=ParseMode.HTML)
        await state.clear()
        return

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

    cities_coordinates = []
    weather_data = {}

    weather_data[start_city] = {
        "forecast": start_forecast,
        "latitude": start_lat,
        "longitude": start_lon,
    }
    cities_coordinates.append({"city": start_city, "lat": start_lat, "lon": start_lon})

    weather_data[end_city] = {
        "forecast": end_forecast,
        "latitude": end_lat,
        "longitude": end_lon,
    }
    cities_coordinates.append({"city": end_city, "lat": end_lat, "lon": end_lon})

    try:
        save_forecast_to_json(cities_coordinates, weather_data, days)
        #time.sleep(1)
        dash_thread = threading.Thread(target=run_dash_app)
        dash_thread.daemon = True
        dash_thread.start()
    except Exception as e:
        await callback_query.message.answer(f"Ошибка при запуске приложения: {str(e)}", parse_mode=ParseMode.HTML)
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
        wind_speed = day["Day"]["Wind"]["Speed"]["Value"]
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

    text = f"Для получения подробного и интерактивного прогноза погоды для выбранных городов, пожалуйста, перейдите по <a href='http://127.0.0.1:8050/'>ссылке</a>."
    await callback_query.message.answer(text, parse_mode=ParseMode.HTML)
    await callback_query.message.answer(forecast_text, parse_mode=ParseMode.HTML)
    await state.clear()


async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())