"""
Weather Service Module for Weather Forecast Application.
Handles OpenWeatherMap API communication for current weather, 24-hour hourly forecast,
5-day daily outlook, weather alerts, dynamic condition theming, and unit conversions.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
import requests


class WeatherServiceError(Exception):
    """Base exception for weather service errors."""
    pass


class CityNotFoundError(WeatherServiceError):
    """Raised when the specified city is not found (404)."""
    pass


class InvalidApiKeyError(WeatherServiceError):
    """Raised when the API key is missing or invalid (401)."""
    pass


class RateLimitExceededError(WeatherServiceError):
    """Raised when the API rate limit is exceeded (429)."""
    pass


class NetworkConnectionError(WeatherServiceError):
    """Raised when there is a network connectivity or DNS issue."""
    pass


class RequestTimeoutError(WeatherServiceError):
    """Raised when the API request times out."""
    pass


class WeatherService:
    """Service to interact with OpenWeatherMap API."""

    CURRENT_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
    DEFAULT_TIMEOUT = 10  # seconds

    def __init__(self, api_key: Optional[str]):
        """Initialize the WeatherService with an API key."""
        self.api_key = api_key

    def fetch_weather(self, city: str) -> Dict[str, Any]:
        """Fetch raw current weather data from OpenWeatherMap API."""
        return self._make_request(self.CURRENT_WEATHER_URL, city)

    def fetch_forecast(self, city: str) -> Dict[str, Any]:
        """Fetch 5-day / 3-hour forecast data from OpenWeatherMap API."""
        return self._make_request(self.FORECAST_URL, city)

    def _make_request(self, endpoint: str, city: str) -> Dict[str, Any]:
        """Helper to execute an HTTP GET request with standard error handling."""
        if not self.api_key:
            raise InvalidApiKeyError(
                "OpenWeatherMap API key is not configured.\n"
                "Please add OPENWEATHER_API_KEY to your .env file."
            )

        city_clean = city.strip()
        if not city_clean:
            raise ValueError("City name cannot be empty.")

        params = {
            "q": city_clean,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            response = requests.get(
                endpoint,
                params=params,
                timeout=self.DEFAULT_TIMEOUT
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                raise CityNotFoundError(
                    f"City '{city_clean}' was not found.\n"
                    "Please check spelling and try again."
                )
            elif response.status_code == 401:
                raise InvalidApiKeyError(
                    "Invalid API Key. Please verify your OpenWeatherMap API key."
                )
            elif response.status_code == 429:
                raise RateLimitExceededError(
                    "API call limit exceeded. Please try again later."
                )
            else:
                response.raise_for_status()
                return response.json()

        except requests.exceptions.Timeout as exc:
            raise RequestTimeoutError(
                "Request timed out while contacting OpenWeatherMap service."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise NetworkConnectionError(
                "Unable to connect to the weather service.\n"
                "Please check your internet connection."
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "Unknown"
            raise WeatherServiceError(
                f"HTTP error occurred: {status_code}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise WeatherServiceError(
                f"Network request error: {str(exc)}"
            ) from exc

    def fetch_full_weather(self, city: str) -> Dict[str, Any]:
        """
        Fetch current weather, 24-hour hourly forecast, and 5-day daily outlook.
        Computes accurate daily min/max for today from forecast intervals.
        """
        current_raw = self.fetch_weather(city)
        weather_data = self.parse_weather_data(current_raw)

        # Retrieve forecast data
        try:
            forecast_raw = self.fetch_forecast(city)
            tz_offset = weather_data.get("timezone_offset", 0)
            today_extremes, hourly_24h, daily_5d = self.parse_forecast_data(
                forecast_raw, tz_offset, weather_data["temp_c"]
            )
            # Update with true daily extremes
            if today_extremes:
                weather_data["temp_min_c"] = today_extremes["temp_min_c"]
                weather_data["temp_max_c"] = today_extremes["temp_max_c"]

            weather_data["hourly_24h"] = hourly_24h
            weather_data["forecast"] = daily_5d

            # Check for weather advisories
            weather_data["alert"] = self.check_weather_alerts(weather_data, daily_5d)

        except Exception:
            # If forecast fails, preserve current weather data with empty fallbacks
            weather_data["hourly_24h"] = []
            weather_data["forecast"] = []
            weather_data["alert"] = None

        # Add condition-based theme tokens
        weather_data["theme"] = self.get_condition_theme(
            weather_data["condition_main"], weather_data["icon_code"]
        )

        return weather_data

    @staticmethod
    def parse_weather_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw OpenWeatherMap API JSON into a clean, formatted dictionary."""
        tz_offset = raw_data.get("timezone", 0)
        local_tz = timezone(timedelta(seconds=tz_offset))

        # Sunrise and Sunset formatted to city's local time
        sunrise_ts = raw_data.get("sys", {}).get("sunrise")
        sunset_ts = raw_data.get("sys", {}).get("sunset")

        sunrise_str = "--:--"
        if sunrise_ts:
            sunrise_dt = datetime.fromtimestamp(sunrise_ts, tz=local_tz)
            sunrise_str = sunrise_dt.strftime("%I:%M %p")

        sunset_str = "--:--"
        if sunset_ts:
            sunset_dt = datetime.fromtimestamp(sunset_ts, tz=local_tz)
            sunset_str = sunset_dt.strftime("%I:%M %p")

        # Weather condition and icon
        weather_list = raw_data.get("weather") or [{}]
        weather_primary = weather_list[0] if weather_list else {}
        condition_main = weather_primary.get("main", "Clear")
        condition_desc = weather_primary.get("description", "clear sky").title()
        icon_code = weather_primary.get("icon", "01d")

        # Main metrics (in metric units)
        main_data = raw_data.get("main", {})
        temp_c = float(main_data.get("temp", 0.0))
        feels_like_c = float(main_data.get("feels_like", 0.0))
        temp_min_c = float(main_data.get("temp_min", 0.0))
        temp_max_c = float(main_data.get("temp_max", 0.0))
        humidity = int(main_data.get("humidity", 0))
        pressure = int(main_data.get("pressure", 0))

        # Wind
        wind_data = raw_data.get("wind", {})
        wind_speed_ms = float(wind_data.get("speed", 0.0))
        wind_deg = wind_data.get("deg")

        # Visibility (in meters from API, convert to km)
        visibility_m = raw_data.get("visibility")
        visibility_km = (visibility_m / 1000.0) if visibility_m is not None else None

        # Location details
        city_name = raw_data.get("name", "Unknown")
        country = raw_data.get("sys", {}).get("country", "")

        return {
            "city": city_name,
            "country": country,
            "condition_main": condition_main,
            "condition_desc": condition_desc,
            "icon_code": icon_code,
            "temp_c": temp_c,
            "feels_like_c": feels_like_c,
            "temp_min_c": temp_min_c,
            "temp_max_c": temp_max_c,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed_ms": wind_speed_ms,
            "wind_deg": wind_deg,
            "visibility_km": visibility_km,
            "sunrise": sunrise_str,
            "sunset": sunset_str,
            "timezone_offset": tz_offset,
            "timestamp": datetime.now().strftime("%d %b %Y | %I:%M:%S %p"),
            "hourly_24h": [],
            "forecast": [],
            "alert": None,
        }

    @staticmethod
    def parse_forecast_data(
        raw_forecast: Dict[str, Any],
        timezone_offset: int,
        current_temp_c: float
    ) -> Tuple[Optional[Dict[str, float]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process 3-hour forecast entries into:
        1. True daily min/max for today.
        2. 24-Hour hourly forecast pills (first 8 entries).
        3. 5-Day daily forecast outlook cards.
        """
        forecast_list = raw_forecast.get("list", [])
        if not forecast_list:
            return None, [], []

        local_tz = timezone(timedelta(seconds=timezone_offset))
        today_date = datetime.now(tz=local_tz).date()

        # Group entries by local date
        grouped_by_date: Dict[Any, List[Tuple[datetime, Dict[str, Any]]]] = {}
        for entry in forecast_list:
            dt_utc = datetime.fromtimestamp(entry["dt"], tz=timezone.utc)
            dt_local = dt_utc.astimezone(local_tz)
            entry_date = dt_local.date()

            if entry_date not in grouped_by_date:
                grouped_by_date[entry_date] = []
            grouped_by_date[entry_date].append((dt_local, entry))

        # 1. Calculate True Today's Min and Max
        today_entries = [e for dt, e in grouped_by_date.get(today_date, [])]
        today_min = current_temp_c
        today_max = current_temp_c

        if today_entries:
            for item in today_entries:
                main_sec = item.get("main", {})
                today_min = min(today_min, float(main_sec.get("temp_min", today_min)))
                today_max = max(today_max, float(main_sec.get("temp_max", today_max)))

        today_extremes = {
            "temp_min_c": today_min,
            "temp_max_c": today_max,
        }

        # 2. Extract 24-Hour Hourly Forecast (First 8 3-hour intervals)
        hourly_24h: List[Dict[str, Any]] = []
        for entry in forecast_list[:8]:
            dt_utc = datetime.fromtimestamp(entry["dt"], tz=timezone.utc)
            dt_local = dt_utc.astimezone(local_tz)
            time_lbl = dt_local.strftime("%I:%M %p")

            main_sec = entry.get("main", {})
            weather_list = entry.get("weather") or [{}]
            weather_obj = weather_list[0]
            pop = float(entry.get("pop", 0.0))  # Probability of precipitation (0.0 to 1.0)

            hourly_24h.append({
                "time_label": time_lbl,
                "temp_c": float(main_sec.get("temp", 0.0)),
                "condition_main": weather_obj.get("main", "Clear"),
                "condition_desc": weather_obj.get("description", "Clear Sky").title(),
                "icon_code": weather_obj.get("icon", "01d"),
                "pop_percent": int(pop * 100),
            })

        # 3. Extract 5-Day Daily Outlook
        daily_5d: List[Dict[str, Any]] = []
        future_dates = [d for d in sorted(grouped_by_date.keys()) if d >= today_date]
        target_dates = future_dates[:5] if len(future_dates) <= 5 else future_dates[1:6]
        if not target_dates and future_dates:
            target_dates = future_dates[:5]

        for d in target_dates:
            day_entries = grouped_by_date[d]
            temps = [e["main"]["temp"] for dt, e in day_entries]
            min_temps = [e["main"].get("temp_min", e["main"]["temp"]) for dt, e in day_entries]
            max_temps = [e["main"].get("temp_max", e["main"]["temp"]) for dt, e in day_entries]

            # Choose reading closest to 12:00 PM local time for expected daytime weather
            best_entry = day_entries[0][1]
            min_diff = 999999
            for dt_local, entry in day_entries:
                diff = abs(dt_local.hour - 12)
                if diff < min_diff:
                    min_diff = diff
                    best_entry = entry

            weather_list = best_entry.get("weather") or [{}]
            weather_obj = weather_list[0]
            cond_main = weather_obj.get("main", "Clear")
            cond_desc = weather_obj.get("description", "Clear Sky").title()
            icon_code = weather_obj.get("icon", "01d")
            pop_max = max([float(e.get("pop", 0.0)) for dt, e in day_entries] or [0.0])

            if d == today_date:
                day_label = "Today"
            else:
                day_label = d.strftime("%a, %d %b")

            daily_5d.append({
                "date": d.strftime("%Y-%m-%d"),
                "day_label": day_label,
                "temp_c": sum(temps) / len(temps) if temps else 0.0,
                "temp_min_c": min(min_temps) if min_temps else 0.0,
                "temp_max_c": max(max_temps) if max_temps else 0.0,
                "condition_main": cond_main,
                "condition_desc": cond_desc,
                "icon_code": icon_code,
                "pop_percent": int(pop_max * 100),
            })

        return today_extremes, hourly_24h, daily_5d

    @staticmethod
    def get_condition_theme(condition_main: str, icon_code: str = "") -> Dict[str, str]:
        """
        Returns subtle condition-themed accent colors while maintaining
        the blue-and-white professional aesthetic.
        """
        cond = condition_main.lower()
        is_night = icon_code.endswith("n")

        if "thunderstorm" in cond:
            return {
                "accent": "#7C3AED",       # Deep Purple
                "card_badge": "#EDE9FE",   # Soft Purple
                "badge_fg": "#5B21B6",
                "name": "Thunderstorm"
            }
        elif "rain" in cond or "drizzle" in cond:
            return {
                "accent": "#2563EB",       # Royal Blue
                "card_badge": "#EFF6FF",   # Soft Blue
                "badge_fg": "#1E40AF",
                "name": "Rainy"
            }
        elif "snow" in cond:
            return {
                "accent": "#0284C7",       # Ocean Ice
                "card_badge": "#F0F9FF",   # Soft Cyan
                "badge_fg": "#0369A1",
                "name": "Snowy"
            }
        elif "mist" in cond or "fog" in cond or "haze" in cond:
            return {
                "accent": "#64748B",       # Slate Gray
                "card_badge": "#F1F5F9",   # Soft Gray
                "badge_fg": "#334155",
                "name": "Misty"
            }
        elif "clear" in cond:
            if is_night:
                return {
                    "accent": "#4338CA",   # Indigo Night
                    "card_badge": "#EEF2FF",
                    "badge_fg": "#3730A3",
                    "name": "Clear Night"
                }
            return {
                "accent": "#D97706",       # Amber Gold Sun
                "card_badge": "#FEF3C7",   # Soft Yellow
                "badge_fg": "#B45309",
                "name": "Sunny"
            }
        else:  # Clouds
            return {
                "accent": "#1E40AF",       # Standard Royal Blue
                "card_badge": "#EFF6FF",   # Soft Blue
                "badge_fg": "#1E40AF",
                "name": "Cloudy"
            }

    @staticmethod
    def check_weather_alerts(
        current_data: Dict[str, Any],
        forecast_list: List[Dict[str, Any]]
    ) -> Optional[Dict[str, str]]:
        """
        Detect and format weather warnings and advisories based on atmospheric data.
        """
        cond = current_data.get("condition_main", "").lower()
        desc = current_data.get("condition_desc", "")
        temp_c = current_data.get("temp_c", 20.0)
        wind_ms = current_data.get("wind_speed_ms", 0.0)
        visibility_km = current_data.get("visibility_km")

        if "thunderstorm" in cond:
            return {
                "title": "⚡ Thunderstorm Advisory",
                "message": f"Active thunderstorm ({desc}) in the region. Seek indoor shelter.",
                "color": "#7C3AED",
                "bg": "#F5F3FF"
            }
        elif "heavy rain" in desc.lower() or "extreme rain" in desc.lower():
            return {
                "title": "🌧️ Heavy Rainfall Warning",
                "message": f"Intense precipitation ({desc}) reported. Watch for localized waterlogging.",
                "color": "#1E40AF",
                "bg": "#EFF6FF"
            }
        elif wind_ms >= 12.0:
            return {
                "title": "💨 High Wind Advisory",
                "message": f"Strong winds detected at {wind_ms:.1f} m/s ({WeatherService.ms_to_mph(wind_ms):.1f} mph).",
                "color": "#B45309",
                "bg": "#FFFBEB"
            }
        elif visibility_km is not None and visibility_km < 2.0:
            return {
                "title": "🌫️ Low Visibility Warning",
                "message": f"Optical range reduced to {visibility_km:.1f} km due to dense fog/haze.",
                "color": "#475569",
                "bg": "#F8FAFC"
            }
        elif temp_c >= 40.0:
            return {
                "title": "☀️ Extreme Heat Advisory",
                "message": f"Elevated temperature ({temp_c:.1f}°C). Stay hydrated and minimize direct sun exposure.",
                "color": "#DC2626",
                "bg": "#FEF2F2"
            }
        elif temp_c <= 0.0:
            return {
                "title": "❄️ Sub-Zero Freeze Warning",
                "message": f"Freezing conditions ({temp_c:.1f}°C). Watch for frost and black ice.",
                "color": "#0284C7",
                "bg": "#F0F9FF"
            }

        return None

    @staticmethod
    def get_weather_symbol(condition: str, icon_code: str = "") -> str:
        """Get an appropriate modern emoji icon as fallback."""
        cond = condition.lower()
        is_night = icon_code.endswith("n")

        if "thunderstorm" in cond:
            return "⛈️"
        elif "drizzle" in cond:
            return "🌦️"
        elif "rain" in cond:
            return "🌧️"
        elif "snow" in cond:
            return "❄️"
        elif "mist" in cond or "fog" in cond or "haze" in cond or "smoke" in cond:
            return "🌫️"
        elif "tornado" in cond or "squall" in cond:
            return "🌪️"
        elif "clear" in cond:
            return "🌙" if is_night else "☀️"
        elif "cloud" in cond:
            if "few" in cond or "scattered" in cond:
                return "🌤️" if not is_night else "☁️"
            return "☁️"

        return "🌤️"

    @staticmethod
    def deg_to_compass(deg: Optional[float]) -> str:
        """Convert wind direction in degrees to a 16-point cardinal compass string."""
        if deg is None:
            return ""
        directions = [
            "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
        ]
        index = int((deg + 11.25) / 22.5) % 16
        return directions[index]

    @staticmethod
    def c_to_f(celsius: float) -> float:
        """Convert Celsius to Fahrenheit."""
        return (celsius * 9.0 / 5.0) + 32.0

    @staticmethod
    def ms_to_mph(ms: float) -> float:
        """Convert meters per second to miles per hour."""
        return ms * 2.23694
