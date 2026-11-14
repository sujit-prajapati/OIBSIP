"""
Secure Password & Passphrase Generator Desktop Application.

A professional desktop security tool built with Python and Tkinter featuring:
- Mode 1: Secure Random Password generator (`secrets`-based CSPRNG)
- Mode 2: Smart Personalized Passphrase Builder using an interactive TagInput
- Common RAM-only Session History window (max 500 entries, Last 5 / All filter)
- Honest strength estimation with predictable pattern detection

Internship Project:
    Oasis Infobyte Python Programming Internship (Task 3)
Author:
    Sujit Prajapati
"""

import math
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Optional
import pyperclip

from generator_core import (
    CURATED_WORDS,
    DEFAULT_LENGTH,
    DEFAULT_RANDOM_WORDS,
    DEFAULT_SYMBOLS,
    MAX_HISTORY_ENTRIES,
    MAX_RANDOM_WORDS,
    MIN_PASSPHRASE_ENTRIES,
    MIN_RANDOM_WORDS,
    SEPARATOR_OPTIONS,
    StrengthResult,
    build_character_groups,
    estimate_passphrase_strength,
    estimate_password_strength,
    estimate_random_passphrase_strength,
    generate_passphrase_batch,
    generate_password,
    generate_random_words_batch,
    parse_entries,
    validate_length,
    validate_quantity,
    validate_random_word_count,
)
from tag_input import TagInput

# ---------------------------------------------------------------------------
# UI Theme Colors (Modern Slate & Royal Blue Palette)
# ---------------------------------------------------------------------------
COLOR_BG = "#F8FAFC"             # Crisp cool slate background
COLOR_CARD_BG = "#FFFFFF"        # Pure white card surface
COLOR_CARD_BORDER = "#E2E8F0"    # Subtle Slate-200 border
COLOR_PRIMARY = "#2563EB"        # Royal Blue Primary
COLOR_PRIMARY_HOVER = "#1D4ED8"  # Darker hover blue
COLOR_PRIMARY_ACTIVE = "#1E40AF" # Deep active blue
COLOR_PRIMARY_LIGHT = "#EFF6FF"  # Soft ice blue for active cards / chips
COLOR_PRIMARY_BORDER = "#BFDBFE" # Refined border for active state
COLOR_INFO_BG = "#EFF6FF"        # Notice background
COLOR_INFO_BORDER = "#BFDBFE"    # Notice border
COLOR_INFO_TEXT = "#1E40AF"      # Notice text
COLOR_SUCCESS = "#16A34A"        # Forest Green (Strong / Copy)
COLOR_SUCCESS_HOVER = "#15803D"
COLOR_WARNING = "#D97706"        # Amber (Medium / Fair)
COLOR_WARNING_BG = "#FFFBEB"     # Amber advisory background
COLOR_WARNING_BORDER = "#FDE68A" # Amber advisory border
COLOR_WARNING_TEXT = "#92400E"   # Amber advisory text
COLOR_DANGER = "#DC2626"         # Crimson Red (Weak / Clear)
COLOR_DANGER_HOVER = "#B91C1C"
COLOR_TEXT_MAIN = "#0F172A"      # High contrast Slate Black
COLOR_TEXT_MUTED = "#64748B"     # Cool Gray Secondary
COLOR_TEXT_LABEL = "#334155"     # Darker form label text
COLOR_METER_BG = "#E2E8F0"       # Strength bar groove
COLOR_INPUT_BORDER = "#CBD5E1"   # Clean input border


def bind_button_hover(btn: tk.Button, normal_bg: str, hover_bg: str):
    """Attach smooth hover background highlighting to a Tkinter button."""
    def _on_enter(_e):
        try:
            if btn["state"] != "disabled":
                btn.config(bg=hover_bg)
        except tk.TclError:
            pass

    def _on_leave(_e):
        try:
            if btn["state"] != "disabled":
                btn.config(bg=normal_bg)
        except tk.TclError:
            pass

    btn.bind("<Enter>", _on_enter)
    btn.bind("<Leave>", _on_leave)


STRENGTH_COLORS: Dict[str, str] = {
    "Not Generated": COLOR_TEXT_MUTED,
    "Weak": COLOR_DANGER,
    "Fair": COLOR_WARNING,
    "Strong": "#059669",
    "Very Strong": COLOR_SUCCESS,
}


