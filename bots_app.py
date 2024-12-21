from flask import Flask, render_template, request
from main import Location, Weather, APIQuotaExceededError
import os
from dash import Dash, html, dcc, Input, Output, State, ALL
import plotly.graph_objects as go
import pandas as pd
import logging
from dash import dash_table
from dash.dash_table.Format import Group
from dotenv import load_dotenv
from pathlib import Path
from queue import Queue
import time
from threading import Thread

app = Dash(__name__)

weather_data = None
forecast_days = 1
cities_coordinates = []

import json

def load_forecast_from_json(filename="weather_forecast.json"):
    try:
        # Загружаем данные из файла
        with open(filename, 'r') as f:
            data = json.load(f)

        # Извлекаем данные
        weather_data = data.get("weather", {})
        forecast_days = data.get("forecast_days", 0)
        cities_coordinates = data.get("city_coordinates", [])

        # Возвращаем распакованные переменные
        return weather_data, forecast_days, cities_coordinates

    except Exception as e:
        print(f"Ошибка при загрузке данных из файла {filename}: {e}")
        return None, None, None

weather_data, forecast_days, cities_coordinates = load_forecast_from_json()

print('----------------------')
print(weather_data)
print('----------------------')
print(forecast_days)
print('----------------------')
print(cities_coordinates)

data_queue = Queue()



app.layout = html.Div(
    [
        html.H1("Прогноз погоды"),
        html.Div(id="output-container"),
        dcc.Interval(
            id='interval-component',
            interval=10 * 1000,  # Обновление каждые 60 секунд
            n_intervals=0
        ),
    ]
)

@app.callback(
    Output("output-container", "children"),
    Input("output-container", "children"),
)
def update_output(current_children):
    try:
        global weather_data, forecast_days, cities_coordinates

        if weather_data is None:
            return html.Div("Ожидаем данные...")
        output_children = []
        try:
            df_city_coordinates = pd.DataFrame(cities_coordinates)
            # print('--------КООРДИНАТЫ-----------')
            # print(df_city_coordinates)
            # print('-------------------')
            # print(df_city_coordinates.columns)
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
                #forecast = data["forecast"]
                forecast = data
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
                #forecast = data["forecast"]
                forecast = data
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
    except Exception as e:
        logging.error(f"Ошибка при обработке прогноза: {str(e)}")
        return html.Div(f"Произошла ошибка: {str(e)}. Пожалуйста, попробуйте еще раз.", style={"color": "red"})

def start_dash_app():
    app.run_server(debug=True, use_reloader=False)

if __name__ == "__main__":
    try:
        start_dash_app()
    except Exception as e:
        logging.error(f"Ошибка при запуске сервера: {str(e)}")