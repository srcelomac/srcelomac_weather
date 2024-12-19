import os
import flask
import requests

accuweather_api_key = os.environ["ACCUWEATHER_API_KEY_8"]
yandex_api_key = os.environ["YANDEX_API_KEY"]

find_city = ''

class APIQuotaExceededError(Exception):
    pass

class Location:
    def __init__(self, accuweather_api_key, yandex_api_key):
        self.yandex_key = yandex_api_key
        self.accuweather_key = accuweather_api_key

    def request_to_yandex(self, city: str):
        try:
            params = {
                'apikey': self.yandex_key,
                'geocode': city,
                'lang': 'ru_RU',
                'format': 'json'
            }

            response = requests.get('https://geocode-maps.yandex.ru/1.x', params=params)

            if response.status_code != 200:
                print(f'Ошибка при получении данных. Код ошибки: {response.status_code}')
                return (f'Ошибка при получении данных. Код ошибки: {response.status_code}')

            return response.json()
        except Exception as e:
            raise Exception(f"Ошибка запроса к API Яндекса: {e}")


    def get_coordinates(self, city: str):
        global find_city
        data = self.request_to_yandex(city)
        if data:
            try:
                coords = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                find_city = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['name']
                lon, lat = coords.split(' ')
                lat = float(lat)
                # print(f"-------------lat------------")
                # print(f"------------{city}------------")
                # print(lat)
                lon = float(lon)
                # print(f"-------------lon------------")
                # print(f"------------{city}------------")
                # print(lon)
                return lat, lon
            except Exception as e:
                raise Exception(f"Ошибка получения координат: {e}")
        return None, None


    def get_location_key(self, lat, lon):
        try:
            params = {
                'apikey': self.accuweather_key,
                'q': f'{lat},{lon}'
            }
            response = requests.get('http://dataservice.accuweather.com/locations/v1/cities/geoposition/search', params=params)

            if response.status_code == 503 or 'ServiceUnavailable' in response.json().get('Code', ''):
                print("APIQuotaExceededError вызывается")
                raise APIQuotaExceededError("Запросы к API закончились")

            if response.status_code != 200 and response.status_code != 201:
                print('Ошибка при получении данных svg:', response.json())
                return f'Ошибка при получении данных. Код ошибки: {response.status_code}'

            return response.json()['Key']
        except APIQuotaExceededError as e:
            print(f"Обработка APIQuotaExceededError: {e}")
            raise
        except KeyError as e:
            raise Exception(f"Ошибка получения ключа локации: {e}")
        except Exception as e:
            raise Exception(f"Ошибка запроса к API AccuWeather: {e}")


class Weather:
    def __init__(self, accuweather_api_key):
        self.accuweather_key = accuweather_api_key
        self.weather = {}

    def get_forecast_data(self, location_key, days=1):
        try:
            if days == 1:
                forecast_url = (
                    f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}"
                )
            elif days == 5:
                forecast_url = (
                    f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}"
                )
            elif days == 10:
                forecast_url = f"http://dataservice.accuweather.com/forecasts/v1/daily/10day/{location_key}"
            elif days == 15:
                forecast_url = f"http://dataservice.accuweather.com/forecasts/v1/daily/15day/{location_key}"
            else:
                forecast_url = (
                    f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}"
                )
            params = {
                "apikey": accuweather_api_key,
                "language": "ru",
                "details": "true",
                "metric": "true",
            }
            response = requests.get(forecast_url, params=params)
            data = response.json()
            if data:
                return data
            else:
                return
        except APIQuotaExceededError as e:
            print(f"Обработка APIQuotaExceededError: {e}")
            raise
        except KeyError as e:
            raise Exception(f"Ошибка получения ключа локации: {e}")
        except Exception as e:
            raise Exception(f"Ошибка запроса к API AccuWeather: {e}")

    def check_bad_weather(self):
        try:
            weather = self.weather
            estimation = []

            if 'temperature' not in weather or 'wind_speed' not in weather or 'precipitation_prob' not in weather:
                raise KeyError("Недостаточно данных для оценки погодных условий.")

            if weather['temperature'] < 0 or weather['temperature'] > 35:
                estimation.append("Температура не в норме")
            if weather['wind_speed'] > 50:
                estimation.append("Порывы сильного ветра")
            if weather['precipitation_prob'] > 70:
                estimation.append("Высокая вероятность выпадения осадков")

            if estimation:
                answer = "Неблагоприятная погода: \n"
                for note in estimation:
                    answer = answer + '   - ' + note + '\n'
                return answer
            else:
                return "Погодные условия благоприятны"
        except KeyError as e:
            return f"KeyError: {e} - Недостаточно данных для проверки погодных условий."
        except Exception as e:
            return f"Произошла ошибка при оценке погодных условий: {e}"