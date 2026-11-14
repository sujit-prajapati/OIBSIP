"""
Unit tests for WeatherService parsing, 24-hour forecast, alerts, and theme logic.
"""

import unittest
from datetime import datetime
from weather_service import WeatherService


class TestWeatherService(unittest.TestCase):
    def setUp(self):
        now_ts = int(datetime.now().timestamp())

        self.sample_weather_response = {
            "coord": {"lon": 72.8777, "lat": 19.076},
            "weather": [
                {
                    "id": 801,
                    "main": "Clouds",
                    "description": "few clouds",
                    "icon": "02d"
                }
            ],
            "base": "stations",
            "main": {
                "temp": 30.5,
                "feels_like": 35.2,
                "temp_min": 30.5,
                "temp_max": 30.5,
                "pressure": 1012,
                "humidity": 68
            },
            "visibility": 10000,
            "wind": {"speed": 4.12, "deg": 280},
            "sys": {
                "country": "IN",
                "sunrise": now_ts - 10000,
                "sunset": now_ts + 20000
            },
            "timezone": 19800,
            "name": "Mumbai",
            "cod": 200
        }

        self.sample_forecast_response = {
            "cod": "200",
            "cnt": 8,
            "list": [
                {
                    "dt": now_ts + 3600 * (i + 1),
                    "main": {"temp": 28.0 + i, "temp_min": 26.5, "temp_max": 34.0},
                    "weather": [{"main": "Clouds", "description": "few clouds", "icon": "02d"}],
                    "pop": 0.25
                }
                for i in range(8)
            ]
        }

    def test_parse_weather_data(self):
        data = WeatherService.parse_weather_data(self.sample_weather_response)
        self.assertEqual(data["city"], "Mumbai")
        self.assertEqual(data["country"], "IN")
        self.assertEqual(data["condition_main"], "Clouds")
        self.assertAlmostEqual(data["temp_c"], 30.5)
        self.assertEqual(data["humidity"], 68)

    def test_parse_forecast_24h_and_extremes(self):
        extremes, hourly, daily = WeatherService.parse_forecast_data(
            self.sample_forecast_response, 19800, current_temp_c=30.5
        )
        self.assertIsNotNone(extremes)
        assert extremes is not None
        self.assertLessEqual(extremes["temp_min_c"], 26.5)
        self.assertGreaterEqual(extremes["temp_max_c"], 34.0)

        # 24-hour forecast has 8 intervals
        self.assertEqual(len(hourly), 8)
        self.assertIn("time_label", hourly[0])
        self.assertEqual(hourly[0]["pop_percent"], 25)

    def test_weather_alerts(self):
        storm_data = {"condition_main": "Thunderstorm", "condition_desc": "severe storm", "temp_c": 28.0}
        alert = WeatherService.check_weather_alerts(storm_data, [])
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertIn("Thunderstorm", alert["title"])

        clear_data = {"condition_main": "Clear", "condition_desc": "clear sky", "temp_c": 25.0, "wind_speed_ms": 3.0}
        no_alert = WeatherService.check_weather_alerts(clear_data, [])
        self.assertIsNone(no_alert)

    def test_condition_theme(self):
        sunny_theme = WeatherService.get_condition_theme("Clear", "01d")
        self.assertEqual(sunny_theme["name"], "Sunny")

        storm_theme = WeatherService.get_condition_theme("Thunderstorm", "11d")
        self.assertEqual(storm_theme["name"], "Thunderstorm")

    def test_compass_conversion(self):
        self.assertEqual(WeatherService.deg_to_compass(0), "N")
        self.assertEqual(WeatherService.deg_to_compass(90), "E")
        self.assertEqual(WeatherService.deg_to_compass(180), "S")
        self.assertEqual(WeatherService.deg_to_compass(270), "W")


if __name__ == "__main__":
    unittest.main()
