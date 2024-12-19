import dash
from dash import dcc, html, Input, Output
from main import Location, Weather, APIQuotaExceededError
import os

app = dash.Dash(__name__)

ACCUWEATHER_API_KEY = os.environ["ACCUWEATHER_API_KEY_6"]
YANDEX_API_KEY = os.environ["YANDEX_API_KEY"]

location = Location(accuweather_api_key=ACCUWEATHER_API_KEY, yandex_api_key=YANDEX_API_KEY)
weather = Weather(accuweather_api_key=ACCUWEATHER_API_KEY)

# Определяем layout приложения
app.layout = html.Div([
    html.H1("Погода и оценка путешествия"),

    # Ввод данных для городов
    html.Div([
        html.Label("Начальный город:"),
        dcc.Input(id="start-city", type="text", value="", style={"marginRight": "10px"}),
        html.Label("Конечный город:"),
        dcc.Input(id="end-city", type="text", value=""),
    ], style={"marginBottom": "20px"}),

    # Кнопка для отправки формы
    html.Button("Получить погоду", id="submit-btn", n_clicks=0),

    # Результаты
    html.Div(id="result-1", style={"marginTop": "20px"}),
    html.Div(id="result-2"),
    html.Div(id="result-3"),
])

# Колбэк для обработки данных и вывода результатов
@app.callback(
    [Output("result-1", "children"),
     Output("result-2", "children"),
     Output("result-3", "children")],
    [Input("submit-btn", "n_clicks")],
    [Input("start-city", "value"),
     Input("end-city", "value")]
)
def update_weather(n_clicks, start_city, end_city):
    result_1 = None
    result_2 = None
    result_3 = None

    if n_clicks > 0:
        try:
            # Получаем погоду для начального города
            find_start_city, start_weather = weather.get_weather(start_city, location)
            start_estimate = weather.check_bad_weather()

            # Получаем погоду для конечного города
            find_end_city, end_weather = weather.get_weather(end_city, location)
            end_estimate = weather.check_bad_weather()

            # Формируем текстовые результаты
            result_1 = f"Погода в городе {find_start_city}:\n{start_weather}\nОценка: {start_estimate}"
            result_2 = f"Погода в городе {find_end_city}:\n{end_weather}\nОценка: {end_estimate}"

            if (len(start_estimate) == 0) and (len(end_estimate) == 0):
                result_3 = "Погодные условия благоприятны! Доброй дороги!"
            else:
                result_3 = "Погодные условия не благоприятны! Мы не советуем вам сейчас отправляться в это путешествие :("
        except APIQuotaExceededError:
            return "Превышен лимит запросов к API. Пожалуйста, попробуйте позже."
        except Exception as e:
            print(f"Произошла ошибка: {e}")
            return "Произошла ошибка. Попробуйте снова."

    return result_1, result_2, result_3

if __name__ == "__main__":
    app.run_server(debug=True)
