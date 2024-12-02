import os
import flask
import requests

accuweather_api_key = os.environ["ACCUWEATHER_API_KEY"]
yandex_api_key = os.environ["YANDEX_API_KEY"]

print(accuweather_api_key)
print(yandex_api_key)


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

        '''
        if data:
            try:
                coordinates = data['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                lon, lat = coordinates.split(' ')
                return str(lon), str(lat)
            except KeyError as e:
                print(f"KeyError: {e} - Возможно, отсутствует один из необходимых ключей.")
            except Exception as e:
                print(f"Произошла ошибка: {e}")

        return None, None
        '''


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

    '''
    def get_location_key(self, address):
        url = "http://dataservice.accuweather.com/locations/v1/cities/search"
        params = {
            "apikey": accuweather_api_key,
            "q": address
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]['Key']
            else:
                print("Местоположение не найдено.")
        else:
            print(f"Ошибка API: {response.status_code}")
        return None
    '''

location = Location(accuweather_api_key=accuweather_api_key, yandex_api_key=yandex_api_key)
location_key = location.get_location_key('Москва')
print(location_key)
