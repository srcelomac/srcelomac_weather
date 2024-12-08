from flask import Flask, render_template, request
from main import Location, Weather, APIQuotaExceededError
import os

app = Flask(__name__)

ACCUWEATHER_API_KEY = os.environ["ACCUWEATHER_API_KEY"]
YANDEX_API_KEY = os.environ["YANDEX_API_KEY"]

location = Location(accuweather_api_key=ACCUWEATHER_API_KEY, yandex_api_key=YANDEX_API_KEY)
weather = Weather(accuweather_api_key=ACCUWEATHER_API_KEY)

@app.route("/", methods=["GET", "POST"])
def index():
    #result = None
    result_1 = None
    result_2 = None
    result_3 = None
    start_city = None
    end_city = None
    if request.method == "POST":
        start_city = request.form.get("start_city")
        end_city = request.form.get("end_city")

        try:
            find_start_city, start_weather = weather.get_weather(start_city, location)
            start_estimate = weather.check_bad_weather()

            find_end_city, end_weather = weather.get_weather(end_city, location)
            end_estimate = weather.check_bad_weather()

            #result = f"Погода в городе {start_city}:\n{start_weather}\nОценка: {start_estimate}\n\nПогода в {end_city}:\n{end_weather}\nОценка: {end_estimate}"
            result_1 = f"Погода в городе {find_start_city}:\n{start_weather}\nОценка: {start_estimate}"
            result_2 = f"Погода в городе {find_end_city}:\n{end_weather}\nОценка: {end_estimate}"
            if (len(start_estimate) == 0) and (len(end_estimate) == 0):
                result_3 = "Погодный условия благоприятны! Доброй дороги!"
            else:
                result_3 = "Погодный условия не благоприятны! Мы не советуем Вас сейчас отправляться в это путешествие :("
        except APIQuotaExceededError:
            return render_template("ErrorAPI.html")
        except Exception as e:
            print(f"Произошла ошибка: {e}")
            return render_template("Error.html")
    return render_template("index.html", city_1=start_city, result_1=result_1, city_2=end_city, result_2=result_2, result_3=result_3)

if __name__ == "__main__":
    app.run(debug=True)