class PasswordGeneratorApp:
    """Main Application Controller for Secure Password & Passphrase Generator GUI."""

    DEFAULT_LENGTH = DEFAULT_LENGTH

    def __init__(self, root: tk.Tk):
        """Initialize the application window, state variables, and layout."""
        self.root = root
        self.root.title("Secure Password Generator - Oasis Infobyte")
        self.root.configure(bg=COLOR_BG)

        # Generation mode ("random" or "passphrase")
        self.generation_mode_var = tk.StringVar(value="random")

        # Random password control variables
        self.length_var = tk.IntVar(value=self.DEFAULT_LENGTH)
        self.uppercase_var = tk.BooleanVar(value=True)
        self.lowercase_var = tk.BooleanVar(value=True)
        self.numbers_var = tk.BooleanVar(value=True)
        self.symbols_var = tk.BooleanVar(value=True)
        self.exclude_ambiguous_var = tk.BooleanVar(value=False)
        self.custom_symbols_var = tk.StringVar(value=DEFAULT_SYMBOLS)

        # Passphrase options (source selector: "custom" or "random_words")
        self.passphrase_source_var = tk.StringVar(value="custom")
        self.random_word_count_var = tk.StringVar(value=str(DEFAULT_RANDOM_WORDS))
        self.separator_var = tk.StringVar(value="-")
        self.passphrase_capitalize_var = tk.BooleanVar(value=True)
        self.passphrase_numbers_var = tk.BooleanVar(value=False)
        self.passphrase_symbols_var = tk.BooleanVar(value=False)

        # Shared control variables
        self.batch_count_var = tk.StringVar(value="1")
        self.enable_history_var = tk.BooleanVar(value=True)
        self.password_var = tk.StringVar(value="")
        self.is_password_visible = tk.BooleanVar(value=True)

        # Non-blocking status timer IDs
        self._copy_status_after_id: Optional[str] = None
        self._hist_status_after_id: Optional[str] = None

        # In-memory session data (never stored permanently on disk)
        self.current_batch: List[str] = []
        self.current_batch_mode: str = "random"
        self.current_passphrase_source: str = "custom"
        self.current_random_word_count: int = DEFAULT_RANDOM_WORDS
        self.current_passphrase_entries: List[str] = []
        self.current_passphrase_flags = (False, False)
        self.password_history: List[str] = []
        self.history_modes: List[str] = []
        self.history_capped: bool = False
        self.batch_entry_widgets: List[tk.Entry] = []

        # Independent per-mode generated output storage & settings
        self.mode_batch_counts: Dict[str, str] = {
            "random": "1",
            "passphrase": "1",
        }
        self.mode_outputs: Dict[str, dict] = {
            "random": {
                "has_generated": False,
                "primary": "",
                "batch": [],
            },
            "passphrase": {
                "has_generated": False,
                "primary": "",
                "batch": [],
                "source": "custom",
                "random_word_count": DEFAULT_RANDOM_WORDS,
                "entries": [],
                "flags": (False, False),
            },
        }

        # Separate History window state (independent visibility, defaults to masked)
        self.history_window: Optional[tk.Toplevel] = None
        self.history_visible_var = tk.BooleanVar(value=False)
        self.history_filter_var = tk.StringVar(value="all")
        self.history_entry_widgets: List[tk.Entry] = []
        self.history_canvas: Optional[tk.Canvas] = None
        self.history_scroll_content: Optional[tk.Frame] = None
        self.history_window_id: Optional[int] = None
        self.lbl_hist_window_title: Optional[tk.Label] = None
        self.lbl_hist_window_count: Optional[tk.Label] = None
        self.lbl_hist_status: Optional[tk.Label] = None
        self.btn_hist_visibility: Optional[tk.Button] = None
        self.btn_hist_copy_all: Optional[tk.Button] = None
        self.btn_hist_clear: Optional[tk.Button] = None

        # Build UI layout
        self.create_widgets()
        self.fit_window_to_screen()

        # Global Enter shortcut (skipped when focus is inside TagInput entry or on a Button)
        self.root.bind("<Return>", self._on_return_shortcut)

        # Intercept window close to securely wipe RAM
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # -----------------------------------------------------------------------
    # GUI Construction
    # -----------------------------------------------------------------------
    def create_widgets(self):
        """Construct the complete user interface with modern card-based styling."""
        header_frame = tk.Frame(self.root, bg=COLOR_BG)
        header_frame.pack(fill="x", padx=20, pady=(4, 2))

        header_content = tk.Frame(header_frame, bg=COLOR_BG)
        header_content.pack(fill="x")

        # Security lock icon badge
        icon_badge = tk.Frame(
            header_content,
            bg="#EFF6FF",
            highlightbackground="#BFDBFE",
            highlightthickness=1,
            padx=7,
            pady=2,
        )
        icon_badge.pack(side="left", padx=(0, 8))

        tk.Label(
            icon_badge,
            text="🔐",
            font=("Segoe UI", 15),
            bg="#EFF6FF",
        ).pack()

        # Application Title and Subtitle
        titles_col = tk.Frame(header_content, bg=COLOR_BG)
        titles_col.pack(side="left", fill="x", expand=True)

        tk.Label(
            titles_col,
            text="Secure Password Generator",
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MAIN,
        ).pack(anchor="w")

        tk.Label(
            titles_col,
            text="Create secure passwords and memorable passphrases",
            font=("Segoe UI", 8),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        # Security Status Pill
        status_pill = tk.Frame(
            header_content,
            bg="#F1F5F9",
            highlightbackground="#E2E8F0",
            highlightthickness=1,
            padx=8,
            pady=2,
        )
        status_pill.pack(side="right")

        tk.Label(
            status_pill,
            text="●",
            font=("Segoe UI", 8),
            bg="#F1F5F9",
            fg=COLOR_SUCCESS,
        ).pack(side="left", padx=(0, 4))

        tk.Label(
            status_pill,
            text="CSPRNG Protected",
            font=("Segoe UI", 8, "bold"),
            bg="#F1F5F9",
            fg=COLOR_TEXT_LABEL,
        ).pack(side="left")

        # Subtle divider below header
        divider = tk.Frame(self.root, bg="#E2E8F0", height=1)
        divider.pack(fill="x", padx=20, pady=(0, 4))

        # Main Elevated Card Container
        main_card = tk.Frame(
            self.root,
            bg=COLOR_CARD_BG,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=16,
            pady=4,
        )
        main_card.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        # Mode Selection Segmented Cards
        mode_container = tk.Frame(main_card, bg=COLOR_CARD_BG)
        mode_container.pack(fill="x", pady=(0, 4))
        mode_container.columnconfigure(0, weight=1)
        mode_container.columnconfigure(1, weight=1)

        # Mode 1 Card: Secure Random Password
        self.card_mode_random = tk.Frame(
            mode_container,
            bg=COLOR_CARD_BG,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=10,
            pady=3,
            cursor="hand2",
        )
        self.card_mode_random.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.btn_mode_random = tk.Button(
            self.card_mode_random,
            text="🔐 Secure Random Password",
            command=lambda: self.switch_mode("random"),
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            anchor="w",
        )
        self.btn_mode_random.pack(fill="x")

        self.lbl_mode_random_sub = tk.Label(
            self.card_mode_random,
            text="Generate cryptographically random passwords.",
            font=("Segoe UI", 8),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED,
            anchor="w",
            cursor="hand2",
        )
        self.lbl_mode_random_sub.pack(fill="x", pady=(1, 0))

        # Mode 2 Card: Personalized Passphrase
        self.card_mode_passphrase = tk.Frame(
            mode_container,
            bg=COLOR_CARD_BG,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=10,
            pady=3,
            cursor="hand2",
        )
        self.card_mode_passphrase.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self.btn_mode_passphrase = tk.Button(
            self.card_mode_passphrase,
            text="💬 Personalized Passphrase",
            command=lambda: self.switch_mode("passphrase"),
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            anchor="w",
        )
        self.btn_mode_passphrase.pack(fill="x")

        self.lbl_mode_pass_sub = tk.Label(
            self.card_mode_passphrase,
            text="Create memorable combinations using words or random wordlists.",
            font=("Segoe UI", 8),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED,
            anchor="w",
            cursor="hand2",
        )
        self.lbl_mode_pass_sub.pack(fill="x", pady=(1, 0))

        # Click and hover bindings for card frames, buttons, and subtitles
        for w in (self.card_mode_random, self.btn_mode_random, self.lbl_mode_random_sub):
            w.bind("<Button-1>", lambda _e: self.switch_mode("random"))
            w.bind("<Enter>", lambda _e: self._on_mode_card_hover("random", True))
            w.bind("<Leave>", lambda _e: self._on_mode_card_hover("random", False))

        for w in (self.card_mode_passphrase, self.btn_mode_passphrase, self.lbl_mode_pass_sub):
            w.bind("<Button-1>", lambda _e: self.switch_mode("passphrase"))
            w.bind("<Enter>", lambda _e: self._on_mode_card_hover("passphrase", True))
            w.bind("<Leave>", lambda _e: self._on_mode_card_hover("passphrase", False))

        # Shared Top Configuration Toolbar (Quantity 1-50 & Reset Defaults)
        shared_row = tk.Frame(main_card, bg=COLOR_CARD_BG)
        shared_row.pack(fill="x", pady=(0, 3))

        qty_group = tk.Frame(shared_row, bg=COLOR_CARD_BG)
        qty_group.pack(side="left")

        tk.Label(
            qty_group,
            text="Quantity to Generate (1–50):",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MAIN,
        ).pack(side="left")

        vcmd_batch = (self.root.register(self._validate_quantity_input), "%P")
        self.spin_batch = tk.Spinbox(
            qty_group,
            from_=1,
            to=50,
            textvariable=self.batch_count_var,
            validate="key",
            validatecommand=vcmd_batch,
            width=5,
            font=("Segoe UI", 9),
            justify="center",
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightcolor=COLOR_PRIMARY,
            highlightbackground=COLOR_INPUT_BORDER,
        )
        self.spin_batch.pack(side="left", padx=(8, 0))

        self.btn_reset_defaults = tk.Button(
            shared_row,
            text="↺ Reset Defaults",
            command=self.reset_settings,
            font=("Segoe UI", 8),
            bg="#F1F5F9",
            fg=COLOR_TEXT_MUTED,
            relief="flat",
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=10,
            pady=2,
            cursor="hand2",
        )
        self.btn_reset_defaults.pack(side="right")
        bind_button_hover(self.btn_reset_defaults, "#F1F5F9", "#E2E8F0")

        # Mode-Specific Options Container
        self.options_container = tk.Frame(main_card, bg=COLOR_CARD_BG)
        self.options_container.pack(fill="x", pady=(0, 3))

        self._build_random_options_panel()
        self._build_passphrase_options_panel()

        # Action Buttons Row
        action_row = tk.Frame(main_card, bg=COLOR_CARD_BG)
        action_row.pack(fill="x", pady=(2, 3))

        self.btn_generate = tk.Button(
            action_row,
            text="⚡ Generate Password(s)",
            command=self.generate_passwords,
            font=("Segoe UI", 10, "bold"),
            bg=COLOR_PRIMARY,
            fg="white",
            activebackground=COLOR_PRIMARY_HOVER,
            activeforeground="white",
            relief="flat",
            padx=15,
            pady=4,
            cursor="hand2",
        )
        self.btn_generate.pack(side="left", padx=(0, 8))
        bind_button_hover(self.btn_generate, COLOR_PRIMARY, COLOR_PRIMARY_HOVER)

        self.btn_visibility = tk.Button(
            action_row,
            text="👁 Hide",
            command=self.toggle_password_visibility,
            font=("Segoe UI", 9),
            bg="#FFFFFF",
            fg=COLOR_TEXT_MAIN,
            activebackground="#F1F5F9",
            activeforeground=COLOR_TEXT_MAIN,
            relief="flat",
            highlightbackground=COLOR_INPUT_BORDER,
            highlightthickness=1,
            padx=10,
            pady=2,
            cursor="hand2",
        )
        self.btn_visibility.pack(side="left", padx=(0, 10))
        bind_button_hover(self.btn_visibility, "#FFFFFF", "#F1F5F9")

        self.lbl_copy_status = tk.Label(
            action_row,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_SUCCESS,
        )
        self.lbl_copy_status.pack(side="left")

        # Primary Output Display Card
        primary_box = tk.Frame(
            main_card,
            bg="#F8FAFC",
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=8,
            pady=3,
        )
        primary_box.pack(fill="x", pady=(0, 2))

        self.entry_password = tk.Entry(
            primary_box,
            textvariable=self.password_var,
            font=("Consolas", 12, "bold"),
            relief="flat",
            bg="#F8FAFC",
            fg=COLOR_TEXT_MAIN,
            readonlybackground="#F8FAFC",
            state="readonly",
        )
        self.entry_password.pack(side="left", fill="x", expand=True, padx=(4, 10))

        self.btn_copy_primary = tk.Button(
            primary_box,
            text="📋 Copy Primary",
            command=self.copy_primary_password,
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_SUCCESS,
            fg="white",
            activebackground=COLOR_SUCCESS_HOVER,
            activeforeground="white",
            disabledforeground="#94A3B8",
            relief="flat",
            padx=12,
            pady=2,
            cursor="hand2",
            state="disabled",
        )
        self.btn_copy_primary.pack(side="right")
        bind_button_hover(self.btn_copy_primary, COLOR_SUCCESS, COLOR_SUCCESS_HOVER)

        # Strength Meter Section
        meter_container = tk.Frame(main_card, bg=COLOR_CARD_BG)
        meter_container.pack(fill="x", pady=(0, 2))

        self.canvas_strength = tk.Canvas(
            meter_container,
            height=6,
            bg=COLOR_METER_BG,
            highlightthickness=0,
        )
        self.canvas_strength.pack(fill="x", pady=(0, 2))
        self.canvas_strength.bind("<Configure>", lambda _e: self._redraw_strength_bar())

        self.lbl_strength = tk.Label(
            meter_container,
            text="Password Strength: Not Generated",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED,
        )
        self.lbl_strength.pack(anchor="w")

        tk.Label(
            meter_container,
            text="Note: Strength is an estimate, not a security guarantee.",
            font=("Segoe UI", 7),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED,
        ).pack(anchor="w")

        # Batch Results Section
        batch_header = tk.Frame(main_card, bg=COLOR_CARD_BG)
        batch_header.pack(fill="x", pady=(0, 2))

        self.lbl_batch_title = tk.Label(
            batch_header,
            text="Generated Passwords (Count: 0):",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MAIN,
        )
        self.lbl_batch_title.pack(side="left")

        self.btn_copy_all = tk.Button(
            batch_header,
            text="📋 Copy All Passwords",
            command=self.copy_all_passwords,
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_PRIMARY,
            fg="white",
            activebackground=COLOR_PRIMARY_HOVER,
            activeforeground="white",
            disabledforeground="#94A3B8",
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            state="disabled",
        )
        self.btn_copy_all.pack(side="right")
        bind_button_hover(self.btn_copy_all, COLOR_PRIMARY, COLOR_PRIMARY_HOVER)

        # Ephemeral Memory Note (anchored to bottom of container)
        lbl_ephemeral = tk.Label(
            main_card,
            text="🔒 Ephemeral Memory: Passwords and custom words exist in RAM only and clear automatically on exit.",
            font=("Segoe UI", 7),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED,
        )
        lbl_ephemeral.pack(side="bottom", anchor="w")

        # Session History Bar (anchored directly above ephemeral note)
        history_bar = tk.Frame(
            main_card,
            bg="#F8FAFC",
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=8,
            pady=2,
        )
        history_bar.pack(side="bottom", fill="x", pady=(0, 2))

        tk.Label(
            history_bar,
            text="Session History:",
            font=("Segoe UI", 9, "bold"),
            bg="#F8FAFC",
            fg=COLOR_TEXT_MAIN,
        ).pack(side="left")

        tk.Checkbutton(
            history_bar,
            text="Save to History",
            variable=self.enable_history_var,
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            activebackground="#F8FAFC",
            selectcolor="white",
            fg=COLOR_TEXT_LABEL,
            cursor="hand2",
        ).pack(side="left", padx=(10, 0))

        self.btn_view_history = tk.Button(
            history_bar,
            text="🕒 View History",
            command=self.open_history_window,
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_PRIMARY,
            activebackground="#EFF6FF",
            activeforeground=COLOR_PRIMARY_HOVER,
            relief="flat",
            highlightbackground=COLOR_PRIMARY,
            highlightthickness=1,
            padx=10,
            pady=2,
            cursor="hand2",
        )
        self.btn_view_history.pack(side="right")
        bind_button_hover(self.btn_view_history, COLOR_CARD_BG, "#EFF6FF")

        self.lbl_history_count = tk.Label(
            history_bar,
            text="0 saved",
            font=("Segoe UI", 8, "bold"),
            bg="#E2E8F0",
            fg=COLOR_TEXT_MAIN,
            padx=8,
            pady=2,
        )
        self.lbl_history_count.pack(side="right", padx=(0, 8))

        self.batch_container = tk.Frame(
            main_card,
            bg="#F8FAFC",
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
        )
        self.batch_container.pack(fill="x", expand=False, pady=(0, 3))

        self.batch_canvas = tk.Canvas(
            self.batch_container,
            bg="#F8FAFC",
            height=28,
            highlightthickness=0,
        )
        self.batch_scrollbar = tk.Scrollbar(
            self.batch_container,
            orient="vertical",
            command=self.batch_canvas.yview,
        )
        self.batch_scroll_content = tk.Frame(self.batch_canvas, bg="#F8FAFC")

        self.batch_scroll_content.bind(
            "<Configure>",
            lambda _e: self.batch_canvas.configure(
                scrollregion=self.batch_canvas.bbox("all")
            ),
        )

        self.batch_window_id = self.batch_canvas.create_window(
            (0, 0), window=self.batch_scroll_content, anchor="nw"
        )
        self.batch_canvas.configure(yscrollcommand=self.batch_scrollbar.set)

        self.batch_canvas.bind(
            "<Configure>",
            lambda e: self.batch_canvas.itemconfig(self.batch_window_id, width=e.width),
        )

        self.root.bind("<MouseWheel>", self._on_main_mousewheel)

        self.batch_scrollbar.pack(side="right", fill="y")
        self.batch_canvas.pack(side="left", fill="both", expand=True)

        self._render_empty_batch_placeholder()

        self.switch_mode("random")

    def _build_random_options_panel(self):
        """Build options panel for Secure Random Password mode."""
        self.random_options_frame = tk.Frame(self.options_container, bg=COLOR_CARD_BG)

        # Length row
        len_row = tk.Frame(self.random_options_frame, bg=COLOR_CARD_BG)
        len_row.pack(fill="x", pady=(0, 5))

        tk.Label(
            len_row,
            text="Password Length (8–64):",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MAIN,
        ).pack(side="left")

        self.spin_length = tk.Spinbox(
            len_row,
            from_=8,
            to=64,
            textvariable=self.length_var,
            width=5,
            font=("Segoe UI", 9),
            justify="center",
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightcolor=COLOR_PRIMARY,
            highlightbackground=COLOR_INPUT_BORDER,
        )
        self.spin_length.pack(side="left", padx=(8, 0))

        # Checkboxes 2x2 grid
        options_grid = tk.Frame(self.random_options_frame, bg=COLOR_CARD_BG)
        options_grid.pack(fill="x", pady=(0, 4))
        options_grid.columnconfigure(0, weight=1, uniform="chk_col")
        options_grid.columnconfigure(1, weight=1, uniform="chk_col")

        checkboxes = [
            ("Uppercase Letters (A-Z)", self.uppercase_var),
            ("Lowercase Letters (a-z)", self.lowercase_var),
            ("Numbers (0-9)", self.numbers_var),
            ("Special Symbols", self.symbols_var),
        ]

        for index, (label_text, var) in enumerate(checkboxes):
            tk.Checkbutton(
                options_grid,
                text=label_text,
                variable=var,
                font=("Segoe UI", 9),
                bg=COLOR_CARD_BG,
                activebackground=COLOR_CARD_BG,
                selectcolor="white",
                fg=COLOR_TEXT_LABEL,
                cursor="hand2",
            ).grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 16), pady=2)

        # Exclude ambiguous row
        amb_row = tk.Frame(self.random_options_frame, bg=COLOR_CARD_BG)
        amb_row.pack(fill="x", pady=(2, 4))

        tk.Checkbutton(
            amb_row,
            text="Exclude Ambiguous Characters (0, O, 1, l, I, |)",
            variable=self.exclude_ambiguous_var,
            font=("Segoe UI", 9),
            bg=COLOR_CARD_BG,
            activebackground=COLOR_CARD_BG,
            selectcolor="white",
            fg=COLOR_TEXT_LABEL,
            cursor="hand2",
        ).pack(side="left")

        # Custom symbols row
        symbols_row = tk.Frame(self.random_options_frame, bg=COLOR_CARD_BG)
        symbols_row.pack(fill="x", pady=(2, 2))

        tk.Label(
            symbols_row,
            text="Custom Symbols:",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_LABEL,
        ).pack(side="left")

        self.entry_symbols = tk.Entry(
            symbols_row,
            textvariable=self.custom_symbols_var,
            font=("Consolas", 9),
            bg="white",
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightcolor=COLOR_PRIMARY,
            highlightbackground=COLOR_INPUT_BORDER,
        )
        self.entry_symbols.pack(side="left", fill="x", expand=True, padx=(8, 0))

    def _build_passphrase_options_panel(self):
        """Build options panel supporting Custom Words and Secure Random Words sources."""
        self.passphrase_options_frame = tk.Frame(
            self.options_container, bg=COLOR_CARD_BG
        )

        # Passphrase Source Selector Bar
        source_bar = tk.Frame(
            self.passphrase_options_frame,
            bg="#F8FAFC",
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=8,
            pady=2,
        )
        source_bar.pack(fill="x", pady=(0, 4))

        tk.Label(
            source_bar,
            text="Passphrase Source:",
            font=("Segoe UI", 9, "bold"),
            bg="#F8FAFC",
            fg=COLOR_TEXT_MAIN,
        ).pack(side="left", padx=(0, 10))

        for src_val, src_label in (
            ("custom", "✏ Custom Words"),
            ("random_words", "🎲 Secure Random Words"),
        ):
            tk.Radiobutton(
                source_bar,
                text=src_label,
                value=src_val,
                variable=self.passphrase_source_var,
                command=self._update_passphrase_source_ui,
                font=("Segoe UI", 9, "bold"),
                bg="#F8FAFC",
                activebackground="#F8FAFC",
                selectcolor="white",
                fg=COLOR_TEXT_MAIN,
                cursor="hand2",
            ).pack(side="left", padx=(0, 14))

        # Source-specific container
        self.passphrase_source_container = tk.Frame(
            self.passphrase_options_frame, bg=COLOR_CARD_BG
        )
        self.passphrase_source_container.pack(fill="x", pady=(0, 2))

        # Subpanel 1: Custom Words (TagInput + Security Advisory)
        self.custom_words_source_frame = tk.Frame(
            self.passphrase_source_container, bg=COLOR_CARD_BG
        )

        self.tag_input = TagInput(
            self.custom_words_source_frame,
            card_bg=COLOR_CARD_BG,
            border_color=COLOR_CARD_BORDER,
            text_main=COLOR_TEXT_MAIN,
            text_muted=COLOR_TEXT_MUTED,
            primary_color=COLOR_PRIMARY,
            danger_color=COLOR_DANGER,
            warning_color=COLOR_WARNING,
        )
        self.tag_input.pack(fill="x", pady=(0, 2))

        notice_box = tk.Frame(
            self.custom_words_source_frame,
            bg=COLOR_WARNING_BG,
            highlightbackground=COLOR_WARNING_BORDER,
            highlightthickness=1,
            padx=8,
            pady=3,
        )
        notice_box.pack(fill="x")

        lbl_notice = tk.Label(
            notice_box,
            text=(
                "⚠ Security Advisory: Never use real names, birthdays, phone numbers, or emails. "
                "Familiar words and predictable personal details do not make a strong password. "
                "Entries remain in RAM only and clear automatically when closed."
            ),
            font=("Segoe UI", 7),
            bg=COLOR_WARNING_BG,
            fg=COLOR_WARNING_TEXT,
            justify="left",
            wraplength=540,
        )
        lbl_notice.pack(anchor="w", fill="x")
        notice_box.bind(
            "<Configure>",
            lambda e: lbl_notice.config(wraplength=max(260, e.width - 24)),
        )

        # Subpanel 2: Secure Random Words (Curated Wordlist + 4-8 words selector)
        self.random_words_source_frame = tk.Frame(
            self.passphrase_source_container, bg=COLOR_CARD_BG
        )

        wc_row = tk.Frame(self.random_words_source_frame, bg=COLOR_CARD_BG)
        wc_row.pack(fill="x", pady=(0, 5))

        tk.Label(
            wc_row,
            text=f"Number of Words ({MIN_RANDOM_WORDS}–{MAX_RANDOM_WORDS}):",
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MAIN,
        ).pack(side="left")

        vcmd_rw = (self.root.register(self._validate_random_words_input), "%P")
        self.spin_random_words = tk.Spinbox(
            wc_row,
            from_=MIN_RANDOM_WORDS,
            to=MAX_RANDOM_WORDS,
            textvariable=self.random_word_count_var,
            validate="key",
            validatecommand=vcmd_rw,
            width=5,
            font=("Segoe UI", 9),
            justify="center",
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightcolor=COLOR_PRIMARY,
            highlightbackground=COLOR_INPUT_BORDER,
        )
        self.spin_random_words.pack(side="left", padx=(8, 12))

        tk.Label(
            wc_row,
            text="Selected independently using secrets.choice() (zero personal info)",
            font=("Segoe UI", 7),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED,
        ).pack(side="left")

        bits_per_word = math.log2(len(CURATED_WORDS))
        info_box = tk.Frame(
            self.random_words_source_frame,
            bg=COLOR_INFO_BG,
            highlightbackground=COLOR_INFO_BORDER,
            highlightthickness=1,
            padx=10,
            pady=5,
        )
        info_box.pack(fill="x")

        lbl_info = tk.Label(
            info_box,
            text=(
                f"ℹ Curated Wordlist Mode: Draws independent random words via Python secrets.choice() "
                f"from a {len(CURATED_WORDS):,}-word non-PII dictionary (~{bits_per_word:.1f} bits per word). "
                "Adding more words increases entropy exponentially."
            ),
            font=("Segoe UI", 7),
            bg=COLOR_INFO_BG,
            fg=COLOR_INFO_TEXT,
            justify="left",
            wraplength=540,
        )
        lbl_info.pack(anchor="w", fill="x")
        info_box.bind(
            "<Configure>",
            lambda e: lbl_info.config(wraplength=max(260, e.width - 24)),
        )

        # Settings Card (Separators & Enhancements)
        settings_box = tk.Frame(
            self.passphrase_options_frame,
            bg="#F8FAFC",
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=8,
            pady=3,
        )
        settings_box.pack(fill="x", pady=(2, 0))

        sep_row = tk.Frame(settings_box, bg="#F8FAFC")
        sep_row.pack(fill="x", pady=(0, 2))

        tk.Label(
            sep_row,
            text="Separator:",
            font=("Segoe UI", 9, "bold"),
            bg="#F8FAFC",
            fg=COLOR_TEXT_MAIN,
        ).pack(side="left", padx=(0, 8))

        for sep_val, sep_label in SEPARATOR_OPTIONS:
            tk.Radiobutton(
                sep_row,
                text=sep_label,
                value=sep_val,
                variable=self.separator_var,
                font=("Segoe UI", 9),
                bg="#F8FAFC",
                activebackground="#F8FAFC",
                selectcolor="white",
                fg=COLOR_TEXT_MAIN,
                cursor="hand2",
            ).pack(side="left", padx=(0, 10))

        enh_row = tk.Frame(settings_box, bg="#F8FAFC")
        enh_row.pack(fill="x")

        tk.Checkbutton(
            enh_row,
            text="Capitalize Words",
            variable=self.passphrase_capitalize_var,
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            activebackground="#F8FAFC",
            selectcolor="white",
            fg=COLOR_TEXT_LABEL,
            cursor="hand2",
        ).pack(side="left", padx=(0, 16))

        tk.Checkbutton(
            enh_row,
            text="Add Random Numbers",
            variable=self.passphrase_numbers_var,
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            activebackground="#F8FAFC",
            selectcolor="white",
            fg=COLOR_TEXT_LABEL,
            cursor="hand2",
        ).pack(side="left", padx=(0, 16))

        tk.Checkbutton(
            enh_row,
            text="Add Random Special Symbols",
            variable=self.passphrase_symbols_var,
            font=("Segoe UI", 9),
            bg="#F8FAFC",
            activebackground="#F8FAFC",
            selectcolor="white",
            fg=COLOR_TEXT_LABEL,
            cursor="hand2",
        ).pack(side="left")

        self._update_passphrase_source_ui()

    def _update_passphrase_source_ui(self):
        """Show controls for Custom Words or Secure Random Words while preserving input."""
        source = self.passphrase_source_var.get()
        if source == "random_words":
            self.custom_words_source_frame.pack_forget()
            self.random_words_source_frame.pack(fill="x")
        else:
            self.passphrase_source_var.set("custom")
            self.random_words_source_frame.pack_forget()
            self.custom_words_source_frame.pack(fill="x")

    def switch_mode(self, mode: str):
        """Switch between Secure Random Password mode and Personalized Passphrase mode."""
        if mode not in ("random", "passphrase"):
            mode = "random"

        old_mode = self.generation_mode_var.get()
        if hasattr(self, "mode_batch_counts") and old_mode in self.mode_batch_counts:
            try:
                self.mode_batch_counts[old_mode] = self.batch_count_var.get()
            except (AttributeError, tk.TclError):
                pass

        self.generation_mode_var.set(mode)
        if hasattr(self, "mode_batch_counts") and mode in self.mode_batch_counts:
            try:
                self.batch_count_var.set(self.mode_batch_counts[mode])
            except (AttributeError, tk.TclError):
                pass

        if mode == "random":
            self.passphrase_options_frame.pack_forget()
            self.random_options_frame.pack(fill="x")

            # Active Card: Random
            self.card_mode_random.config(
                bg=COLOR_PRIMARY_LIGHT,
                highlightbackground=COLOR_PRIMARY,
                highlightthickness=2,
            )
            self.btn_mode_random.config(
                bg=COLOR_PRIMARY_LIGHT,
                fg=COLOR_PRIMARY_ACTIVE,
                activebackground=COLOR_PRIMARY_LIGHT,
                activeforeground=COLOR_PRIMARY_ACTIVE,
            )
            self.lbl_mode_random_sub.config(
                bg=COLOR_PRIMARY_LIGHT,
                fg=COLOR_PRIMARY,
            )

            # Inactive Card: Passphrase
            self.card_mode_passphrase.config(
                bg=COLOR_CARD_BG,
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
            )
            self.btn_mode_passphrase.config(
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_MAIN,
                activebackground="#F8FAFC",
                activeforeground=COLOR_TEXT_MAIN,
            )
            self.lbl_mode_pass_sub.config(
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_MUTED,
            )
            self.btn_generate.config(text="⚡ Generate Password(s)")
            if hasattr(self, "btn_copy_all") and self.btn_copy_all.winfo_exists():
                self.btn_copy_all.config(text="📋 Copy All Passwords")
        else:
            self.random_options_frame.pack_forget()
            self.passphrase_options_frame.pack(fill="x")

            # Inactive Card: Random
            self.card_mode_random.config(
                bg=COLOR_CARD_BG,
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
            )
            self.btn_mode_random.config(
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_MAIN,
                activebackground="#F8FAFC",
                activeforeground=COLOR_TEXT_MAIN,
            )
            self.lbl_mode_random_sub.config(
                bg=COLOR_CARD_BG,
                fg=COLOR_TEXT_MUTED,
            )

            # Active Card: Passphrase
            self.card_mode_passphrase.config(
                bg=COLOR_PRIMARY_LIGHT,
                highlightbackground=COLOR_PRIMARY,
                highlightthickness=2,
            )
            self.btn_mode_passphrase.config(
                bg=COLOR_PRIMARY_LIGHT,
                fg=COLOR_PRIMARY_ACTIVE,
                activebackground=COLOR_PRIMARY_LIGHT,
                activeforeground=COLOR_PRIMARY_ACTIVE,
            )
            self.lbl_mode_pass_sub.config(
                bg=COLOR_PRIMARY_LIGHT,
                fg=COLOR_PRIMARY,
            )
            self.btn_generate.config(text="⚡ Generate Passphrase(s)")
            if hasattr(self, "btn_copy_all") and self.btn_copy_all.winfo_exists():
                self.btn_copy_all.config(text="📋 Copy All Passphrases")

        self._restore_mode_output(mode)

    def _restore_mode_output(self, mode: str):
        """Display only the results belonging to the selected mode, restoring its previous state."""
        if not hasattr(self, "mode_outputs"):
            return

        self._set_copy_status("", COLOR_SUCCESS, auto_clear=False)
        saved = self.mode_outputs.get(mode, {})
        has_generated = saved.get("has_generated", False)

        if not has_generated or not saved.get("batch"):
            self.current_batch = []
            self.current_batch_mode = mode
            if mode == "passphrase":
                self.current_passphrase_entries.clear()
            self.password_var.set("")
            self.lbl_strength.config(
                text="Password Strength: Not Generated", fg=COLOR_TEXT_MUTED
            )
            self.canvas_strength.delete("all")
            self._render_empty_batch_placeholder()
            self._update_copy_buttons_state()
            return

        self.current_batch = list(saved.get("batch", []))
        self.current_batch_mode = mode
        if mode == "passphrase":
            self.current_passphrase_source = saved.get("source", "custom")
            self.current_random_word_count = saved.get(
                "random_word_count", DEFAULT_RANDOM_WORDS
            )
            self.current_passphrase_entries = list(saved.get("entries", []))
            self.current_passphrase_flags = saved.get("flags", (False, False))
        else:
            self.current_passphrase_entries.clear()

        primary_item = saved.get("primary", "")
        self.password_var.set(primary_item)
        mask_char = "" if self.is_password_visible.get() else "●"
        if hasattr(self, "entry_password") and self.entry_password.winfo_exists():
            self.entry_password.config(show=mask_char)

        self.update_strength_display(primary_item)
        self._render_batch_results()
        self._update_copy_buttons_state()

    def _on_mode_card_hover(self, card_name: str, entering: bool):
        """Provide subtle tactile hover effect on inactive mode cards."""
        current_mode = self.generation_mode_var.get()
        if card_name == "random" and current_mode != "random":
            bg = "#F8FAFC" if entering else COLOR_CARD_BG
            border = "#CBD5E1" if entering else COLOR_CARD_BORDER
            self.card_mode_random.config(bg=bg, highlightbackground=border)
            self.btn_mode_random.config(bg=bg)
            self.lbl_mode_random_sub.config(bg=bg)
        elif card_name == "passphrase" and current_mode != "passphrase":
            bg = "#F8FAFC" if entering else COLOR_CARD_BG
            border = "#CBD5E1" if entering else COLOR_CARD_BORDER
            self.card_mode_passphrase.config(bg=bg, highlightbackground=border)
            self.btn_mode_passphrase.config(bg=bg)
            self.lbl_mode_pass_sub.config(bg=bg)

    # -----------------------------------------------------------------------
    # Window Dimensions, Shortcuts & Scroll Handling
    # -----------------------------------------------------------------------
    def fit_window_to_screen(self):
        """Size and center the window smoothly within current screen limits."""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        req_w = self.root.winfo_reqwidth()
        req_h = self.root.winfo_reqheight()

        width = min(max(740, req_w + 30), max(680, screen_width - 40))
        height = min(max(580, req_h + 16), max(560, screen_height - 60))

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2 - 12)

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(min(680, screen_width - 40), 540)

    def _on_return_shortcut(self, _event) -> None:
        """Trigger generation on Enter unless focused inside TagInput or interactive button."""
        try:
            focused = self.root.focus_get()
        except tk.TclError:
            focused = None
        if focused == self.tag_input.entry:
            return
        if isinstance(focused, (tk.Button, tk.Checkbutton, tk.Radiobutton)):
            return
        self.generate_passwords()

    def _on_main_mousewheel(self, event):
        """Scroll main batch canvas cleanly with mouse wheel or trackpad."""
        try:
            if self.current_batch and self.batch_canvas and self.batch_canvas.winfo_exists():
                delta = event.delta
                if delta == 0:
                    return
                units = int(-1 * (delta / 120))
                if units == 0:
                    units = -1 if delta > 0 else 1
                self.batch_canvas.yview_scroll(units, "units")
        except tk.TclError:
            pass

    @staticmethod
    def _validate_quantity_input(proposed_value: str) -> bool:
        """Allow empty during editing or integers strictly within 1..50."""
        if proposed_value == "":
            return True
        if not proposed_value.isdigit() or proposed_value.startswith("0"):
            return False
        return 1 <= int(proposed_value) <= 50

    @staticmethod
    def _validate_random_words_input(proposed_value: str) -> bool:
        """Allow empty during editing or integers strictly within 4..8."""
        if proposed_value == "":
            return True
        return proposed_value in {"4", "5", "6", "7", "8"}

    # Thin delegation wrappers keeping existing call points readable
    @staticmethod
    def validate_quantity(raw_value: object):
        return validate_quantity(raw_value)

    @staticmethod
    def parse_custom_words(raw_text: str) -> List[str]:
        return parse_entries(raw_text)

    @staticmethod
    def calculate_strength(password: str):
        res = estimate_password_strength(password)
        return (res.label, STRENGTH_COLORS.get(res.label, COLOR_TEXT_MUTED), res.fraction)

    # -----------------------------------------------------------------------
    # Inline Non-Blocking Status & Validation Failure Cleanup
    # -----------------------------------------------------------------------
    def _set_copy_status(self, message: str, color: str = COLOR_SUCCESS, auto_clear: bool = True):
        """Update inline status label on dashboard with optional 3-second auto-clear."""
        if self._copy_status_after_id is not None:
            try:
                self.root.after_cancel(self._copy_status_after_id)
            except tk.TclError:
                pass
            self._copy_status_after_id = None

        self.lbl_copy_status.config(text=message, fg=color)
        if auto_clear and message:
            self._copy_status_after_id = self.root.after(3000, self._clear_copy_status)

    def _clear_copy_status(self):
        self._copy_status_after_id = None
        try:
            if self.lbl_copy_status.winfo_exists():
                self.lbl_copy_status.config(text="")
        except tk.TclError:
            pass

    def _set_hist_status(self, message: str, color: str = COLOR_SUCCESS, auto_clear: bool = True):
        """Update inline status label inside History window without blocking popups."""
        if self._hist_status_after_id is not None:
            try:
                self.root.after_cancel(self._hist_status_after_id)
            except tk.TclError:
                pass
            self._hist_status_after_id = None

        if self.lbl_hist_status and self.lbl_hist_status.winfo_exists():
            self.lbl_hist_status.config(text=message, fg=color)
            if auto_clear and message:
                self._hist_status_after_id = self.root.after(3000, self._restore_hist_status)

    def _restore_hist_status(self):
        self._hist_status_after_id = None
        try:
            if self.lbl_hist_status and self.lbl_hist_status.winfo_exists():
                visible = self.history_visible_var.get()
                self.lbl_hist_status.config(
                    text=(
                        "⚠ Passwords are currently visible."
                        if visible
                        else "🔒 Passwords are masked by default for privacy."
                    ),
                    fg=COLOR_WARNING if visible else COLOR_TEXT_MUTED,
                )
        except tk.TclError:
            pass

    def _clear_output_on_validation_failure(self):
        """
        Clear stale generated output when validation fails so previous results
        cannot be mistaken for newly generated output. Leaves history untouched.
        """
        mode = self.generation_mode_var.get()
        if hasattr(self, "mode_outputs") and mode in self.mode_outputs:
            self.mode_outputs[mode] = {
                "has_generated": False,
                "primary": "",
                "batch": [],
                "source": "custom",
                "random_word_count": DEFAULT_RANDOM_WORDS,
                "entries": [],
                "flags": (False, False),
            }
        self.password_var.set("")
        self.current_batch.clear()
        self.current_passphrase_entries.clear()
        self._set_copy_status("", COLOR_SUCCESS, auto_clear=False)
        self.lbl_strength.config(
            text="Password Strength: Invalid Input", fg=COLOR_DANGER
        )
        self.canvas_strength.delete("all")
        self._render_empty_batch_placeholder()

    # -----------------------------------------------------------------------
    # Settings & Visibility Handlers
    # -----------------------------------------------------------------------
    def reset_settings(self):
        """Restore all parameters to recommended secure defaults and clear TagInput."""
        self.length_var.set(self.DEFAULT_LENGTH)
        self.uppercase_var.set(True)
        self.lowercase_var.set(True)
        self.numbers_var.set(True)
        self.symbols_var.set(True)
        self.exclude_ambiguous_var.set(False)
        self.custom_symbols_var.set(DEFAULT_SYMBOLS)

        self.passphrase_source_var.set("custom")
        self.random_word_count_var.set(str(DEFAULT_RANDOM_WORDS))
        self._update_passphrase_source_ui()

        self.tag_input.clear()
        self.separator_var.set("-")
        self.passphrase_capitalize_var.set(True)
        self.passphrase_numbers_var.set(False)
        self.passphrase_symbols_var.set(False)

        self.batch_count_var.set("1")
        self.enable_history_var.set(True)

        if hasattr(self, "mode_batch_counts"):
            self.mode_batch_counts["random"] = "1"
            self.mode_batch_counts["passphrase"] = "1"
        if hasattr(self, "mode_outputs"):
            self.mode_outputs["random"] = {
                "has_generated": False,
                "primary": "",
                "batch": [],
            }
            self.mode_outputs["passphrase"] = {
                "has_generated": False,
                "primary": "",
                "batch": [],
                "source": "custom",
                "random_word_count": DEFAULT_RANDOM_WORDS,
                "entries": [],
                "flags": (False, False),
            }

        self.password_var.set("")
        self._set_copy_status("", COLOR_SUCCESS, auto_clear=False)
        self.lbl_strength.config(
            text="Password Strength: Not Generated", fg=COLOR_TEXT_MUTED
        )
        self.canvas_strength.delete("all")

        self.current_batch.clear()
        self.current_passphrase_source = "custom"
        self.current_random_word_count = DEFAULT_RANDOM_WORDS
        self.current_passphrase_entries.clear()
        self._render_empty_batch_placeholder()

    def toggle_password_visibility(self):
        """Toggle plain text or masked display across main dashboard views only."""
        visible = not self.is_password_visible.get()
        self.is_password_visible.set(visible)

        mask_char = "" if visible else "●"
        self.btn_visibility.config(text="👁 Hide" if visible else "👁 Show")
        self.entry_password.config(show=mask_char)

        for entry in self.batch_entry_widgets:
            try:
                entry.config(show=mask_char)
            except tk.TclError:
                pass

    # -----------------------------------------------------------------------
    # Generation Dispatch (Delegated to generator_core)
    # -----------------------------------------------------------------------
    def get_character_groups(self) -> List[str]:
        """Build validated character pools for Random Password mode."""
        return build_character_groups(
            upper=self.uppercase_var.get(),
            lower=self.lowercase_var.get(),
            digits=self.numbers_var.get(),
            symbols_on=self.symbols_var.get(),
            custom_symbols=self.custom_symbols_var.get(),
            exclude_ambiguous=self.exclude_ambiguous_var.get(),
        )

    def generate_single_password(self, length: int, groups: List[str]) -> str:
        """Delegate single random password creation to generator_core."""
        return generate_password(length, groups)

    def generate_passwords(self):
        """Validate active mode inputs strictly and generate requested batch."""
        self._set_copy_status("", COLOR_SUCCESS, auto_clear=False)

        qty_ok, quantity, qty_err = validate_quantity(self.spin_batch.get())
        if not qty_ok or quantity is None:
            self._clear_output_on_validation_failure()
            messagebox.showerror("Invalid Quantity", qty_err)
            return

        mode = self.generation_mode_var.get()

        if mode == "passphrase":
            separator = self.separator_var.get()
            if separator not in ("-", "_", ".", " "):
                separator = "-"

            inc_caps = self.passphrase_capitalize_var.get()
            inc_nums = self.passphrase_numbers_var.get()
            inc_syms = self.passphrase_symbols_var.get()
            source = self.passphrase_source_var.get()

            if source == "random_words":
                rw_ok, word_count, rw_err = validate_random_word_count(
                    self.spin_random_words.get()
                )
                if not rw_ok or word_count is None:
                    self._clear_output_on_validation_failure()
                    messagebox.showerror("Invalid Word Count", rw_err)
                    return

                batch = generate_random_words_batch(
                    word_count=word_count,
                    separator=separator,
                    capitalize=inc_caps,
                    add_digits=inc_nums,
                    add_symbols=inc_syms,
                    quantity=quantity,
                )

                self.current_batch = list(batch.items)
                self.current_batch_mode = "passphrase"
                self.current_passphrase_source = "random_words"
                self.current_random_word_count = word_count
                self.current_passphrase_entries.clear()
                self.current_passphrase_flags = (inc_nums, inc_syms)
                history_label = "Passphrase"
            else:
                # Ensure a trailing fragment typed without a comma is committed first
                self.tag_input.commit_pending()
                entries = self.tag_input.get_entries()
                if len(entries) < MIN_PASSPHRASE_ENTRIES:
                    self._clear_output_on_validation_failure()
                    messagebox.showerror(
                        "Insufficient Entries",
                        f"Please add at least {MIN_PASSPHRASE_ENTRIES} distinct words or numbers "
                        f"(currently {len(entries)}).\nExample: Cricket, Mumbai, Coding, 41",
                    )
                    return

                batch = generate_passphrase_batch(
                    entries=entries,
                    separator=separator,
                    capitalize=inc_caps,
                    add_digits=inc_nums,
                    add_symbols=inc_syms,
                    quantity=quantity,
                )

                self.current_batch = list(batch.items)
                self.current_batch_mode = "passphrase"
                self.current_passphrase_source = "custom"
                self.current_passphrase_entries = list(entries)
                self.current_passphrase_flags = (inc_nums, inc_syms)
                history_label = "Passphrase"

            if batch.produced < batch.requested:
                self._set_copy_status(
                    f"Generated {batch.produced} of {batch.requested} unique",
                    color=COLOR_WARNING,
                    auto_clear=False,
                )
                messagebox.showinfo("Unique Combinations Limit", batch.limited_reason)
        else:
            len_ok, length, len_err = validate_length(self.spin_length.get())
            if not len_ok or length is None:
                self._clear_output_on_validation_failure()
                messagebox.showerror("Invalid Length", len_err)
                return

            try:
                groups = self.get_character_groups()
            except ValueError as err:
                self._clear_output_on_validation_failure()
                messagebox.showerror("Invalid Character Options", str(err))
                return

            generated_list = [generate_password(length, groups) for _ in range(quantity)]
            self.current_batch = generated_list
            self.current_batch_mode = "random"
            self.current_passphrase_entries.clear()
            history_label = "Random"

        primary_item = self.current_batch[0]
        self.password_var.set(primary_item)

        if hasattr(self, "mode_outputs"):
            if mode == "passphrase":
                self.mode_outputs["passphrase"] = {
                    "has_generated": True,
                    "primary": primary_item,
                    "batch": list(self.current_batch),
                    "source": self.current_passphrase_source,
                    "random_word_count": self.current_random_word_count,
                    "entries": list(self.current_passphrase_entries),
                    "flags": self.current_passphrase_flags,
                }
            else:
                self.mode_outputs["random"] = {
                    "has_generated": True,
                    "primary": primary_item,
                    "batch": list(self.current_batch),
                }
        if hasattr(self, "mode_batch_counts"):
            self.mode_batch_counts[mode] = str(quantity)

        self.update_strength_display(primary_item)
        self._render_batch_results()

        if self.enable_history_var.get():
            self._record_to_history(self.current_batch, history_label)

    # -----------------------------------------------------------------------
    # Batch Results Rendering
    # -----------------------------------------------------------------------
    def _update_copy_buttons_state(self):
        """Enable or disable Copy Primary and Copy All based on generated outputs."""
        has_primary = bool(self.password_var.get())
        has_batch = bool(self.current_batch)
        if hasattr(self, "btn_copy_primary") and self.btn_copy_primary.winfo_exists():
            self.btn_copy_primary.config(state="normal" if has_primary else "disabled")
        if hasattr(self, "btn_copy_all") and self.btn_copy_all.winfo_exists():
            self.btn_copy_all.config(state="normal" if has_batch else "disabled")

    def _render_empty_batch_placeholder(self):
        """Display compact placeholder state in batch results area."""
        for widget in self.batch_scroll_content.winfo_children():
            widget.destroy()

        self.batch_entry_widgets.clear()
        noun = (
            "Passphrases"
            if self.generation_mode_var.get() == "passphrase"
            else "Passwords"
        )
        self.lbl_batch_title.config(text=f"Generated {noun} (Count: 0):")

        if hasattr(self, "batch_container"):
            self.batch_container.pack_configure(fill="x", expand=False)
        self.batch_canvas.config(height=28)

        self._update_copy_buttons_state()

        tk.Label(
            self.batch_scroll_content,
            text="Generated results will appear here after clicking Generate.",
            font=("Segoe UI", 8, "italic"),
            bg="#F8FAFC",
            fg=COLOR_TEXT_MUTED,
            pady=4,
        ).pack()

        self.batch_scroll_content.update_idletasks()
        self.batch_canvas.configure(scrollregion=self.batch_canvas.bbox("all"))

    def _render_batch_results(self):
        """Render individual rows for every password/passphrase in the current batch."""
        for widget in self.batch_scroll_content.winfo_children():
            widget.destroy()

        self.batch_entry_widgets.clear()
        count = len(self.current_batch)
        noun = "Passphrases" if self.current_batch_mode == "passphrase" else "Passwords"
        self.lbl_batch_title.config(text=f"Generated {noun} (Count: {count}):")

        if hasattr(self, "batch_container"):
            if count <= 1:
                self.batch_container.pack_configure(fill="x", expand=False)
                self.batch_canvas.config(height=38)
            else:
                self.batch_container.pack_configure(fill="x", expand=False)
                self.batch_canvas.config(height=68)

        self._update_copy_buttons_state()

        mask_char = "" if self.is_password_visible.get() else "●"

        for idx, item in enumerate(self.current_batch):
            row_frame = tk.Frame(
                self.batch_scroll_content,
                bg="white",
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
                padx=6,
                pady=2,
            )
            row_frame.pack(fill="x", padx=4, pady=2)

            tk.Label(
                row_frame,
                text=f"#{idx + 1:02d}",
                font=("Segoe UI", 9, "bold"),
                width=4,
                bg="white",
                fg=COLOR_PRIMARY,
            ).pack(side="left")

            entry_row = tk.Entry(
                row_frame,
                font=("Consolas", 10),
                bg="white",
                relief="flat",
                bd=0,
                show=mask_char,
            )
            entry_row.insert(0, item)
            entry_row.config(state="readonly", readonlybackground="white")
            entry_row.pack(side="left", fill="x", expand=True, padx=(4, 6))
            self.batch_entry_widgets.append(entry_row)

            strength_res = self._evaluate_item_strength(item)
            tier_color = STRENGTH_COLORS.get(strength_res.label, COLOR_TEXT_MUTED)
            tk.Label(
                row_frame,
                text=f"[{strength_res.label}]",
                font=("Segoe UI", 8, "bold"),
                width=11,
                bg="white",
                fg=tier_color,
            ).pack(side="left", padx=(0, 6))

            btn_copy_row = tk.Button(
                row_frame,
                text="📋 Copy",
                command=lambda p=item, num=idx + 1: self.copy_single_password(p, num),
                font=("Segoe UI", 8),
                bg="#F1F5F9",
                fg=COLOR_TEXT_MAIN,
                activebackground="#E2E8F0",
                relief="flat",
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
                padx=8,
                pady=1,
                cursor="hand2",
            )
            btn_copy_row.pack(side="right")
            bind_button_hover(btn_copy_row, "#F1F5F9", "#E2E8F0")

        self.batch_scroll_content.update_idletasks()
        self.batch_canvas.configure(scrollregion=self.batch_canvas.bbox("all"))
        self.batch_canvas.yview_moveto(0.0)

    # -----------------------------------------------------------------------
    # Strength Display
    # -----------------------------------------------------------------------
    def _evaluate_item_strength(self, value: str) -> StrengthResult:
        """Compute active mode StrengthResult using honest pattern-aware models."""
        if self.current_batch_mode == "passphrase":
            has_nums, has_syms = self.current_passphrase_flags
            if self.current_passphrase_source == "random_words":
                return estimate_random_passphrase_strength(
                    word_count=self.current_random_word_count,
                    pool_size=len(CURATED_WORDS),
                    has_digits=has_nums,
                    has_symbols=has_syms,
                )
            if self.current_passphrase_entries:
                return estimate_passphrase_strength(
                    entries=self.current_passphrase_entries,
                    has_digits=has_nums,
                    has_symbols=has_syms,
                    sample_phrase=value,
                )
        return estimate_password_strength(value)

    def update_strength_display(self, password: str):
        """Update strength label and visual progress bar."""
        res = self._evaluate_item_strength(password)
        color = STRENGTH_COLORS.get(res.label, COLOR_TEXT_MUTED)

        if self.current_batch_mode == "passphrase":
            if self.current_passphrase_source == "random_words":
                label_text = (
                    f"Estimated Entropy: ~{res.bits:.1f} bits "
                    f"({res.label} — {self.current_random_word_count} words from "
                    f"{len(CURATED_WORDS):,}-word list)"
                )
            else:
                note_suffix = f" ({res.notes[0]})" if res.notes else ""
                label_text = (
                    f"Estimated strength: {res.label} (~{round(res.bits)} bits, "
                    f"assuming your words are known){note_suffix}"
                )
        else:
            note_suffix = f" ({res.notes[0]})" if res.notes else ""
            label_text = f"Password Strength: {res.label}{note_suffix}"

        self.lbl_strength.config(text=label_text, fg=color)

        self.canvas_strength.delete("all")
        width = self.canvas_strength.winfo_width()
        if width <= 1:
            width = 580

        fill_width = int(width * res.fraction)
        if fill_width > 0:
            self.canvas_strength.create_rectangle(
                0, 0, fill_width, 6, fill=color, outline=""
            )

    def _redraw_strength_bar(self):
        """Redraw active strength bar dynamically when the window or canvas resizes."""
        password = self.password_var.get()
        if password:
            res = self._evaluate_item_strength(password)
            color = STRENGTH_COLORS.get(res.label, COLOR_TEXT_MUTED)
            self.canvas_strength.delete("all")
            width = self.canvas_strength.winfo_width()
            if width <= 1:
                width = 580
            fill_width = int(width * res.fraction)
            if fill_width > 0:
                self.canvas_strength.create_rectangle(
                    0, 0, fill_width, 6, fill=color, outline=""
                )

    # -----------------------------------------------------------------------
    # Non-Blocking Clipboard Actions
    # -----------------------------------------------------------------------
    def _copy_to_clipboard(self, content: str, parent=None) -> bool:
        """Copy text using pyperclip with Tkinter native clipboard fallback."""
        target_parent = parent or self.root
        try:
            pyperclip.copy(content)
            return True
        except Exception:
            try:
                target_parent.clipboard_clear()
                target_parent.clipboard_append(content)
                target_parent.update()
                return True
            except Exception as err:
                messagebox.showerror(
                    "Copy Error",
                    f"Unable to copy to clipboard:\n{err}",
                    parent=target_parent,
                )
                return False

    def copy_primary_password(self):
        """Copy primary generated item without blocking success popups."""
        password = self.password_var.get()
        if not password:
            messagebox.showwarning(
                "No Password",
                "Please generate a password or passphrase first.",
            )
            return

        if self._copy_to_clipboard(password):
            self._set_copy_status("✓ Primary copied to clipboard!", COLOR_SUCCESS)

    def copy_single_password(self, password: str, number: int):
        """Copy a specific item from the generated batch inline."""
        if self._copy_to_clipboard(password):
            self._set_copy_status(f"✓ Item #{number:02d} copied to clipboard!", COLOR_SUCCESS)

    def copy_all_passwords(self):
        """Copy all items in the current batch separated by newlines."""
        if not self.current_batch:
            messagebox.showwarning("No Passwords", "No generated passwords to copy.")
            return

        combined_text = "\n".join(self.current_batch)
        count = len(self.current_batch)
        if self._copy_to_clipboard(combined_text):
            self._set_copy_status(f"✓ {count} items copied to clipboard!", COLOR_SUCCESS)

    # -----------------------------------------------------------------------
    # Ephemeral Session History (Bounded at MAX_HISTORY_ENTRIES = 500)
    # -----------------------------------------------------------------------
    def _record_to_history(self, items: List[str], mode_label: str):
        """Prepend every newly generated item and enforce MAX_HISTORY_ENTRIES."""
        while len(self.history_modes) < len(self.password_history):
            self.history_modes.append("Saved")

        for item in reversed(items):
            self.password_history.insert(0, item)
            self.history_modes.insert(0, mode_label)

        if len(self.password_history) > MAX_HISTORY_ENTRIES:
            self.password_history = self.password_history[:MAX_HISTORY_ENTRIES]
            self.history_modes = self.history_modes[:MAX_HISTORY_ENTRIES]
            self.history_capped = True

        self._update_history_count_label()
        self._refresh_history_window()

    def _update_history_count_label(self):
        """Update saved count badge on dashboard and History window header."""
        count = len(self.password_history)
        noun = "password" if count == 1 else "passwords"
        self.lbl_history_count.config(text=f"{count} saved")
        if self.history_window and self.history_window.winfo_exists():
            if self.lbl_hist_window_title:
                self.lbl_hist_window_title.config(
                    text=f"🕒 Session History ({count} {noun})"
                )
            if self.lbl_hist_window_count:
                cap_note = (
                    f" • Capped at newest {MAX_HISTORY_ENTRIES}"
                    if self.history_capped
                    else ""
                )
                self.lbl_hist_window_count.config(
                    text=f"Stored in RAM only • Automatically cleared on exit{cap_note}"
                )

    def open_history_window(self):
        """Open and refresh the separate RAM-only Session History window."""
        if self.history_window and self.history_window.winfo_exists():
            self._refresh_history_window()
            self.history_window.lift()
            self.history_window.focus_force()
            return

        # Default to masked on every open independently of main screen
        self.history_visible_var.set(False)

        win = tk.Toplevel(self.root)
        win.title("Session History - Secure Password Generator")
        win.configure(bg=COLOR_BG)
        self.history_window = win

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = min(700, screen_w - 60)
        h = min(550, screen_h - 80)
        x = max(0, (screen_w - w) // 2 + 25)
        y = max(0, (screen_h - h) // 2 + 18)
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.minsize(540, 380)

        win.protocol("WM_DELETE_WINDOW", self.close_history_window)
        win.bind("<Escape>", lambda _e: self.close_history_window())

        # Header
        header = tk.Frame(win, bg=COLOR_BG)
        header.pack(fill="x", padx=20, pady=(12, 8))

        title_col = tk.Frame(header, bg=COLOR_BG)
        title_col.pack(side="left", fill="x", expand=True)

        self.lbl_hist_window_title = tk.Label(
            title_col,
            text="🕒 Session History (0 passwords)",
            font=("Segoe UI", 13, "bold"),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MAIN,
        )
        self.lbl_hist_window_title.pack(anchor="w")

        self.lbl_hist_window_count = tk.Label(
            title_col,
            text="",
            font=("Segoe UI", 8),
            bg=COLOR_BG,
            fg=COLOR_TEXT_MUTED,
        )
        self.lbl_hist_window_count.pack(anchor="w")

        self.btn_hist_visibility = tk.Button(
            header,
            text="👁 Show Passwords",
            command=self.toggle_history_visibility,
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MAIN,
            relief="flat",
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.btn_hist_visibility.pack(side="right")
        bind_button_hover(self.btn_hist_visibility, COLOR_CARD_BG, "#EFF6FF")

        hist_card = tk.Frame(
            win,
            bg=COLOR_CARD_BG,
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=16,
            pady=10,
        )
        hist_card.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        # Status & Last 5 / All Filter Toolbar
        toolbar = tk.Frame(hist_card, bg=COLOR_CARD_BG)
        toolbar.pack(fill="x", pady=(0, 6))

        self.lbl_hist_status = tk.Label(
            toolbar,
            text="🔒 Passwords are masked by default for privacy.",
            font=("Segoe UI", 8),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED,
        )
        self.lbl_hist_status.pack(side="left")

        filter_box = tk.Frame(toolbar, bg=COLOR_CARD_BG)
        filter_box.pack(side="right")

        tk.Label(
            filter_box,
            text="Show:",
            font=("Segoe UI", 8, "bold"),
            bg=COLOR_CARD_BG,
            fg=COLOR_TEXT_MUTED,
        ).pack(side="left", padx=(0, 4))

        for val, label in (("all", "All"), ("last5", "Last 5")):
            tk.Radiobutton(
                filter_box,
                text=label,
                value=val,
                variable=self.history_filter_var,
                command=self._refresh_history_window,
                font=("Segoe UI", 8),
                bg=COLOR_CARD_BG,
                activebackground=COLOR_CARD_BG,
                selectcolor="white",
                cursor="hand2",
            ).pack(side="left", padx=(0, 6))

        # Scrollable List Area
        list_container = tk.Frame(
            hist_card,
            bg="#F8FAFC",
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
        )
        list_container.pack(fill="both", expand=True, pady=(0, 10))

        self.history_canvas = tk.Canvas(
            list_container,
            bg="#F8FAFC",
            highlightthickness=0,
        )
        hist_scrollbar = tk.Scrollbar(
            list_container,
            orient="vertical",
            command=self.history_canvas.yview,
        )
        self.history_scroll_content = tk.Frame(self.history_canvas, bg="#F8FAFC")

        self.history_scroll_content.bind(
            "<Configure>",
            lambda _e: self.history_canvas.configure(
                scrollregion=self.history_canvas.bbox("all")
            ),
        )

        self.history_window_id = self.history_canvas.create_window(
            (0, 0), window=self.history_scroll_content, anchor="nw"
        )
        self.history_canvas.configure(yscrollcommand=hist_scrollbar.set)

        self.history_canvas.bind(
            "<Configure>",
            lambda e: self.history_canvas.itemconfig(
                self.history_window_id, width=e.width
            ),
        )
        win.bind("<MouseWheel>", self._on_history_mousewheel)

        hist_scrollbar.pack(side="right", fill="y")
        self.history_canvas.pack(side="left", fill="both", expand=True)

        # Action Footer Bar
        footer_bar = tk.Frame(hist_card, bg=COLOR_CARD_BG)
        footer_bar.pack(fill="x")

        self.btn_hist_copy_all = tk.Button(
            footer_bar,
            text="📋 Copy All",
            command=self.copy_all_history,
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_PRIMARY,
            fg="white",
            activebackground=COLOR_PRIMARY_HOVER,
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
        )
        self.btn_hist_copy_all.pack(side="left", padx=(0, 8))
        bind_button_hover(self.btn_hist_copy_all, COLOR_PRIMARY, COLOR_PRIMARY_HOVER)

        self.btn_hist_clear = tk.Button(
            footer_bar,
            text="🗑 Clear History",
            command=lambda: self.clear_history(parent_window=win),
            font=("Segoe UI", 9, "bold"),
            bg=COLOR_DANGER,
            fg="white",
            activebackground=COLOR_DANGER_HOVER,
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
        )
        self.btn_hist_clear.pack(side="left")
        bind_button_hover(self.btn_hist_clear, COLOR_DANGER, COLOR_DANGER_HOVER)

        btn_hist_close = tk.Button(
            footer_bar,
            text="✕ Close",
            command=self.close_history_window,
            font=("Segoe UI", 9),
            bg="#F1F5F9",
            fg=COLOR_TEXT_MAIN,
            activebackground="#E2E8F0",
            relief="flat",
            highlightbackground=COLOR_CARD_BORDER,
            highlightthickness=1,
            padx=14,
            pady=5,
            cursor="hand2",
        )
        btn_hist_close.pack(side="right")
        bind_button_hover(btn_hist_close, "#F1F5F9", "#E2E8F0")

        self._update_history_count_label()
        self._refresh_history_window()

    def _on_history_mousewheel(self, event):
        """Scroll history window canvas independently."""
        try:
            if (
                self.history_canvas
                and self.password_history
                and self.history_canvas.winfo_exists()
            ):
                delta = event.delta
                if delta == 0:
                    return
                units = int(-1 * (delta / 120))
                if units == 0:
                    units = -1 if delta > 0 else 1
                self.history_canvas.yview_scroll(units, "units")
        except tk.TclError:
            pass

    def close_history_window(self):
        """Close the History window while preserving session history entries."""
        if self._hist_status_after_id is not None:
            try:
                self.root.after_cancel(self._hist_status_after_id)
            except tk.TclError:
                pass
            self._hist_status_after_id = None

        if self.history_window and self.history_window.winfo_exists():
            self.history_window.destroy()
        self.history_window = None
        self.history_entry_widgets.clear()
        self.history_canvas = None
        self.history_scroll_content = None
        self.lbl_hist_window_title = None
        self.lbl_hist_window_count = None
        self.lbl_hist_status = None
        self.btn_hist_visibility = None
        self.btn_hist_copy_all = None
        self.btn_hist_clear = None

    def toggle_history_visibility(self):
        """Toggle visibility inside History window independently from main screen."""
        visible = not self.history_visible_var.get()
        self.history_visible_var.set(visible)
        mask_char = "" if visible else "●"

        if self.btn_hist_visibility:
            self.btn_hist_visibility.config(
                text="👁 Hide Passwords" if visible else "👁 Show Passwords"
            )
        self._restore_hist_status()

        for entry in self.history_entry_widgets:
            try:
                entry.config(show=mask_char)
            except tk.TclError:
                pass

    def _get_displayed_history(self) -> List[str]:
        """Return entries matching the active History view filter (All or Last 5)."""
        if self.history_filter_var.get() == "last5":
            return self.password_history[:5]
        return self.password_history

    def _refresh_history_window(self):
        """Populate or refresh the rows inside the separate History window if open."""
        self._update_history_count_label()
        if not (self.history_window and self.history_window.winfo_exists()):
            return
        if not self.history_scroll_content:
            return

        for widget in self.history_scroll_content.winfo_children():
            widget.destroy()

        self.history_entry_widgets.clear()
        displayed = self._get_displayed_history()
        has_items = len(self.password_history) > 0

        if self.btn_hist_copy_all:
            self.btn_hist_copy_all.config(state="normal" if has_items else "disabled")
        if self.btn_hist_clear:
            self.btn_hist_clear.config(state="normal" if has_items else "disabled")

        if not has_items:
            tk.Label(
                self.history_scroll_content,
                text="No passwords or passphrases saved in this session yet.",
                font=("Segoe UI", 9, "italic"),
                bg="#F8FAFC",
                fg=COLOR_TEXT_MUTED,
                pady=40,
            ).pack()
            self.history_scroll_content.update_idletasks()
            if self.history_canvas:
                self.history_canvas.configure(
                    scrollregion=self.history_canvas.bbox("all")
                )
            return

        mask_char = "" if self.history_visible_var.get() else "●"

        for idx, pwd in enumerate(displayed):
            row = tk.Frame(
                self.history_scroll_content,
                bg="white",
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
                padx=6,
                pady=2,
            )
            row.pack(fill="x", padx=6, pady=2)

            tk.Label(
                row,
                text=f"#{idx + 1:02d}",
                font=("Segoe UI", 9, "bold"),
                width=5,
                bg="white",
                fg=COLOR_PRIMARY,
            ).pack(side="left")

            mode_tag = (
                self.history_modes[idx]
                if idx < len(self.history_modes)
                else "Saved"
            )
            tag_bg = "#EFF6FF" if mode_tag == "Passphrase" else "#F1F5F9"
            tag_fg = "#1D4ED8" if mode_tag == "Passphrase" else COLOR_TEXT_MAIN

            tk.Label(
                row,
                text=mode_tag,
                font=("Segoe UI", 8, "bold"),
                width=10,
                bg=tag_bg,
                fg=tag_fg,
                padx=4,
                pady=1,
            ).pack(side="left", padx=(0, 6))

            entry = tk.Entry(
                row,
                font=("Consolas", 10),
                bg="white",
                relief="flat",
                bd=0,
                show=mask_char,
            )
            entry.insert(0, pwd)
            entry.config(state="readonly", readonlybackground="white")
            entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
            self.history_entry_widgets.append(entry)

            btn_hist_copy = tk.Button(
                row,
                text="📋 Copy",
                command=lambda p=pwd, num=idx + 1: self.copy_history_item(p, num),
                font=("Segoe UI", 8),
                bg="#F1F5F9",
                fg=COLOR_TEXT_MAIN,
                activebackground="#E2E8F0",
                relief="flat",
                highlightbackground=COLOR_CARD_BORDER,
                highlightthickness=1,
                padx=8,
                pady=1,
                cursor="hand2",
            )
            btn_hist_copy.pack(side="right")
            bind_button_hover(btn_hist_copy, "#F1F5F9", "#E2E8F0")

        self.history_scroll_content.update_idletasks()
        if self.history_canvas:
            self.history_canvas.configure(
                scrollregion=self.history_canvas.bbox("all")
            )
            self.history_canvas.yview_moveto(0.0)

    def copy_history_item(self, password: str, number: int):
        """Copy an individual saved item using non-blocking inline status feedback."""
        parent = (
            self.history_window
            if self.history_window and self.history_window.winfo_exists()
            else self.root
        )
        if self._copy_to_clipboard(password, parent=parent):
            self._set_hist_status(f"✓ Item #{number} copied to clipboard!", COLOR_SUCCESS)

    def copy_all_history(self):
        """Copy all saved (or Last 5 filtered) session entries separated by newlines."""
        parent = (
            self.history_window
            if self.history_window and self.history_window.winfo_exists()
            else self.root
        )
        items_to_copy = self._get_displayed_history()
        if not items_to_copy:
            messagebox.showwarning(
                "History Empty",
                "There are no saved passwords to copy.",
                parent=parent,
            )
            return

        combined = "\n".join(items_to_copy)
        count = len(items_to_copy)
        if self._copy_to_clipboard(combined, parent=parent):
            self._set_hist_status(f"✓ Copied {count} history entries!", COLOR_SUCCESS)

    def clear_history(self, parent_window=None):
        """Clear temporary password history after explicit user confirmation."""
        parent = parent_window or self.root
        if not self.password_history:
            messagebox.showinfo(
                "History Empty",
                "There is no password history to clear.",
                parent=parent,
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Clear History",
            "Are you sure you want to clear your session password history?\n"
            "This action cannot be undone.",
            parent=parent,
        )

        if confirm:
            self.password_history.clear()
            self.history_modes.clear()
            self.history_capped = False
            self._refresh_history_window()
            self._set_copy_status("", COLOR_SUCCESS, auto_clear=False)
            self._set_hist_status("✓ Session history cleared.", COLOR_SUCCESS)

    def on_close(self):
        """Purge all sensitive memory, TagInput entries, and timers upon exit."""
        if self._copy_status_after_id is not None:
            try:
                self.root.after_cancel(self._copy_status_after_id)
            except tk.TclError:
                pass
            self._copy_status_after_id = None

        self.password_history.clear()
        self.history_modes.clear()
        self.history_capped = False
        self.current_batch.clear()
        self.current_passphrase_entries.clear()
        self.password_var.set("")
        if hasattr(self, "mode_outputs"):
            self.mode_outputs.clear()
        try:
            self.tag_input.clear()
        except tk.TclError:
            pass
        self.close_history_window()
        self.root.destroy()


def main():
    """Application entry point."""
    root = tk.Tk()
    PasswordGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
