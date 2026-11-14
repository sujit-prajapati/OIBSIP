"""
Comprehensive GUI Integration & Scenario Test Suite for WeatherApp.
Tests 24-hour hourly forecast, 5-day daily forecast, alert banners,
tooltips, unit conversions, and error scenarios.
"""

import unittest
from unittest.mock import patch
import tkinter as tk

from main import WeatherApp, ToolTip


class TestWeatherAppGUI(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = WeatherApp(self.root)

        self.sample_mumbai_full = {
            "city": "Mumbai",
            "country": "IN",
            "condition_main": "Clear",
            "condition_desc": "Clear Sky",
            "icon_code": "01d",
            "temp_c": 32.4,
            "feels_like_c": 36.8,
            "temp_min_c": 27.0,
            "temp_max_c": 35.0,
            "humidity": 65,
            "pressure": 1010,
            "wind_speed_ms": 3.6,
            "wind_deg": 280,
            "visibility_km": 10.0,
            "sunrise": "06:42 AM",
            "sunset": "06:01 PM",
            "timezone_offset": 19800,
            "timestamp": "10 Nov 2026 | 01:45 PM",
            "hourly_24h": [
                {
                    "time_label": f"{i:02d}:00",
                    "temp_c": 30.0 + i,
                    "condition_main": "Clear",
                    "condition_desc": "Sunny",
                    "icon_code": "01d",
                    "pop_percent": 10 * i,
                }
                for i in range(8)
            ],
            "forecast": [
                {
                    "date": "2026-11-10",
                    "day_label": "Today",
                    "temp_c": 32.0,
                    "temp_min_c": 27.0,
                    "temp_max_c": 35.0,
                    "condition_main": "Clear",
                    "condition_desc": "Clear Sky",
                    "icon_code": "01d",
                    "pop_percent": 10,
                },
                {
                    "date": "2026-11-11",
                    "day_label": "Tue, 11 Nov",
                    "temp_c": 31.0,
                    "temp_min_c": 26.0,
                    "temp_max_c": 34.0,
                    "condition_main": "Clouds",
                    "condition_desc": "Few Clouds",
                    "icon_code": "02d",
                    "pop_percent": 20,
                },
                {
                    "date": "2026-11-12",
                    "day_label": "Wed, 12 Nov",
                    "temp_c": 29.5,
                    "temp_min_c": 25.0,
                    "temp_max_c": 32.0,
                    "condition_main": "Rain",
                    "condition_desc": "Light Rain",
                    "icon_code": "10d",
                    "pop_percent": 60,
                },
                {
                    "date": "2026-11-13",
                    "day_label": "Thu, 13 Nov",
                    "temp_c": 30.0,
                    "temp_min_c": 26.0,
                    "temp_max_c": 33.0,
                    "condition_main": "Clear",
                    "condition_desc": "Sunny",
                    "icon_code": "01d",
                    "pop_percent": 15,
                },
                {
                    "date": "2026-11-14",
                    "day_label": "Fri, 14 Nov",
                    "temp_c": 31.5,
                    "temp_min_c": 27.0,
                    "temp_max_c": 34.0,
                    "condition_main": "Clouds",
                    "condition_desc": "Scattered Clouds",
                    "icon_code": "03d",
                    "pop_percent": 30,
                },
            ],
            "alert": {
                "title": "⚡ Thunderstorm Advisory",
                "message": "Isolated thunderstorm expected in evening.",
                "color": "#7C3AED",
                "bg": "#F5F3FF",
            },
            "theme": {
                "accent": "#D97706",
                "card_badge": "#FEF3C7",
                "badge_fg": "#B45309",
                "name": "Sunny",
            },
        }

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def test_initial_ui_state(self):
        """Verify initial UI controls and counts."""
        self.assertEqual(self.app.current_unit, "C")
        self.assertEqual(self.app.city_entry.get(), "Mumbai")
        self.assertFalse(self.app.is_loading)
        self.assertEqual(len(self.app.hourly_cards), 8)
        self.assertEqual(len(self.app.forecast_cards), 5)

    def test_render_weather_data_full(self):
        """Verify rendering of Hero card, 24-hour pills, and 5-day outlook."""
        self.app.set_unit("C")
        self.app._render_weather_data(self.sample_mumbai_full)

        self.assertIn("Mumbai, IN", self.app.lbl_location.cget("text"))
        self.assertEqual(self.app.lbl_temp.cget("text"), "32.4 °C")
        self.assertEqual(self.app.lbl_theme_pill.cget("text"), "● Sunny")

        # Alert banner is visible
        self.assertIn("Thunderstorm Advisory", self.app.lbl_alert_title.cget("text"))

        # Hourly 24-hour pills
        self.assertEqual(self.app.hourly_cards[0]["time"].cget("text"), "00:00")
        self.assertEqual(self.app.hourly_cards[0]["temp"].cget("text"), "30°")

        # 5-day outlook cards
        self.assertEqual(self.app.forecast_cards[0]["day"].cget("text"), "Today")
        self.assertEqual(self.app.forecast_cards[0]["temp"].cget("text"), "32.0 °C")
        self.assertEqual(self.app.forecast_cards[0]["rain"].cget("text"), "Rain: 10%")

    def test_unit_conversion_fahrenheit(self):
        """Verify toggle to Fahrenheit updates hero, hourly, and daily cards."""
        self.app.current_data = self.sample_mumbai_full
        self.app.set_unit("F")

        self.assertEqual(self.app.current_unit, "F")
        self.assertEqual(self.app.lbl_temp.cget("text"), "90.3 °F")
        # 30 C = 86 F
        self.assertEqual(self.app.hourly_cards[0]["temp"].cget("text"), "86°")
        # 32 C = 89.6 F
        self.assertEqual(self.app.forecast_cards[0]["temp"].cget("text"), "89.6 °F")

        # Toggle back
        self.app.set_unit("C")
        self.assertEqual(self.app.current_unit, "C")
        self.assertEqual(self.app.lbl_temp.cget("text"), "32.4 °C")

    def test_tooltip_behavior(self):
        """Verify tooltip instantiation and safe destruction."""
        tip = ToolTip(self.app.btn_refresh, "Test Tooltip")
        tip.show_tip()
        self.assertIsNotNone(tip.tip_window)
        tip.hide_tip()
        self.assertIsNone(tip.tip_window)

    def test_clear_recent_history(self):
        """Verify clearing search history chips."""
        self.app.recent_cities = ["Mumbai", "Delhi", "London"]
        self.app.clear_recent_history()
        self.assertEqual(self.app.recent_cities, ["Mumbai"])

    @patch("tkinter.messagebox.showwarning")
    def test_empty_city_warning(self, mock_warning):
        self.app.city_entry.delete(0, tk.END)
        self.app.trigger_search()
        mock_warning.assert_called_once()

    @patch("tkinter.messagebox.showerror")
    def test_error_handlers(self, mock_error):
        self.app._on_fetch_error("City Not Found", "City not found.", "#EF4444")
        mock_error.assert_called_once()
        self.assertIn("City Not Found", self.app.lbl_status.cget("text"))


if __name__ == "__main__":
    unittest.main()
