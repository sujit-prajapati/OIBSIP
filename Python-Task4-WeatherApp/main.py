"""
Weather Forecast Desktop Application - Professional Edition.

A modern, premium desktop weather dashboard built with Python, Tkinter,
and the OpenWeatherMap API.

Features:
    - Real-time atmospheric observations (Temp, Feels Like, Humidity, Wind, Pressure, Visibility, Sun)
    - 24-Hour hourly forecast pills (3-hour intervals with precipitation probability)
    - 5-Day daily forecast outlook cards with true min/max temperatures
    - Dynamic weather alerts and atmospheric advisory banners
    - Condition-based dynamic accent themes (Sunny, Rainy, Stormy, Snowy, Cloudy, Misty)
    - Vibrant, colorful local PNG weather icons (zero black silhouettes)
    - Interactive informational tooltips for atmospheric measurements
    - Instant °C / °F unit toggle across current, 24-hour, and 5-day forecasts
    - Non-blocking background worker threading for smooth UI responsiveness
    - Deduplicated recent search chips with Clear History support
    - Wind speed with 16-point cardinal compass headings

Internship Project:
    Oasis Infobyte Python Programming Internship (Task 4)
Author:
    Sujit Prajapati
"""

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional, List, Dict

from dotenv import load_dotenv

from weather_service import (
    WeatherService,
    WeatherServiceError,
    CityNotFoundError,
    InvalidApiKeyError,
    RateLimitExceededError,
    NetworkConnectionError,
    RequestTimeoutError,
)

# ---------------------------------------------------------------------------
# UI Theme Colors (Professional Blue & White Palette)
# ---------------------------------------------------------------------------
COLOR_BG = "#F1F5F9"           # Soft slate-blue canvas background
COLOR_PRIMARY = "#1E40AF"      # Deep Royal Blue
COLOR_PRIMARY_HOVER = "#1D4ED8"# Hover blue
COLOR_ACCENT = "#2563EB"       # Sky Blue Accent
COLOR_CARD_BG = "#FFFFFF"      # Crisp White Card Background
COLOR_CARD_BORDER = "#E2E8F0"  # Subtle Border
COLOR_TEXT_MAIN = "#0F172A"    # High contrast Slate Black
COLOR_TEXT_MUTED = "#64748B"   # Cool Gray Secondary
COLOR_BADGE_BG = "#EFF6FF"     # Very soft blue pill badge
COLOR_SUCCESS = "#10B981"      # Green status
COLOR_WARNING = "#F59E0B"      # Amber status
COLOR_DANGER = "#EF4444"       # Red status


