from unittest.mock import MagicMock, patch

import requests
from unittest.mock import MagicMock, patch
from django.core.cache import cache
from django.test import TestCase, override_settings

from .models import City


SAMPLE_WEATHER = {
    "response": [
        {
            "periods": [
                {
                    "tempC": 12.3,
                    "feelslikeC": 11.0,
                    "humidity": 80,
                    "pressureMB": 1012,
                    "windSpeedMPS": 4.1,
                    "weather": "Light rain",
                    "icon": "rain.png",
                }
            ]
        }
    ]
}


@override_settings(
    XWEATHER_CLIENT_ID="test-id",
    XWEATHER_CLIENT_SECRET="test-secret",
)
class WeatherMapTests(TestCase):

    def setUp(self):
        cache.clear()

        self.city = City.objects.create(
            name="Dublin",
            country="Ireland",
            latitude=53.3498,
            longitude=-6.2603,
        )

    def test_map_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_cities_api(self):
        response = self.client.get("/api/cities/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["name"], "Dublin")

    def test_unknown_city(self):
        response = self.client.get("/api/weather/999999/")
        self.assertEqual(response.status_code, 404)

    @patch("weathermap.views.requests.get")
    def test_weather_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_WEATHER
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = self.client.get(
            f"/api/weather/{self.city.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["temperature"], 12.3)
        self.assertEqual(response.json()["humidity"], 80)

        self.assertEqual(
            mock_get.call_args.kwargs["params"]["units"],
            "metric",
        )

    @patch("weathermap.views.requests.get")
    def test_weather_caching(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_WEATHER
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        self.client.get(f"/api/weather/{self.city.id}/")
        self.client.get(f"/api/weather/{self.city.id}/")

        self.assertEqual(mock_get.call_count, 1)

    @override_settings(
        XWEATHER_CLIENT_ID="",
        XWEATHER_CLIENT_SECRET="",
    )
    def test_missing_credentials(self):
        response = self.client.get(
            f"/api/weather/{self.city.id}/"
        )
        self.assertEqual(response.status_code, 503)

    @patch("weathermap.views.requests.get")
    def test_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()

        response = self.client.get(
            f"/api/weather/{self.city.id}/"
        )

        self.assertEqual(response.status_code, 502)

    @patch("weathermap.views.requests.get")
    def test_invalid_provider_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"wrong": "data"}
        mock_get.return_value = mock_response

        response = self.client.get(
            f"/api/weather/{self.city.id}/"
        )

        self.assertEqual(response.status_code, 502)

    @patch("weathermap.views.requests.get")
    def test_rejected_credentials_do_not_leak(self, mock_get):
        error_response = MagicMock()
        error_response.status_code = 401

        mock_get.return_value.raise_for_status.side_effect = (
            requests.exceptions.HTTPError(
                "Rejected request with client_secret=test-secret",
                response=error_response,
            )
        )

        response = self.client.get(
            f"/api/weather/{self.city.id}/"
        )

        self.assertEqual(response.status_code, 502)
        self.assertNotIn(
            "test-secret",
            response.content.decode(),
        )

    @patch("weathermap.views.requests.get")
    def test_three_day_forecast(self, mock_get):
        sample_forecast = {
            "response": [
                {
                    "periods": [
                        {
                            "dateTimeISO": "2026-11-10T07:00:00+00:00",
                            "minTempC": 6.0,
                            "maxTempC": 12.0,
                            "weather": "Cloudy",
                            "humidity": 75,
                            "icon": "cloudy.png",
                        },
                        {
                            "dateTimeISO": "2026-11-11T07:00:00+00:00",
                            "minTempC": 5.0,
                            "maxTempC": 11.0,
                            "weather": "Rain",
                            "humidity": 85,
                            "icon": "rain.png",
                        },
                        {
                            "dateTimeISO": "2026-11-12T07:00:00+00:00",
                            "minTempC": 7.0,
                            "maxTempC": 13.0,
                            "weather": "Partly cloudy",
                            "humidity": 70,
                            "icon": "pcloudy.png",
                        },
                    ]
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = sample_forecast
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = self.client.get(
            f"/api/forecast/{self.city.id}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["forecast"]), 3)
        self.assertEqual(
            response.json()["forecast"][0]["max_temp"],
            12.0,
        )

    @patch("weathermap.views.requests.get")
    def test_forecast_cache(self, mock_get):
        sample_forecast = {
            "response": [
                {
                    "periods": [
                        {
                            "dateTimeISO": "2026-11-10T07:00:00+00:00",
                            "minTempC": 6,
                            "maxTempC": 12,
                            "weather": "Cloudy",
                        }
                    ]
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = sample_forecast
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = f"/api/forecast/{self.city.id}/"

        self.client.get(url)
        self.client.get(url)

        self.assertEqual(mock_get.call_count, 1)

    def test_unknown_forecast_city(self):
        response = self.client.get("/api/forecast/999999/")
        self.assertEqual(response.status_code, 404)