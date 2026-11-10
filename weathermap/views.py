import requests

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from .models import City


XWEATHER_BASE_URL = "https://data.api.xweather.com/conditions"


def map_view(request):
    return render(request, "weathermap/map.html")


def get_cities_json(request):
    cities = City.objects.values(
        "id",
        "name",
        "country",
        "latitude",
        "longitude",
    )

    return JsonResponse(list(cities), safe=False)


def get_weather(request, city_id):
    city = get_object_or_404(City, pk=city_id)

    client_id = settings.XWEATHER_CLIENT_ID
    client_secret = settings.XWEATHER_CLIENT_SECRET

    if not client_id or not client_secret:
        return JsonResponse(
            {"error": "XWeather credentials are not configured."},
            status=503,
        )

    cache_key = f"weather_city_{city.id}"
    cached = cache.get(cache_key)

    if cached is not None:
        return JsonResponse(cached)

    # XWeather Conditions API uses the location in the URL.
    location = f"{city.latitude},{city.longitude}"
    url = f"{XWEATHER_BASE_URL}/{location}"

    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "units": "metric",
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10,
        )

        response.raise_for_status()
        payload = response.json()

        # Expected XWeather Conditions response:
        # response[0].periods[0]
        period = payload["response"][0]["periods"][0]

        result = {
            "city": city.name,
            "country": city.country,
            "temperature": period.get("tempC"),
            "feels_like": period.get("feelslikeC"),
            "humidity": period.get("humidity"),
            "pressure": period.get("pressureMB"),
            "wind_speed": period.get("windSpeedMPS"),
            "description": period.get("weather"),
            "icon": period.get("icon"),
        }

        cache.set(cache_key, result, timeout=600)

        return JsonResponse(result)

    except requests.exceptions.HTTPError as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else 502
        )

        if status_code in (401, 403):
            message = "XWeather rejected the API credentials or access."

        elif status_code == 429:
            message = "XWeather request limit has been reached."

        else:
            message = f"XWeather returned HTTP {status_code}."

        # Do not return str(error):
        # the request URL can contain credentials.
        return JsonResponse(
            {"error": message},
            status=502,
        )

    except requests.exceptions.RequestException:
        return JsonResponse(
            {"error": "Could not connect to the weather provider."},
            status=502,
        )

    except (KeyError, IndexError, TypeError, ValueError):
        return JsonResponse(
            {"error": "Unexpected response from the weather provider."},
            status=502,
        )

def get_forecast(request, city_id):
    """
    Return a three-day forecast for one city.

    The browser calls Django.
    Django calls XWeather using secret credentials.
    Successful results are cached for ten minutes.
    """

    city = get_object_or_404(City, pk=city_id)

    client_id = settings.XWEATHER_CLIENT_ID
    client_secret = settings.XWEATHER_CLIENT_SECRET

    if not client_id or not client_secret:
        return JsonResponse(
            {"error": "XWeather credentials are not configured."},
            status=503,
        )

    cache_key = f"forecast_city_{city.id}"

    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return JsonResponse(cached_data)

    location = f"{city.latitude},{city.longitude}"

    url = (
        "https://data.api.xweather.com/"
        f"forecasts/{location}"
    )

    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "units": "metric",
        "filter": "day",
        "limit": 3,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        payload = response.json()

        raw_periods = payload["response"][0]["periods"]

        forecast_days = []

        for period in raw_periods[:3]:

            date_time = period.get("dateTimeISO")

            if not date_time:
                raise ValueError("Forecast date is missing")

            forecast_days.append({
                "date": date_time[:10],
                "min_temp": period.get("minTempC"),
                "max_temp": period.get("maxTempC"),
                "description": period.get("weather"),
                "humidity": period.get("humidity"),
                "icon": period.get("icon"),
            })

        if not forecast_days:
            raise ValueError("No forecast periods returned")

        result = {
            "city": city.name,
            "country": city.country,
            "forecast": forecast_days,
        }

        cache.set(cache_key, result, timeout=600)

        return JsonResponse(result)

    except requests.exceptions.HTTPError as error:

        status_code = (
            error.response.status_code
            if error.response is not None
            else 502
        )

        if status_code in (401, 403):
            message = (
                "XWeather rejected the forecast request. "
                "Check credentials and endpoint access."
            )

        elif status_code == 429:
            message = "XWeather request limit reached."

        else:
            message = (
                f"XWeather forecast returned HTTP {status_code}."
            )

        return JsonResponse(
            {"error": message},
            status=502,
        )

    except requests.exceptions.RequestException:
        return JsonResponse(
            {"error": "Could not connect to XWeather forecast service."},
            status=502,
        )

    except (KeyError, IndexError, TypeError, ValueError):
        return JsonResponse(
            {"error": "Unexpected forecast response format."},
            status=502,
        )