import os
import flask
import requests

accuweather_api_key = os.environ["ACCUWEATHER_API_KEY"]
yandex_api_key = os.environ["YANDEX_API_KEY"]

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
        data = self.request_to_yandex(city)
        if data:
            try:
                coords = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                lon, lat = coords.split(' ')
                return str(lon), str(lat)
            except Exception as e:
                raise Exception(f"Ошибка получения координат: {e}")
        return None, None


    def get_location_key(self, city: str):
        try:
            lon, lat = self.get_coordinates(city)
            params = {
                'apikey': self.accuweather_key,
                'q': f'{lat},{lon}'
            }
            response = requests.get('http://dataservice.accuweather.com/locations/v1/cities/geoposition/search', params=params)

            if response.status_code == 503 or 'ServiceUnavailable' in response.json().get('Code', ''):
                raise APIQuotaExceededError("Запросы к API закончились")

            if response.status_code != 200 and response.status_code != 201:
                print('Ошибка при получении данных svg:', response.json())
                return f'Ошибка при получении данных. Код ошибки: {response.status_code}'

            return response.json()['Key']
        except KeyError as e:
            raise Exception(f"Ошибка получения ключа локации: {e}")
        except Exception as e:
            raise Exception(f"Ошибка запроса к API AccuWeather: {e}")


import requests

class Weather:
    def __init__(self, accuweather_api_key):
        self.accuweather_key = accuweather_api_key
        self.weather = {}

    def get_current_weather(self, city: str, location: Location):
        try:
            location_key = location.get_location_key(city)

            if not location_key:
                raise Exception(f"Не удалось получить location_key")

            params = {
                "apikey": self.accuweather_key,
                "details": "true"
            }
            response = requests.get(f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}", params=params)

            if response.status_code != 200 and response.status_code != 201:
                return f"Ошибка при получении данных о погоде. Код ошибки: {response.status_code}"

            data = response.json()
            self.weather['temperature'] = data[0]['Temperature']['Metric']['Value']
            self.weather['humidity'] = data[0]['RelativeHumidity']
            self.weather['wind_speed'] = data[0]['Wind']['Speed']['Metric']['Value']
            return f"   - Температура: {self.weather['temperature']}°C \n   - Влажность: {self.weather['humidity']}% \n   - Скорость ветра: {self.weather['wind_speed']} м/с"
            #return data
        except Exception as e:
            raise Exception(f"Ошибка получения данных текущей погоды: {e}")





    def get_forecast(self, city: str, location: Location):
        try:
            location_key = location.get_location_key(city)

            params = {
                'apikey': self.accuweather_key,
                'language': 'ru',
                'details': 'true',
                'metric': 'true'
            }
            response = requests.get(f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}", params=params)

            data = response.json()
            self.weather['precipitation_prob'] = data['DailyForecasts'][0]['Day']['PrecipitationProbability']
            return f"   - Шанс дождя: {self.weather['precipitation_prob']}%"
            #return data
        except Exception as e:
            raise Exception(f"Ошибка получения данных прогноза погоды: {e}")

    def get_weather(self, city: str, location: Location):
        try:
            current_weather = self.get_current_weather(city, location)
            forecast = self.get_forecast(city, location)
        except APIQuotaExceededError:
            raise APIQuotaExceededError("Запросы к API закончились")
        except Exception as e:
            raise Exception(f"Ошибка получения данных текущей погоды и прогноза: {e}")

        return f"{current_weather}\n{forecast}"

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