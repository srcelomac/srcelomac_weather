# Веб-сервис с прогнозом погоды для заданного маршрута

## Описание проекта

Погодные условия могут поменять план путешествия в любой момент. Планировать поездки проще, если заранее знать, что где-то в пути погода испортится: пойдёт дождь или неожиданно похолодает. Ты можешь спроектировать свой веб-сервис, который будет учитывать погоду на маршруте, и использовать его в путешествиях!

Этот веб-сервис предсказывает вероятность плохой погоды для заданного маршрута. Сервис предоставляет пользователю удобные визуализации и прогнозы погоды.

Сервис использует:
- **AccuWeather API** для получения данных о погоде.
- **Yandex Geosearch API** для определения координат городов.

## Основные возможности

- Отображение текущей погоды: температура, влажность, скорость ветра.
- Прогноз на один день с указанием вероятности осадков.
- Оценка неблагоприятных погодных условий (например, экстремальные температуры, сильный ветер или высокий шанс осадков).
- Информирование о том, безопасно ли путешествовать.

## Ошибки
Если возникнут проблемы с подключением к API или некорректные данные, отображается соответствущая страница ошибки `Error.html`. В консоле будут указаны описания ошибок и полный их путь.

Если будет достигнут лимит запросов к API, отображается соотвествующая страница ошибки `ErrorAPI.html`.

---

## Установка и запуск

### Требования

- Python 3.8+
- Установленные библиотеки из файла `requirements.txt`
- Настроенные API-ключи:
  - **AccuWeather API Key**
  - **Yandex Geocoder API Key**

### Установка и запуск

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/srcelomac/srcelomac_weather
   cd srcelomac_weather
2. Записать свои API-ключи в соотвествующие переменные
3. Запустить файл `app.py`