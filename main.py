import os
import flask
import requests

accuweather_api_key = os.environ["ACCUWEATHER_API_KEY"]
yandex_api_key = os.environ["YANDEX_API_KEY"]


class Location:
    def __init__(self, accuweather_api_key, yandex_api_key):
        self.yandex_key = yandex_api_key
        self.accuweather_key = accuweather_api_key

    def request_to_yandex(self, city: str):
        params = {
            'apikey': self.yandex_key,
            'geocode': city,
            'lang': 'ru_RU',
            'format': 'json'
        }

        response = requests.get('https://geocode-maps.yandex.ru/1.x', params=params)

        if response.status_code != 200:
            print(f'Ошибка при получении данных. Код ошибки: {response.status_code}')
            return  None

        return response.json()


    def get_coordinates(self, city: str):
        data = self.request_to_yandex(city)
        if data:
            try:
                coords = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                lon, lat = coords.split(' ')
                return str(lon), str(lat)
            except KeyError:
                print('Не удалось получить координаты')
                return None, None
        return None, None


    def get_location_key(self, city: str):
        lon, lat = self.get_coordinates(city)
        if lon and lat:
            params = {
                'apikey': self.accuweather_key,
                'q': f'{lat},{lon}'
            }
            response = requests.get('http://dataservice.accuweather.com/locations/v1/cities/geoposition/search', params=params)

            if response.status_code != 200 and response.status_code != 201:
                print('Ошибка при получении данных:', response.json())
                return f'Ошибка при получении данных. Код ошибки: {response.status_code}'

            return response.json()['Key']
        else:
            return "Не удалось получить координаты для указанного города."


import requests

class Weather:
    def __init__(self, accuweather_api_key):
        self.accuweather_key = accuweather_api_key
        self.weather = {}

    def get_current_weather(self, city: str, location: Location):
        location_key = location.get_location_key(city)

        if not location_key:
            return f"Не удалось получить location_key: {location_key}"

        params = {
            "apikey": self.accuweather_key,
            "details": "true"
        }
        response = requests.get(f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}", params=params)

        if response.status_code != 200 and response.status_code != 201:
            return f"Ошибка при получении данных о погоде. Код ошибки: {response.status_code}"

        data = response.json()
        if data:
            try:
                self.weather['temperature'] = data[0]['Temperature']['Metric']['Value']
                self.weather['humidity'] = data[0]['RelativeHumidity']
                self.weather['wind_speed'] = data[0]['Wind']['Speed']['Metric']['Value']
                return f"   - Температура: {self.weather['temperature']}°C \n   - Влажность: {self.weather['humidity']}% \n   - Скорость ветра: {self.weather['wind_speed']} м/с"
                #return data
            except KeyError as e:
                return f"KeyError: {e} - Некорректный формат данных."
            except Exception as e:
                return f"Произошла ошибка: {e}"
        return "Данные о погоде отсутствуют."

    def get_forecast(self, city: str, location: Location):
        location_key = location.get_location_key(city)

        params = {
            'apikey': self.accuweather_key,
            'language': 'ru',
            'details': 'true',
            'metric': 'true'
        }
        response = requests.get(f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}", params=params)

        data = response.json()
        if data:
            self.weather['precipitation_prob'] = data['DailyForecasts'][0]['Day']['PrecipitationProbability']
            return f"   - Шанс дождя: {self.weather['precipitation_prob']}%"
            #return data
        else:
            return "Не получилось получить данные о погоде"

    def get_weather(self, city: str, location: Location):
        current_weather = self.get_current_weather(city, location)
        forecast = self.get_forecast(city, location)

        # Возвращаем все данные о текущей погоде и прогнозе
        return f"{current_weather}\n{forecast}"

    def check_bad_weather(self):
        weather = self.weather
        estimation = []

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