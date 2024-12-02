from flask import Flask, render_template, request
from main import Location, Weather
import os

app = Flask(__name__)

ACCUWEATHER_API_KEY = os.environ["ACCUWEATHER_API_KEY"]
YANDEX_API_KEY = os.environ["YANDEX_API_KEY"]

location = Location(accuweather_api_key=ACCUWEATHER_API_KEY, yandex_api_key=YANDEX_API_KEY)
weather = Weather(accuweather_api_key=ACCUWEATHER_API_KEY)

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        start_city = request.form.get("start_city")
        end_city = request.form.get("end_city")

        start_weather = weather.get_weather(start_city, location)
        start_estimate = weather.check_bad_weather()

        end_weather = weather.get_weather(end_city, location)
        end_estimate = weather.check_bad_weather()

        result = f"Погода в {start_city}:\n{start_weather}\nОценка: {start_estimate}\n\nПогода в {end_city}:\n{end_weather}\nОценка: {end_estimate}"

    return render_template("index.html", result=result)

if __name__ == "__main__":
    app.run(debug=True)
