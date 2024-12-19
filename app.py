from flask import Flask, render_template, request
from main import Location, Weather, APIQuotaExceededError
import os
from dash import Dash, html, dcc, Input, Output, State, ALL
import plotly.graph_objects as go
import pandas as pd
import logging
from dash import dash_table
from dash.dash_table.Format import Group

app = Dash(__name__)

ACCUWEATHER_API_KEY = os.environ["ACCUWEATHER_API_KEY_9"]
YANDEX_API_KEY = os.environ["YANDEX_API_KEY"]

location = Location(accuweather_api_key=ACCUWEATHER_API_KEY, yandex_api_key=YANDEX_API_KEY)
weather = Weather(accuweather_api_key=ACCUWEATHER_API_KEY)

app.layout = html.Div(
    [
        html.H1("Прогноз погоды"),
        html.Div(
            [
                html.Label("Введите города маршрута:"),
                html.Div(
                    [
                        dcc.Input(
                            id={"type": "city-input", "index": 0},
                            type="text",
                            placeholder="Город №1",
                        ),
                    ],
                    id="city-input-container",
                ),
                html.Button("Добавить город в маршрут", id="add-city", n_clicks=0),
            ]
        ),
        html.Div(
            [
                html.Label("Выберите, на сколько дней построить прогноз:"),
                dcc.Dropdown(
                    id="forecast-days",
                    options=[
                        {"label": "1 день", "value": 1},
                        {"label": "2 дня", "value": 2},
                        {"label": "3 дня", "value": 3},
                        {"label": "4 дня", "value": 4},
                        {"label": "5 дней", "value": 5},
                    ],
                    value=1,
                ),
            ]
        ),
        html.Button("Получить прогноз", id="submit-button", n_clicks=0),
        html.Div(id="output-container"),
    ]
)


@app.callback(
    Output("city-input-container", "children"),
    Input("add-city", "n_clicks"),
    State("city-input-container", "children"),
)
def city_inputs(n_clicks, children):
    try:
        new_children = children.copy()
        new_input = dcc.Input(
            id={"type": "city-input", "index": n_clicks},
            type="text",
            placeholder=f"Город №{n_clicks + 2}",
        )
        new_children.append(new_input)
        return new_children
    except Exception as e:
        logging.error(f"Ошибка при добавлении города: {str(e)}")
        return children



