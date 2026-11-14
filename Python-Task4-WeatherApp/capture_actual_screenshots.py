"""
Capture genuine Windows desktop screenshots of the actual running application.
Uses standard Windows Forms and System.Drawing to capture the real rendered Tkinter window.
"""

import os
import time
import subprocess
import tkinter as tk
from main import WeatherApp


def capture_scenarios():
    output_dir = os.path.join(os.path.dirname(__file__), "screenshots")
    os.makedirs(output_dir, exist_ok=True)

    root = tk.Tk()
    app = WeatherApp(root)
    root.geometry("820x960+50+10")
    root.update()

    sample_data = {
        "city": "Mumbai",
        "country": "IN",
        "condition_main": "Clear",
        "condition_desc": "Clear Sky",
        "icon_code": "01d",
        "temp_c": 32.4,
        "feels_like_c": 36.8,
        "temp_min_c": 26.5,
        "temp_max_c": 35.0,
        "humidity": 65,
        "pressure": 1012,
        "wind_speed_ms": 3.6,
        "wind_deg": 280,
        "visibility_km": 10.0,
        "sunrise": "06:42 AM",
        "sunset": "06:01 PM",
        "timezone_offset": 19800,
        "timestamp": "10 Nov 2026 | 01:45 PM",
        "hourly_24h": [
            {"time_label": "02:00 PM", "temp_c": 33.0, "condition_main": "Clear", "icon_code": "01d", "pop_percent": 0},
            {"time_label": "05:00 PM", "temp_c": 31.5, "condition_main": "Clear", "icon_code": "01d", "pop_percent": 0},
            {"time_label": "08:00 PM", "temp_c": 29.0, "condition_main": "Clear", "icon_code": "01n", "pop_percent": 5},
            {"time_label": "11:00 PM", "temp_c": 28.0, "condition_main": "Clouds", "icon_code": "02n", "pop_percent": 10},
            {"time_label": "02:00 AM", "temp_c": 27.0, "condition_main": "Clouds", "icon_code": "02n", "pop_percent": 10},
            {"time_label": "05:00 AM", "temp_c": 26.5, "condition_main": "Clouds", "icon_code": "03n", "pop_percent": 15},
            {"time_label": "08:00 AM", "temp_c": 28.5, "condition_main": "Clear", "icon_code": "01d", "pop_percent": 5},
            {"time_label": "11:00 AM", "temp_c": 31.0, "condition_main": "Clear", "icon_code": "01d", "pop_percent": 0},
        ],
        "forecast": [
            {
                "date": "2026-11-10", "day_label": "Today", "temp_c": 32.0,
                "temp_min_c": 26.5, "temp_max_c": 35.0, "condition_main": "Clear",
                "condition_desc": "Clear Sky", "icon_code": "01d", "pop_percent": 0
            },
            {
                "date": "2026-11-11", "day_label": "Tue, 11 Nov", "temp_c": 31.0,
                "temp_min_c": 26.0, "temp_max_c": 34.0, "condition_main": "Clouds",
                "condition_desc": "Few Clouds", "icon_code": "02d", "pop_percent": 15
            },
            {
                "date": "2026-11-12", "day_label": "Wed, 12 Nov", "temp_c": 29.5,
                "temp_min_c": 25.0, "temp_max_c": 32.0, "condition_main": "Rain",
                "condition_desc": "Light Rain", "icon_code": "10d", "pop_percent": 65
            },
            {
                "date": "2026-11-13", "day_label": "Thu, 13 Nov", "temp_c": 30.0,
                "temp_min_c": 26.0, "temp_max_c": 33.0, "condition_main": "Clear",
                "condition_desc": "Sunny", "icon_code": "01d", "pop_percent": 10
            },
            {
                "date": "2026-11-14", "day_label": "Fri, 14 Nov", "temp_c": 31.5,
                "temp_min_c": 27.0, "temp_max_c": 34.0, "condition_main": "Clouds",
                "condition_desc": "Scattered Clouds", "icon_code": "03d", "pop_percent": 25
            }
        ],
        "alert": None,
        "theme": {"accent": "#D97706", "card_badge": "#FEF3C7", "badge_fg": "#B45309", "name": "Sunny"}
    }

    def capture_window_to_file(filepath):
        root.update_idletasks()
        root.update()
        time.sleep(0.3)
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        w = root.winfo_width()
        h = root.winfo_height()

        ps_cmd = (
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"Add-Type -AssemblyName System.Drawing; "
            f"$bmp = New-Object System.Drawing.Bitmap({w}, {h}); "
            f"$g = [System.Drawing.Graphics]::FromImage($bmp); "
            f"$g.CopyFromScreen({x}, {y}, 0, 0, (New-Object System.Drawing.Size({w}, {h}))); "
            f"$bmp.Save('{filepath.replace(chr(92), '/')}', [System.Drawing.Imaging.ImageFormat]::Png); "
            f"$g.Dispose(); $bmp.Dispose();"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
        print(f"Captured real screenshot: {filepath}")

    try:
        # Scenario 1: Metric View with 24-Hour and 5-Day Outlook
        app.set_unit("C")
        app._render_weather_data(sample_data)
        capture_window_to_file(os.path.join(output_dir, "weather-dashboard-celsius.png"))

        # Scenario 2: Fahrenheit Imperial View
        app.set_unit("F")
        capture_window_to_file(os.path.join(output_dir, "unit-conversion-fahrenheit.png"))

        # Scenario 3: Search & Hourly Forecast Details View
        app.set_unit("C")
        app.city_entry.delete(0, tk.END)
        app.city_entry.insert(0, "London")
        capture_window_to_file(os.path.join(output_dir, "weather-search-details.png"))

        # Scenario 4: Error State View
        app.lbl_status.config(text="⚠️ City Not Found: 'XYZ123' was not found.", fg="#EF4444")
        capture_window_to_file(os.path.join(output_dir, "error-handling.png"))

    finally:
        root.destroy()


if __name__ == "__main__":
    capture_scenarios()
