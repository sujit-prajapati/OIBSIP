"""
Interactive comma-aware Tag/Chip Input widget built purely with Tkinter.

Allows users to type or paste comma-separated words and numbers on a single line,
automatically turning committed entries into removable wrapped chips with inline
duplicate/length/limit feedback and strictly RAM-only storage.
"""

import re
import tkinter as tk
from typing import Callable, List, Optional, Tuple

from generator_core import MAX_ENTRIES, MAX_ENTRY_LENGTH

TAG_BG = "#EFF6FF"
TAG_BORDER = "#BFDBFE"
TAG_TEXT = "#1D4ED8"
TAG_CLOSE_HOVER = "#DC2626"
PLACEHOLDER_TEXT = "Type entries separated by commas..."


class TagInput(tk.Frame):
    """Reusable Tkinter Frame providing a comma-splitting wrapping tag/chip input."""

    def __init__(
        self,
        master: tk.Misc,
        on_change: Optional[Callable[[], None]] = None,
        card_bg: str = "#FFFFFF",
        border_color: str = "#E2E8F0",
        text_main: str = "#0F172A",
        text_muted: str = "#64748B",
        primary_color: str = "#2563EB",
        danger_color: str = "#DC2626",
        warning_color: str = "#D97706",
    ):
        super().__init__(master, bg=card_bg)
        self._on_change = on_change
        self._card_bg = card_bg
        self._border_color = border_color
        self._text_main = text_main
        self._text_muted = text_muted
        self._primary_color = primary_color
        self._danger_color = danger_color
        self._warning_color = warning_color

        self._entries: List[str] = []
        self._seen_lower = set()
        self._placeholder_active = False
        self._status_after_id: Optional[str] = None
        self._chip_frames: List[tk.Frame] = []

        self._build_ui()
        self._show_placeholder()
        self._update_counter()
        self._rebuild_chips()

    def _build_ui(self) -> None:
        """Construct the header, single-line entry, status line, and wrapping chip box."""
        top_row = tk.Frame(self, bg=self._card_bg)
        top_row.pack(fill="x", pady=(0, 2))

        tk.Label(
            top_row,
            text="Add Your Words & Numbers:",
            font=("Segoe UI", 9, "bold"),
            bg=self._card_bg,
            fg=self._text_main,
        ).pack(side="left")

        self.btn_clear_all = tk.Button(
            top_row,
            text="Clear All",
            command=self.clear,
            font=("Segoe UI", 8),
            bg="#F1F5F9",
            fg=self._text_muted,
            activebackground="#E2E8F0",
            relief="flat",
            highlightbackground="#E2E8F0",
            highlightthickness=1,
            padx=8,
            pady=1,
            cursor="hand2",
        )
        self.btn_clear_all.pack(side="right")
        self.btn_clear_all.bind("<Enter>", lambda _e: self.btn_clear_all.config(bg="#E2E8F0"))
        self.btn_clear_all.bind("<Leave>", lambda _e: self.btn_clear_all.config(bg="#F1F5F9"))

        self.lbl_counter = tk.Label(
            top_row,
            text="0 entries added (minimum 2 required)",
            font=("Segoe UI", 8, "bold"),
            bg=self._card_bg,
            fg=self._primary_color,
        )
        self.lbl_counter.pack(side="right", padx=(0, 10))

        # Single-line interactive input box
        self.entry_shell = tk.Frame(
            self,
            bg="white",
            highlightbackground="#CBD5E1",
            highlightthickness=1,
            padx=8,
            pady=2,
        )
        self.entry_shell.pack(fill="x", pady=(0, 2))

        self.entry = tk.Entry(
            self.entry_shell,
            font=("Segoe UI", 9),
            bg="white",
            fg=self._text_main,
            relief="flat",
            bd=0,
        )
        self.entry.pack(fill="x", expand=True)

        self.entry.bind("<FocusIn>", self._handle_focus_in)
        self.entry.bind("<FocusOut>", self._handle_focus_out)
        self.entry.bind("<KeyRelease>", self._handle_key_release)
        self.entry.bind("<Return>", self._handle_return)
        self.entry.bind("<BackSpace>", self._handle_backspace)
        self.entry.bind("<<Paste>>", self._handle_paste_event)

        # Inline status message (duplicates / char length / max count)
        self.lbl_status = tk.Label(
            self,
            text="Example: Cricket, Mumbai, Coding, 41, Success, 2026",
            font=("Segoe UI", 7),
            bg=self._card_bg,
            fg=self._text_muted,
            anchor="w",
        )
        self.lbl_status.pack(fill="x", pady=(0, 2))

        # Wrapping, bounded-height scrollable container for removable chips
        chip_shell = tk.Frame(
            self,
            bg="#F8FAFC",
            highlightbackground=self._border_color,
            highlightthickness=1,
        )
        chip_shell.pack(fill="x", pady=(0, 2))

        self.chip_text = tk.Text(
            chip_shell,
            height=2,
            wrap="word",
            bg="#F8FAFC",
            fg=self._text_muted,
            relief="flat",
            bd=3,
            cursor="arrow",
            state="disabled",
            takefocus=0,
        )
        self.chip_scroll = tk.Scrollbar(
            chip_shell,
            orient="vertical",
            command=self.chip_text.yview,
        )
        self.chip_text.configure(yscrollcommand=self.chip_scroll.set)
        self.chip_scroll.pack(side="right", fill="y")
        self.chip_text.pack(side="left", fill="both", expand=True)

    # -----------------------------------------------------------------------
    # Placeholder & Status Helpers
    # -----------------------------------------------------------------------
    def _show_placeholder(self) -> None:
        """Render muted placeholder text without storing it as content."""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, PLACEHOLDER_TEXT)
        self.entry.config(fg=self._text_muted)
        self._placeholder_active = True

    def _hide_placeholder(self) -> None:
        """Clear placeholder text when the user begins interacting."""
        if self._placeholder_active:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=self._text_main)
            self._placeholder_active = False

    def _set_status(self, message: str, color: Optional[str] = None, auto_clear: bool = True) -> None:
        """Show inline validation feedback without blocking popups."""
        if self._status_after_id is not None:
            try:
                self.after_cancel(self._status_after_id)
            except tk.TclError:
                pass
            self._status_after_id = None

        self.lbl_status.config(
            text=message,
            fg=color or self._warning_color,
        )
        if auto_clear:
            self._status_after_id = self.after(3200, self._reset_status_default)

    def _reset_status_default(self) -> None:
        """Restore subtle helper caption when inline feedback expires."""
        self._status_after_id = None
        try:
            if self.winfo_exists():
                self.lbl_status.config(
                    text="Example: Cricket, Mumbai, Coding, 41, Success, 2026",
                    fg=self._text_muted,
                )
        except tk.TclError:
            pass

    def _update_counter(self) -> None:
        """Update live entry counter and minimum-2 hint."""
        count = len(self._entries)
        noun = "entry" if count == 1 else "entries"
        color = self._primary_color if count >= 2 else self._text_muted
        self.lbl_counter.config(
            text=f"{count} {noun} added (minimum 2 required)",
            fg=color,
        )

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------
    def get_entries(self) -> List[str]:
        """Return a copy of the currently committed custom entries."""
        return list(self._entries)

    def add_from_text(self, raw_text: str) -> Tuple[List[str], List[str]]:
        """
        Parse raw comma/newline-separated text and add valid unique entries.

        Returns `(added_entries, rejected_messages)`.
        """
        added: List[str] = []
        rejected: List[str] = []

        for raw_token in re.split(r"[,\r\n]+", raw_text or ""):
            cleaned = " ".join(raw_token.split())
            if not cleaned:
                continue

            if len(cleaned) > MAX_ENTRY_LENGTH:
                rejected.append(
                    f"'{cleaned[:16]}...' exceeds {MAX_ENTRY_LENGTH} characters"
                )
                continue

            if len(self._entries) >= MAX_ENTRIES:
                rejected.append(f"Maximum {MAX_ENTRIES} entries limit reached")
                break

            key = cleaned.lower()
            if key in self._seen_lower:
                rejected.append(f"'{cleaned}' is already added")
                continue

            self._seen_lower.add(key)
            self._entries.append(cleaned)
            added.append(cleaned)

        if added:
            self._update_counter()
            self._rebuild_chips()
            if self._on_change:
                self._on_change()

        if rejected:
            self._set_status(rejected[0], color=self._warning_color, auto_clear=True)
        elif added:
            self._reset_status_default()

        return (added, rejected)

    def remove_at(self, index: int) -> None:
        """Remove a single chip by index."""
        if 0 <= index < len(self._entries):
            removed = self._entries.pop(index)
            self._seen_lower.discard(removed.lower())
            self._update_counter()
            self._rebuild_chips()
            self._reset_status_default()
            if self._on_change:
                self._on_change()

    def clear(self) -> None:
        """Remove all committed chips and clear pending input text."""
        self._entries.clear()
        self._seen_lower.clear()
        self._placeholder_active = False
        self.entry.delete(0, tk.END)
        try:
            has_focus = self.focus_get() == self.entry
        except tk.TclError:
            has_focus = False
        if not has_focus:
            self._show_placeholder()
        else:
            self.entry.config(fg=self._text_main)
        self._update_counter()
        self._rebuild_chips()
        self._reset_status_default()
        if self._on_change:
            self._on_change()

    def commit_pending(self) -> None:
        """Commit any pending non-placeholder text currently in the single-line entry."""
        if self._placeholder_active:
            return
        pending = self.entry.get()
        self.entry.delete(0, tk.END)
        if pending.strip():
            self.add_from_text(pending)

    # -----------------------------------------------------------------------
    # Event Handlers
    # -----------------------------------------------------------------------
    def _handle_focus_in(self, _event) -> None:
        try:
            self.entry_shell.config(highlightbackground=self._primary_color, highlightthickness=1)
        except tk.TclError:
            pass
        self._hide_placeholder()

    def _handle_focus_out(self, _event) -> None:
        try:
            self.entry_shell.config(highlightbackground="#CBD5E1", highlightthickness=1)
        except tk.TclError:
            pass
        if not self._placeholder_active:
            if self.entry.get().strip():
                self.commit_pending()
            if not self.entry.get():
                self._show_placeholder()

    def _handle_return(self, _event) -> str:
        self.commit_pending()
        return "break"

    def _handle_backspace(self, _event) -> Optional[str]:
        if not self._placeholder_active and self.entry.get() == "" and self._entries:
            self.remove_at(len(self._entries) - 1)
            return "break"
        return None

    def _handle_key_release(self, _event) -> None:
        if self._placeholder_active:
            return
        current = self.entry.get()
        if "," in current:
            completed, trailing = current.rsplit(",", 1)
            self.entry.delete(0, tk.END)
            cleaned_trailing = trailing.lstrip()
            if cleaned_trailing:
                self.entry.insert(0, cleaned_trailing)
            if completed.strip():
                self.add_from_text(completed)

    def _handle_paste_event(self, _event) -> None:
        """Convert pasted comma/newline-separated text into chips once paste lands."""
        self._hide_placeholder()
        self.after_idle(self._process_pasted_content)

    def _process_pasted_content(self) -> None:
        """Process text inserted by <<Paste>> and create chips immediately."""
        if self._placeholder_active:
            return
        current = self.entry.get()
        if "," in current or "\n" in current or "\r" in current:
            self.entry.delete(0, tk.END)
            self.add_from_text(current)

    # -----------------------------------------------------------------------
    # Chip Rendering (Wrapped Flow Inside Bounded Scrollable Text Widget)
    # -----------------------------------------------------------------------
    def _rebuild_chips(self) -> None:
        """Render wrapped pill chips for every committed entry."""
        for frame in self._chip_frames:
            try:
                frame.destroy()
            except tk.TclError:
                pass
        self._chip_frames.clear()

        self.chip_text.config(state="normal")
        self.chip_text.delete("1.0", tk.END)

        if not self._entries:
            self.chip_text.insert(
                "1.0",
                "No entries yet — type words or numbers separated by commas above.",
            )
            self.chip_text.config(fg=self._text_muted, state="disabled")
            return

        for idx, text_val in enumerate(self._entries):
            chip = tk.Frame(
                self.chip_text,
                bg=TAG_BG,
                highlightbackground=TAG_BORDER,
                highlightthickness=1,
                padx=8,
                pady=2,
            )
            lbl = tk.Label(
                chip,
                text=text_val,
                font=("Segoe UI", 8, "bold"),
                bg=TAG_BG,
                fg=TAG_TEXT,
            )
            lbl.pack(side="left", padx=(0, 4))

            btn_x = tk.Label(
                chip,
                text="✕",
                font=("Segoe UI", 8, "bold"),
                bg=TAG_BG,
                fg=TAG_TEXT,
                cursor="hand2",
            )
            btn_x.pack(side="left", padx=(2, 0))
            btn_x.bind("<Button-1>", lambda _e, i=idx: self.remove_at(i))
            btn_x.bind("<Enter>", lambda _e, w=btn_x: w.config(fg=TAG_CLOSE_HOVER))
            btn_x.bind("<Leave>", lambda _e, w=btn_x: w.config(fg=TAG_TEXT))

            self._chip_frames.append(chip)
            self.chip_text.window_create(tk.END, window=chip, padx=3, pady=3)
            # Trailing space allows tk.Text word-wrapping cleanly between chips
            self.chip_text.insert(tk.END, " ")

        self.chip_text.see(tk.END)
        self.chip_text.config(state="disabled")