@app.callback(
    Output("output-container", "children"),
    Input("submit-button", "n_clicks"),
    State({"type": "city-input", "index": ALL}, "value"),
    State("forecast-days", "value"),
)
def update_output(n_clicks, cities, forecast_days):
    try:
        if n_clicks > 0:
            all_cities = [city for city in cities if city]
            if not all_cities:
                return html.Div("Должен быть введен хотя бы один город")
            if any(any(char.isdigit() for char in element) for element in all_cities):
                return html.Div("В названии городов не должны присутстовать цифры")

            weather_data = {}
            city_coordinates = []
            errors = []
            for city in all_cities:
                try:
                    lat, lon = location.get_coordinates(city)
                    location_key = location.get_location_key(lat, lon)
                    if not location_key:
                        errors.append(f"Не удалось найти город <<{city}>>")
                        continue
                    forecast = weather.get_forecast_data(location_key, days=forecast_days)
                    if not forecast:
                        errors.append(f"Не удалось получить прогноз для города <<{city}>>")
                        continue
                    weather_data[city] = {
                        "forecast": forecast,
                        "latitude": lat,
                        "longitude": lon,
                    }
                    city_coordinates.append({"city": city, "lat": lat, "lon": lon})
                except APIQuotaExceededError:
                    errors.append(f"Превышена квота запросов для API по городу <<{city}>>")
                except Exception as e:
                    errors.append(f"Ошибка обработки города <<{city}>>: {str(e)}")

            if not weather_data:
                return html.Div(errors, style={"color": "red"})

            output_children = []

            if errors:
                output_children.append(html.Div(errors))

            try:
                df_city_coordinates = pd.DataFrame(city_coordinates)
                fig = go.Figure()

                fig.add_trace(
                    go.Scattermapbox(
                        lat=df_city_coordinates["lat"],
                        lon=df_city_coordinates["lon"],
                        mode="markers+lines",
                        marker=go.scattermapbox.Marker(size=9),
                        text=df_city_coordinates["city"],
                    )
                )

                fig.update_layout(
                    mapbox_style="open-street-map",
                    mapbox_zoom=3,
                    mapbox_center_lat=df_city_coordinates["lat"].mean(),
                    mapbox_center_lon=df_city_coordinates["lon"].mean(),
                    height=500,
                )

                fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

                output_children.append(dcc.Graph(figure=fig))

                for city, data in weather_data.items():
                    forecast = data["forecast"]
                    dates = []
                    min_temps = []
                    max_temps = []
                    wind_speeds = []
                    precipitation_probs = []
                    for cnt, day in enumerate(forecast["DailyForecasts"]):
                        if (cnt >= forecast_days):
                            break
                        dates.append(day["Date"][:10])
                        min_temps.append(day["Temperature"]["Minimum"]["Value"])
                        max_temps.append(day["Temperature"]["Maximum"]["Value"])
                        wind_speeds.append(day["Day"]["Wind"]["Speed"]["Value"])
                        precipitation_probs.append(day["Day"]["PrecipitationProbability"])

                    temp_trace_min = go.Scatter(x=dates, y=min_temps, mode="lines+markers", name="Мин. температура")
                    temp_trace_max = go.Scatter(x=dates, y=max_temps, mode="lines+markers", name="Макс. температура")

                    temp_layout = go.Layout(
                        title=f"Температура в городе '{city}'",
                        xaxis={"title": "Дата"},
                        yaxis={"title": "Температура (°C)"},
                    )
                    temp_fig = go.Figure(
                        data=[temp_trace_min, temp_trace_max], layout=temp_layout
                    )
                    output_children.append(dcc.Graph(figure=temp_fig))

                    wind_trace = go.Bar(x=dates, y=wind_speeds, name="Скорость ветра")
                    wind_layout = go.Layout(
                        title=f"Скорость ветра в городе '{city}'",
                        xaxis={"title": "Дата"},
                        yaxis={"title": "Скорость ветра (км/ч)"},
                    )
                    wind_fig = go.Figure(data=[wind_trace], layout=wind_layout)
                    output_children.append(dcc.Graph(figure=wind_fig))

                    precipitation_prob_trace = go.Bar(x=dates, y=precipitation_probs, name="Вероятность осадков")
                    precipitation_prob_layout = go.Layout(
                        title=f"Вероятность дождя в городе '{city}'",
                        xaxis={"title": "Дата"},
                        yaxis={"title": "Вероятность (%)"},
                    )
                    precip_fig = go.Figure(data=[precipitation_prob_trace], layout=precipitation_prob_layout)
                    output_children.append(dcc.Graph(figure=precip_fig))

                table_data = []
                for city, data in weather_data.items():
                    forecast = data["forecast"]
                    for cnt, day in enumerate(forecast["DailyForecasts"]):
                        if (cnt >= forecast_days):
                            break
                        table_data.append({
                            "Город": city,
                            "Дата": day["Date"][:10],
                            "Мин. температура (°C)": day["Temperature"]["Minimum"]["Value"],
                            "Макс. температура (°C)": day["Temperature"]["Maximum"]["Value"],
                            "Скорость ветра (км/ч)": day["Day"]["Wind"]["Speed"]["Value"],
                            "Вероятность осадков (%)": day["Day"]["PrecipitationProbability"]
                        })

                table = dash_table.DataTable(
                    id='weather-table',
                    columns=[
                        {"name": "Город", "id": "Город"},
                        {"name": "Дата", "id": "Дата"},
                        {"name": "Мин. температура (°C)", "id": "Мин. температура (°C)"},
                        {"name": "Макс. температура (°C)", "id": "Макс. температура (°C)"},
                        {"name": "Скорость ветра (км/ч)", "id": "Скорость ветра (км/ч)"},
                        {"name": "Вероятность осадков (%)", "id": "Вероятность осадков (%)"},
                    ],
                    data=table_data,
                    style_table={'height': '400px', 'overflowY': 'auto'},
                    style_cell={'textAlign': 'center', 'padding': '5px'},
                    style_header={'fontWeight': 'bold', 'textAlign': 'center'},
                )

                output_children.append(table)

            except Exception as e:
                print(f'Ошибка: {str(e)}')
                logging.error(f"Ошибка при создании графиков: {str(e)}")
                return html.Div(f"Произошла ошибка: {str(e)}. Пожалуйста, попробуйте еще раз.", style={"color": "red"})

            return output_children
        else:
            return html.Div()
    except Exception as e:
        logging.error(f"Ошибка при обработке прогноза: {str(e)}")
        return html.Div(f"Произошла ошибка: {str(e)}. Пожалуйста, попробуйте еще раз.", style={"color": "red"})


if __name__ == "__main__":
    try:
        app.run_server(debug=True)
    except Exception as e:
        logging.error(f"Ошибка при запуске сервера: {str(e)}")