class ToolTip:
    """Lightweight, non-intrusive hover tooltip for GUI elements."""

    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        try:
            if not self.widget.winfo_exists():
                return
            x = self.widget.winfo_rootx() + 15
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        except tk.TclError:
            return
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#0F172A",
            foreground="#FFFFFF",
            relief="flat",
            font=("Segoe UI", 8),
            padx=8,
            pady=4,
        )
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class WeatherApp:
    """Main Application Controller for Weather Forecast Dashboard."""

    DEFAULT_CITY = "Mumbai"
    MAX_RECENT_CITIES = 5

    def __init__(self, root: tk.Tk):
        """Initialize window, state, and UI components."""
        self.root = root
        self.root.title("Weather Forecast Dashboard - Oasis Infobyte")
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        init_w = min(820, max(700, screen_w - 40))
        init_h = min(920, max(660, screen_h - 70))
        x_pos = max(0, (screen_w - init_w) // 2)
        y_pos = max(0, (screen_h - init_h) // 2 - 15)
        self.root.geometry(f"{init_w}x{init_h}+{x_pos}+{y_pos}")
        self.root.minsize(min(740, screen_w - 40), min(660, screen_h - 80))
        self.root.configure(bg=COLOR_BG)

        # Load API configuration
        load_dotenv()
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
        self.weather_service = WeatherService(api_key=self.api_key)

        # State management
        self.current_unit = "C"  # 'C' for Celsius, 'F' for Fahrenheit
        self.current_data: Optional[Dict] = None
        self.is_loading = False
        self.recent_cities: List[str] = [
            "Mumbai", "Delhi", "Bengaluru", "London", "New York"
        ]

        # Icon caching
        self.icon_cache: Dict[str, tk.PhotoImage] = {}
        self.small_icon_cache: Dict[str, tk.PhotoImage] = {}
        self.icons_dir = os.path.join(os.path.dirname(__file__), "assets", "icons")

        # Build UI
        self._setup_styles()
        self._build_status_bar()
        self._build_scrollable_container()
        self._build_header()
        self._build_search_section()
        self._build_recent_chips()
        self._build_alert_banner()
        self._build_hero_card()
        self._build_hourly_section()
        self._build_metrics_grid()
        self._build_forecast_section()

        # Keyboard shortcuts
        self.root.bind("<Return>", lambda event: self.trigger_search())
        self.root.bind("<F5>", lambda event: self.refresh_weather())

        # Load initial city on startup in background
        self._startup_after_id: Optional[str] = self.root.after(
            100, self._run_startup_search
        )

    def _run_startup_search(self):
        """Safely initiate default city weather fetch if window still exists."""
        self._startup_after_id = None
        try:
            if self.root.winfo_exists():
                self.search_city(self.DEFAULT_CITY)
        except tk.TclError:
            pass

    # -----------------------------------------------------------------------
    # Icon Helper Methods
    # -----------------------------------------------------------------------
    def _get_icon_image(self, icon_code: str, small: bool = False) -> Optional[tk.PhotoImage]:
        """Load local PNG weather icon with memory caching."""
        cache = self.small_icon_cache if small else self.icon_cache
        if icon_code in cache:
            return cache[icon_code]

        icon_path = os.path.join(self.icons_dir, f"{icon_code}.png")
        if not os.path.exists(icon_path) and icon_code.endswith("n"):
            icon_path = os.path.join(self.icons_dir, f"{icon_code[:-1]}d.png")

        if os.path.exists(icon_path):
            try:
                base_img = tk.PhotoImage(file=icon_path)
                img = base_img.subsample(2, 2) if small else base_img
                cache[icon_code] = img
                return img
            except Exception:
                return None
        return None

    # -----------------------------------------------------------------------
    # UI Building Methods
    # -----------------------------------------------------------------------
    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use("clam")

    def _build_scrollable_container(self):
        """Build smooth canvas container with mouse wheel support."""
        self.canvas = tk.Canvas(self.root, bg=COLOR_BG, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(
            self.root, orient="vertical", command=self.canvas.yview
        )
        self.scroll_content = tk.Frame(self.canvas, bg=COLOR_BG)

        self.scroll_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scroll_content, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.root.bind("<MouseWheel>", self._on_mousewheel)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

    def _on_mousewheel(self, event):
        """Scroll dashboard canvas safely on mouse wheel."""
        try:
            if self.canvas.winfo_exists():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass

    def _on_canvas_configure(self, event):
        """Dynamically resize scroll content to match canvas width perfectly."""
        if event.widget == self.canvas:
            self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _build_header(self):
        """Build the application title bar and unit conversion toggle."""
        header_frame = tk.Frame(self.scroll_content, bg=COLOR_BG)
        header_frame.pack(fill="x", padx=30, pady=(16, 8))

        title_box = tk.Frame(header_frame, bg=COLOR_BG)
        title_box.pack(side="left")

        app_title = tk.Label(
            title_box,
            text="🌤️ WEATHER FORECAST DASHBOARD",
            font=("Segoe UI", 18, "bold"),
            bg=COLOR_BG,
            fg=COLOR_PRIMARY,
        )
        app_title.pack(anchor="w")

        app_subtitle = tk.Label(
            title_box,
            text="Live global atmospheric intelligence, hourly & 5-day outlook",
            font=("Segoe UI", 9),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED,
        )
        app_subtitle.pack(anchor="w")

        # Unit Toggle Buttons (°C / °F)
        toggle_box = tk.Frame(
            header_frame,
            bg=COLOR_CARD_BORDER,
            padx=2,
            pady=2,
            relief="flat"
        )
        toggle_box.pack(side="right", pady=5)

        self.btn_celsius = tk.Button(
            toggle_box,
            text="°C",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_PRIMARY,
            fg="white",
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
            command=lambda: self.set_unit("C"),
        )
        self.btn_celsius.pack(side="left")
        ToolTip(self.btn_celsius, "Switch to Metric units (°C, m/s, km)")

        self.btn_fahrenheit = tk.Button(
            toggle_box,
            text="°F",
            font=("Segoe UI", 9, "bold"),
            bg="white",
            fg=COLOR_TEXT_MAIN,
            relief="flat",
            padx=12,
            pady=3,
            cursor="hand2",
            command=lambda: self.set_unit("F"),
        )
        self.btn_fahrenheit.pack(side="left")
        ToolTip(self.btn_fahrenheit, "Switch to Imperial units (°F, mph, mi)")

    def _build_search_section(self):
        """Build modern search input, Search button, and Refresh button."""
        search_container = tk.Frame(
            self.scroll_content,
            bg=COLOR_CARD_BG,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=10,
            pady=6
        )
        search_container.pack(fill="x", padx=30, pady=(4, 8))

        search_icon = tk.Label(
            search_container,
            text="🔍",
            font=("Segoe UI", 11),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED
        )
        search_icon.pack(side="left", padx=(8, 4))

        self.city_entry = tk.Entry(
            search_container,
            font=("Segoe UI", 12),
            relief="flat",
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_PRIMARY
        )
        self.city_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.city_entry.insert(0, self.DEFAULT_CITY)
        self.city_entry.bind("<FocusIn>", lambda e: self.city_entry.select_range(0, tk.END))

        # Clear text button
        btn_clear = tk.Button(
            search_container,
            text="✕",
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED,
            activeforeground=COLOR_TEXT_MAIN,
            relief="flat",
            cursor="hand2",
            command=self._clear_search_field
        )
        btn_clear.pack(side="left", padx=(0, 8))
        ToolTip(btn_clear, "Clear city input")

        # Search Button
        self.btn_search = tk.Button(
            search_container,
            text="Search",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_PRIMARY,
            fg="white",
            activebackground=COLOR_PRIMARY_HOVER,
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=5,
            cursor="hand2",
            command=self.trigger_search
        )
        self.btn_search.pack(side="left", padx=(0, 6))

        # Refresh Button
        self.btn_refresh = tk.Button(
            search_container,
            text="🔄 Refresh",
            font=("Segoe UI", 10),
            bg="#E2E8F0",
            fg=COLOR_TEXT_MAIN,
            activebackground="#CBD5E1",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.refresh_weather
        )
        self.btn_refresh.pack(side="left")
        ToolTip(self.btn_refresh, "Reload latest live weather observations (F5)")

    def _build_recent_chips(self):
        """Build clickable quick-search chips for recent/popular cities with clear option."""
        self.chips_frame = tk.Frame(self.scroll_content, bg=COLOR_BG)
        self.chips_frame.pack(fill="x", padx=30, pady=(0, 8))

        lbl_recent = tk.Label(
            self.chips_frame,
            text="Recent Searches:",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED
        )
        lbl_recent.pack(side="left", padx=(4, 6))

        self.chip_buttons_container = tk.Frame(self.chips_frame, bg=COLOR_BG)
        self.chip_buttons_container.pack(side="left", fill="x")

        self.btn_clear_history = tk.Button(
            self.chips_frame,
            text="✕ Clear History",
            font=("Segoe UI", 8),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED,
            activeforeground=COLOR_DANGER,
            relief="flat",
            cursor="hand2",
            command=self.clear_recent_history
        )
        self.btn_clear_history.pack(side="right", padx=(6, 0))
        ToolTip(self.btn_clear_history, "Clear recent search chips")

        self._render_chips()

    def _render_chips(self):
        """Render recent city pill buttons."""
        for widget in self.chip_buttons_container.winfo_children():
            widget.destroy()

        for city in self.recent_cities:
            chip = tk.Button(
                self.chip_buttons_container,
                text=city,
                font=("Segoe UI", 8),
                bg=COLOR_CARD_BG,
                fg=COLOR_PRIMARY,
                relief="flat",
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
                padx=8,
                pady=1,
                cursor="hand2",
                command=lambda c=city: self.search_city(c)
            )
            chip.pack(side="left", padx=3)

    def clear_recent_history(self):
        """Clear recent search history chips."""
        self.recent_cities = [self.DEFAULT_CITY]
        self._render_chips()

    def _build_alert_banner(self):
        """Build weather alert / advisory banner frame."""
        self.alert_frame = tk.Frame(
            self.scroll_content,
            bg="#FEF2F2",
            highlightbackground="#FCA5A5",
            highlightthickness=1,
            padx=14,
            pady=8
        )
        # Hidden by default until an alert is detected

        self.lbl_alert_title = tk.Label(
            self.alert_frame,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg="#FEF2F2",
            fg=COLOR_DANGER
        )
        self.lbl_alert_title.pack(anchor="w")

        self.lbl_alert_msg = tk.Label(
            self.alert_frame,
            text="",
            font=("Segoe UI", 9),
            bg="#FEF2F2",
            fg=COLOR_TEXT_MAIN
        )
        self.lbl_alert_msg.pack(anchor="w")

    def _build_hero_card(self):
        """Build the main hero card showing city, temperature, colorful icon, and theme badge."""
        self.hero_card = tk.Frame(
            self.scroll_content,
            bg=COLOR_CARD_BG,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=22,
            pady=16
        )
        self.hero_card.pack(fill="x", padx=30, pady=(0, 10))

        # Location and time bar
        top_row = tk.Frame(self.hero_card, bg=COLOR_CARD_BG)
        top_row.pack(fill="x")

        self.lbl_location = tk.Label(
            top_row,
            text="📍 Searching...",
            font=("Segoe UI", 16, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MAIN
        )
        self.lbl_location.pack(side="left")

        # Condition Theme Pill
        self.lbl_theme_pill = tk.Label(
            top_row,
            text="● Live",
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_BADGE_BG,
            fg=COLOR_PRIMARY,
            padx=8,
            pady=2,
            relief="flat"
        )
        self.lbl_theme_pill.pack(side="left", padx=10)

        self.lbl_time = tk.Label(
            top_row,
            text="",
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED
        )
        self.lbl_time.pack(side="right")

        # Weather Hero Display: Colorful Icon + Temp + Condition
        center_row = tk.Frame(self.hero_card, bg=COLOR_CARD_BG)
        center_row.pack(fill="x", pady=(10, 6))

        self.lbl_icon = tk.Label(
            center_row,
            text="",
            font=("Segoe UI Emoji", 36),
            bg=COLOR_CARD_BG
        )
        self.lbl_icon.pack(side="left", padx=(10, 18))

        temp_info_box = tk.Frame(center_row, bg=COLOR_CARD_BG)
        temp_info_box.pack(side="left", fill="y", expand=True, anchor="w")

        self.lbl_temp = tk.Label(
            temp_info_box,
            text="-- °C",
            font=("Segoe UI", 36, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_PRIMARY
        )
        self.lbl_temp.pack(anchor="w")

        self.lbl_condition = tk.Label(
            temp_info_box,
            text="Weather Condition",
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MAIN
        )
        self.lbl_condition.pack(anchor="w")

        # Pills Row: Feels Like + True Daily Min / Max Range
        pills_row = tk.Frame(self.hero_card, bg=COLOR_CARD_BG)
        pills_row.pack(fill="x", pady=(6, 0))

        self.lbl_feels_like_pill = tk.Label(
            pills_row,
            text="Feels like: -- °C",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_BADGE_BG,
            fg=COLOR_PRIMARY,
            padx=10,
            pady=3,
            relief="flat"
        )
        self.lbl_feels_like_pill.pack(side="left", padx=(0, 10))
        ToolTip(self.lbl_feels_like_pill, "Apparent temperature considering humidity and wind factor")

        self.lbl_temp_range_pill = tk.Label(
            pills_row,
            text="Today's Min: -- °C  |  Max: -- °C",
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            fg=COLOR_TEXT_MUTED,
            padx=10,
            pady=3,
            relief="flat"
        )
        self.lbl_temp_range_pill.pack(side="left")
        ToolTip(self.lbl_temp_range_pill, "True daily minimum & maximum calculated from forecast intervals")

    def _build_hourly_section(self):
        """Build 24-hour hourly forecast pills section."""
        lbl_hourly = tk.Label(
            self.scroll_content,
            text="⏱️ 24-HOUR FORECAST (3-Hour Intervals)",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED
        )
        lbl_hourly.pack(anchor="w", padx=32, pady=(4, 6))

        self.hourly_container = tk.Frame(self.scroll_content, bg=COLOR_BG)
        self.hourly_container.pack(fill="x", padx=30, pady=(0, 10))

        # 8 columns for 24 hours
        for c in range(8):
            self.hourly_container.columnconfigure(c, weight=1)

        self.hourly_cards: List[Dict[str, tk.Label]] = []
        for i in range(8):
            pill_box = tk.Frame(
                self.hourly_container,
                bg=COLOR_CARD_BG,
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
                padx=4,
                pady=8
            )
            pill_box.grid(row=0, column=i, padx=2, sticky="nsew")

            lbl_time = tk.Label(
                pill_box,
                text="--",
                font=("Segoe UI", 8, "bold"),
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_MAIN
            )
            lbl_time.pack()

            lbl_icon = tk.Label(
                pill_box,
                text="",
                font=("Segoe UI Emoji", 14),
                bg=COLOR_CARD_BG
            )
            lbl_icon.pack(pady=2)

            lbl_temp = tk.Label(
                pill_box,
                text="--",
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_CARD_BG,
                fg=COLOR_PRIMARY
            )
            lbl_temp.pack()

            lbl_pop = tk.Label(
                pill_box,
                text="--",
                font=("Segoe UI", 7),
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_MUTED
            )
            lbl_pop.pack(pady=(2, 0))

            self.hourly_cards.append({
                "time": lbl_time,
                "icon": lbl_icon,
                "temp": lbl_temp,
                "pop": lbl_pop,
            })

    def _build_metrics_grid(self):
        """Build 2x3 grid of detail cards with informative tooltips."""
        section_label = tk.Label(
            self.scroll_content,
            text="ATMOSPHERIC DETAILS",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED
        )
        section_label.pack(anchor="w", padx=32, pady=(4, 6))

        grid_container = tk.Frame(self.scroll_content, bg=COLOR_BG)
        grid_container.pack(fill="x", padx=30, pady=(0, 10))

        for col in range(3):
            grid_container.columnconfigure(col, weight=1)

        # Card 1: Humidity
        self.card_humidity, card_h_frame = self._create_metric_card(
            grid_container, row=0, col=0,
            icon="💧", title="Humidity", default_val="--"
        )
        ToolTip(card_h_frame, "Relative humidity in the atmosphere. 30%-60% is comfortable.")

        # Card 2: Wind Speed + Compass Direction
        self.card_wind, card_w_frame = self._create_metric_card(
            grid_container, row=0, col=1,
            icon="💨", title="Wind Speed", default_val="--"
        )
        ToolTip(card_w_frame, "Current wind velocity and 16-point cardinal compass direction.")

        # Card 3: Atmospheric Pressure
        self.card_pressure, card_p_frame = self._create_metric_card(
            grid_container, row=0, col=2,
            icon="⏲️", title="Pressure", default_val="--"
        )
        ToolTip(card_p_frame, "Barometric air pressure in hectopascals (hPa). Standard sea-level is 1013 hPa.")

        # Card 4: Visibility
        self.card_visibility, card_v_frame = self._create_metric_card(
            grid_container, row=1, col=0,
            icon="👁️", title="Visibility", default_val="--"
        )
        ToolTip(card_v_frame, "Horizontal optical clarity. Above 10 km indicates clear visibility.")

        # Card 5: Sunrise
        self.card_sunrise, card_sr_frame = self._create_metric_card(
            grid_container, row=1, col=1,
            icon="🌅", title="Sunrise", default_val="--"
        )
        ToolTip(card_sr_frame, "Local sunrise time adjusted to the city's UTC timezone offset.")

        # Card 6: Sunset
        self.card_sunset, card_ss_frame = self._create_metric_card(
            grid_container, row=1, col=2,
            icon="🌇", title="Sunset", default_val="--"
        )
        ToolTip(card_ss_frame, "Local sunset time adjusted to the city's UTC timezone offset.")

    def _create_metric_card(
        self, parent: tk.Widget, row: int, col: int,
        icon: str, title: str, default_val: str
    ):
        """Create a styled weather parameter card and return (value_label, card_frame)."""
        card_frame = tk.Frame(
            parent,
            bg=COLOR_CARD_BG,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=14,
            pady=10
        )
        card_frame.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        header = tk.Frame(card_frame, bg=COLOR_CARD_BG)
        header.pack(fill="x", anchor="w")

        icon_lbl = tk.Label(
            header,
            text=icon,
            font=("Segoe UI Emoji", 12),
            bg=COLOR_CARD_BG
        )
        icon_lbl.pack(side="left", padx=(0, 5))

        title_lbl = tk.Label(
            header,
            text=title,
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED
        )
        title_lbl.pack(side="left")

        val_lbl = tk.Label(
            card_frame,
            text=default_val,
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MAIN
        )
        val_lbl.pack(anchor="w", pady=(6, 0))

        return val_lbl, card_frame

    def _build_forecast_section(self):
        """Build 5-day weather forecast horizontal section."""
        lbl_forecast = tk.Label(
            self.scroll_content,
            text="📅 5-DAY WEATHER OUTLOOK",
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED
        )
        lbl_forecast.pack(anchor="w", padx=32, pady=(4, 6))

        self.forecast_container = tk.Frame(self.scroll_content, bg=COLOR_BG)
        self.forecast_container.pack(fill="x", padx=30, pady=(0, 16))

        for c in range(5):
            self.forecast_container.columnconfigure(c, weight=1)

        self.forecast_cards: List[Dict[str, tk.Label]] = []
        for i in range(5):
            card_box = tk.Frame(
                self.forecast_container,
                bg=COLOR_CARD_BG,
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
                padx=8,
                pady=10
            )
            card_box.grid(row=0, column=i, padx=3, sticky="nsew")

            lbl_day = tk.Label(
                card_box,
                text="--",
                font=("Segoe UI", 9, "bold"),
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_MAIN
            )
            lbl_day.pack()

            lbl_icon = tk.Label(
                card_box,
                text="",
                font=("Segoe UI Emoji", 20),
                bg=COLOR_CARD_BG
            )
            lbl_icon.pack(pady=4)

            lbl_temp = tk.Label(
                card_box,
                text="-- °C",
                font=("Segoe UI", 11, "bold"),
                bg=COLOR_CARD_BG,
                fg=COLOR_PRIMARY
            )
            lbl_temp.pack()

            lbl_range = tk.Label(
                card_box,
                text="-- / --",
                font=("Segoe UI", 8),
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_MUTED
            )
            lbl_range.pack()

            lbl_desc = tk.Label(
                card_box,
                text="--",
                font=("Segoe UI", 8),
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_MUTED,
                wraplength=100
            )
            lbl_desc.pack(pady=(2, 0))

            lbl_rain = tk.Label(
                card_box,
                text="",
                font=("Segoe UI", 7),
                bg=COLOR_CARD_BG,
                fg=COLOR_PRIMARY
            )
            lbl_rain.pack(pady=(1, 0))

            self.forecast_cards.append({
                "day": lbl_day,
                "icon": lbl_icon,
                "temp": lbl_temp,
                "range": lbl_range,
                "desc": lbl_desc,
                "rain": lbl_rain,
            })

    def _build_status_bar(self):
        """Build status bar at bottom of window."""
        status_bar = tk.Frame(
            self.root,
            bg=COLOR_CARD_BG,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=16,
            pady=6
        )
        status_bar.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(
            status_bar,
            text="● Ready",
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_SUCCESS
        )
        self.lbl_status.pack(side="left")

        self.lbl_last_updated = tk.Label(
            status_bar,
            text="Press Search or F5 to refresh",
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED
        )
        self.lbl_last_updated.pack(side="right")

    # -----------------------------------------------------------------------
    # Logic & Event Handlers
    # -----------------------------------------------------------------------
    def _clear_search_field(self):
        """Clear entry text and give it focus."""
        self.city_entry.delete(0, tk.END)
        self.city_entry.focus_set()

    def set_unit(self, unit: str):
        """Switch temperature unit between 'C' and 'F'."""
        if self.current_unit == unit:
            return
        self.current_unit = unit

        if unit == "C":
            self.btn_celsius.config(bg=COLOR_PRIMARY, fg="white")
            self.btn_fahrenheit.config(bg="white", fg=COLOR_TEXT_MAIN)
        else:
            self.btn_celsius.config(bg="white", fg=COLOR_TEXT_MAIN)
            self.btn_fahrenheit.config(bg=COLOR_PRIMARY, fg="white")

        if self.current_data:
            self._render_weather_data(self.current_data)

    def trigger_search(self):
        """Triggered by Search button or Enter key."""
        city = self.city_entry.get().strip()
        if not city:
            messagebox.showwarning(
                "Input Warning",
                "Please enter a city name to search."
            )
            return
        self.search_city(city)

    def refresh_weather(self):
        """Refresh weather for currently viewed or entered city."""
        city = self.city_entry.get().strip()
        if not city and self.current_data:
            city = self.current_data.get("city", self.DEFAULT_CITY)
        if not city:
            city = self.DEFAULT_CITY
        self.search_city(city)

    def search_city(self, city_name: str):
        """
        Initiate asynchronous weather & forecast fetching for given city.
        Runs on background worker thread to prevent UI freezing.
        """
        if self.is_loading:
            return

        city_clean = city_name.strip()
        if not city_clean:
            return

        if self.city_entry.get().strip() != city_clean:
            self.city_entry.delete(0, tk.END)
            self.city_entry.insert(0, city_clean)

        self._set_loading_state(True, city_clean)

        worker = threading.Thread(
            target=self._fetch_weather_worker,
            args=(city_clean,),
            daemon=True
        )
        worker.start()

    def _safe_after(self, callback, *args):
        """Safely invoke callback on main thread if window still exists."""
        try:
            if self.root.winfo_exists():
                self.root.after(0, callback, *args)
        except (tk.TclError, RuntimeError):
            pass

    def _fetch_weather_worker(self, city_name: str):
        """Worker thread executing HTTP requests safely."""
        try:
            full_data = self.weather_service.fetch_full_weather(city_name)
            self._safe_after(self._on_fetch_success, full_data)

        except CityNotFoundError as err:
            self._safe_after(self._on_fetch_error, "City Not Found", str(err), COLOR_DANGER)
        except InvalidApiKeyError as err:
            self._safe_after(self._on_fetch_error, "API Key Error", str(err), COLOR_DANGER)
        except RateLimitExceededError as err:
            self._safe_after(self._on_fetch_error, "Rate Limit", str(err), COLOR_WARNING)
        except RequestTimeoutError as err:
            self._safe_after(self._on_fetch_error, "Timeout", str(err), COLOR_WARNING)
        except NetworkConnectionError as err:
            self._safe_after(self._on_fetch_error, "Connection Error", str(err), COLOR_DANGER)
        except WeatherServiceError as err:
            self._safe_after(self._on_fetch_error, "Weather Error", str(err), COLOR_DANGER)
        except Exception as err:
            self._safe_after(
                self._on_fetch_error,
                "Unexpected Error",
                f"An unexpected error occurred:\n{str(err)}",
                COLOR_DANGER
            )

    def _set_loading_state(self, loading: bool, city_name: str = ""):
        """Toggle UI elements during loading."""
        self.is_loading = loading
        if loading:
            self.btn_search.config(state="disabled", text="Searching...")
            self.btn_refresh.config(state="disabled")
            self.lbl_status.config(
                text=f"⏳ Fetching weather & forecast for '{city_name}'...",
                fg=COLOR_WARNING
            )
        else:
            self.btn_search.config(state="normal", text="Search")
            self.btn_refresh.config(state="normal")
            self.lbl_status.config(text="● Ready", fg=COLOR_SUCCESS)

    def _on_fetch_success(self, parsed_data: dict):
        """Invoked on the main thread when API data is received."""
        self._set_loading_state(False)
        self.current_data = parsed_data

        city_name = parsed_data["city"]
        if city_name in self.recent_cities:
            self.recent_cities.remove(city_name)
        self.recent_cities.insert(0, city_name)
        if len(self.recent_cities) > self.MAX_RECENT_CITIES:
            self.recent_cities.pop()
        self._render_chips()

        self._render_weather_data(parsed_data)

    def _on_fetch_error(self, title: str, message: str, status_color: str):
        """Invoked on the main thread when an error occurs."""
        self._set_loading_state(False)
        self.lbl_status.config(text=f"⚠️ {title}", fg=status_color)
        messagebox.showerror(title, message)

    def _render_weather_data(self, data: dict):
        """Render parsed weather dictionary into UI components."""
        is_metric = (self.current_unit == "C")
        unit_sym = "°C" if is_metric else "°F"

        # Current temperature values
        temp = data["temp_c"] if is_metric else WeatherService.c_to_f(data["temp_c"])
        feels = data["feels_like_c"] if is_metric else WeatherService.c_to_f(data["feels_like_c"])
        t_min = data["temp_min_c"] if is_metric else WeatherService.c_to_f(data["temp_min_c"])
        t_max = data["temp_max_c"] if is_metric else WeatherService.c_to_f(data["temp_max_c"])

        # Wind speed + compass direction
        compass = WeatherService.deg_to_compass(data.get("wind_deg"))
        compass_str = f" ({compass})" if compass else ""
        if is_metric:
            wind_str = f"{data['wind_speed_ms']:.1f} m/s{compass_str}"
        else:
            wind_str = f"{WeatherService.ms_to_mph(data['wind_speed_ms']):.1f} mph{compass_str}"

        # Visibility
        if data["visibility_km"] is not None:
            if is_metric:
                vis_str = f"{data['visibility_km']:.1f} km"
            else:
                vis_str = f"{(data['visibility_km'] * 0.621371):.1f} mi"
        else:
            vis_str = "N/A"

        # Dynamic Condition Theme
        theme = data.get("theme", {})
        accent_color = theme.get("accent", COLOR_PRIMARY)
        theme_name = theme.get("name", "Live")
        self.lbl_theme_pill.config(
            text=f"● {theme_name}",
            bg=theme.get("card_badge", COLOR_BADGE_BG),
            fg=theme.get("badge_fg", COLOR_PRIMARY)
        )

        # Weather Alert Banner
        alert = data.get("alert")
        if alert:
            self.alert_frame.pack(fill="x", padx=30, pady=(0, 8), before=self.hero_card)
            self.alert_frame.config(bg=alert.get("bg", "#FEF2F2"))
            self.lbl_alert_title.config(
                text=alert.get("title", "Weather Alert"),
                bg=alert.get("bg", "#FEF2F2"),
                fg=alert.get("color", COLOR_DANGER)
            )
            self.lbl_alert_msg.config(
                text=alert.get("message", ""),
                bg=alert.get("bg", "#FEF2F2")
            )
        else:
            self.alert_frame.pack_forget()

        # 1. Update Hero Card
        icon_code = data.get("icon_code", "01d")
        icon_img = self._get_icon_image(icon_code, small=False)

        if icon_img:
            self.lbl_icon.config(image=icon_img, text="")
        else:
            symbol = WeatherService.get_weather_symbol(data["condition_main"], icon_code)
            self.lbl_icon.config(image="", text=symbol)

        self.lbl_location.config(text=f"📍 {data['city']}, {data['country']}")
        self.lbl_time.config(text=f"Updated: {data['timestamp']}")
        self.lbl_temp.config(text=f"{temp:.1f} {unit_sym}", fg=accent_color)
        self.lbl_condition.config(text=data["condition_desc"])
        self.lbl_feels_like_pill.config(text=f"Feels like: {feels:.1f} {unit_sym}")
        self.lbl_temp_range_pill.config(
            text=f"Today's Min: {t_min:.1f} {unit_sym}  •  Max: {t_max:.1f} {unit_sym}"
        )

        # 2. Update 24-Hour Hourly Forecast
        hourly_list = data.get("hourly_24h", [])
        for i, h_card in enumerate(self.hourly_cards):
            if i < len(hourly_list):
                h_item = hourly_list[i]
                h_temp = h_item["temp_c"] if is_metric else WeatherService.c_to_f(h_item["temp_c"])
                h_icon_code = h_item.get("icon_code", "01d")
                h_img = self._get_icon_image(h_icon_code, small=True)

                h_card["time"].config(text=h_item["time_label"])
                if h_img:
                    h_card["icon"].config(image=h_img, text="")
                else:
                    h_sym = WeatherService.get_weather_symbol(h_item["condition_main"], h_icon_code)
                    h_card["icon"].config(image="", text=h_sym)

                h_card["temp"].config(text=f"{h_temp:.0f}°")
                pop = h_item.get("pop_percent", 0)
                h_card["pop"].config(text=f"💧 {pop}%" if pop > 0 else "")
            else:
                h_card["time"].config(text="--")
                h_card["icon"].config(image="", text="--")
                h_card["temp"].config(text="--")
                h_card["pop"].config(text="")

        # 3. Update Detail Cards
        self.card_humidity.config(text=f"{data['humidity']}%")
        self.card_wind.config(text=wind_str)
        self.card_pressure.config(text=f"{data['pressure']} hPa")
        self.card_visibility.config(text=vis_str)
        self.card_sunrise.config(text=data["sunrise"])
        self.card_sunset.config(text=data["sunset"])

        # 4. Update 5-Day Forecast Cards
        forecast_list = data.get("forecast", [])
        for i, card_widgets in enumerate(self.forecast_cards):
            if i < len(forecast_list):
                f_item = forecast_list[i]
                f_temp = f_item["temp_c"] if is_metric else WeatherService.c_to_f(f_item["temp_c"])
                f_min = f_item["temp_min_c"] if is_metric else WeatherService.c_to_f(f_item["temp_min_c"])
                f_max = f_item["temp_max_c"] if is_metric else WeatherService.c_to_f(f_item["temp_max_c"])

                f_icon_code = f_item.get("icon_code", "01d")
                f_icon_img = self._get_icon_image(f_icon_code, small=True)

                if f_icon_img:
                    card_widgets["icon"].config(image=f_icon_img, text="")
                else:
                    f_symbol = WeatherService.get_weather_symbol(f_item["condition_main"], f_icon_code)
                    card_widgets["icon"].config(image="", text=f_symbol)

                card_widgets["day"].config(text=f_item["day_label"])
                card_widgets["temp"].config(text=f"{f_temp:.1f} {unit_sym}")
                card_widgets["range"].config(text=f"{f_min:.0f}° / {f_max:.0f}°")
                card_widgets["desc"].config(text=f_item["condition_desc"])
                f_pop = f_item.get("pop_percent", 0)
                card_widgets["rain"].config(text=f"Rain: {f_pop}%" if f_pop > 0 else "")
            else:
                card_widgets["day"].config(text="--")
                card_widgets["icon"].config(image="", text="--")
                card_widgets["temp"].config(text="--")
                card_widgets["range"].config(text="--")
                card_widgets["desc"].config(text="--")
                card_widgets["rain"].config(text="")

        # 5. Update Status Bar
        self.lbl_last_updated.config(text=f"Last updated: {data['timestamp']}")


def main():
    """Application entry point."""
    root = tk.Tk()
    app = WeatherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
