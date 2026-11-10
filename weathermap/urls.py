from django.urls import path

from . import views

app_name = "weathermap"

urlpatterns = [
    path(
        "",
        views.map_view,
        name="map",
    ),
    path(
        "api/cities/",
        views.get_cities_json,
        name="cities",
    ),
    path(
        "api/weather/<int:city_id>/",
        views.get_weather,
        name="weather",
    ),
    path(
        "api/forecast/<int:city_id>/",
        views.get_forecast,
        name="forecast",
    ),
]