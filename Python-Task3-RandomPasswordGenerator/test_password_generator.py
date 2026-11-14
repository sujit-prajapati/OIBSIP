"""Automated unit and GUI integration test suite for Secure Password & Passphrase Generator."""

import tkinter as tk
import unittest
from unittest.mock import patch

from generator_core import (
    AMBIGUOUS_CHARS,
    DEFAULT_SYMBOLS,
    MAX_HISTORY_ENTRIES,
    PASSPHRASE_SYMBOLS,
)
from main import PasswordGeneratorApp
from tag_input import PLACEHOLDER_TEXT


class TestSecurePasswordGenerator(unittest.TestCase):
    """GUI and integration tests for Mode 1, Mode 2 (TagInput), and Common History."""

    def setUp(self) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = PasswordGeneratorApp(self.root)
        self.root.update_idletasks()

    def tearDown(self) -> None:
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Section A: Mode 1 — Secure Random Password
    # ------------------------------------------------------------------

    def test_a01_random_mode_lengths(self) -> None:
        """Test random mode lengths 8, 12, 16, 32, and 64."""
        for length in (8, 12, 16, 32, 64):
            self.app.length_var.set(length)
            self.app.batch_count_var.set("1")
            self.app.generate_passwords()
            pwd = self.app.password_var.get()
            self.assertEqual(len(pwd), length)
            self.assertEqual(len(self.app.current_batch), 1)

    def test_a02_character_categories_respected(self) -> None:
        """Verify Uppercase, Lowercase, Numbers, Special Symbols options."""
        self.app.length_var.set(20)
        self.app.uppercase_var.set(True)
        self.app.lowercase_var.set(True)
        self.app.numbers_var.set(True)
        self.app.symbols_var.set(True)
        self.app.batch_count_var.set("5")
        self.app.generate_passwords()

        for pwd in self.app.current_batch:
            self.assertTrue(any(c.isupper() for c in pwd))
            self.assertTrue(any(c.islower() for c in pwd))
            self.assertTrue(any(c.isdigit() for c in pwd))
            self.assertTrue(any(c in DEFAULT_SYMBOLS for c in pwd))

    def test_a03_minimum_two_categories_and_custom_symbol_errors(self) -> None:
        """Bugs B1–B4: Reject <2 categories, empty custom symbols, bad custom symbols, ambiguous-only."""
        history_before = len(self.app.password_history)

        # Single category only -> rejected cleanly
        self.app.uppercase_var.set(False)
        self.app.lowercase_var.set(False)
        self.app.numbers_var.set(True)
        self.app.symbols_var.set(False)
        with patch("main.messagebox.showerror") as mock_err:
            self.app.generate_passwords()
            mock_err.assert_called_once()
        self.assertEqual(self.app.password_var.get(), "")
        self.assertEqual(self.app.current_batch, [])
        self.assertEqual(len(self.app.password_history), history_before)

        # Two categories with Symbols enabled + empty custom symbols -> rejected (B1)
        self.app.symbols_var.set(True)
        self.app.custom_symbols_var.set("")
        with patch("main.messagebox.showerror") as mock_err:
            self.app.generate_passwords()
            mock_err.assert_called_once()

        # Invalid chars in custom symbols -> rejected (B2)
        self.app.custom_symbols_var.set("ab c a")
        with patch("main.messagebox.showerror") as mock_err:
            self.app.generate_passwords()
            mock_err.assert_called_once()

        # Ambiguous-only custom symbols + Exclude Ambiguous ON -> rejected (B3)
        self.app.exclude_ambiguous_var.set(True)
        self.app.custom_symbols_var.set("|")
        with patch("main.messagebox.showerror") as mock_err:
            self.app.generate_passwords()
            mock_err.assert_called_once()

    def test_a04_exclude_ambiguous_on_and_off(self) -> None:
        """Test Exclude Ambiguous Characters ON and OFF."""
        self.app.exclude_ambiguous_var.set(True)
        self.app.length_var.set(48)
        self.app.batch_count_var.set("5")
        self.app.generate_passwords()
        for pwd in self.app.current_batch:
            self.assertFalse(any(ch in AMBIGUOUS_CHARS for ch in pwd))

        self.app.exclude_ambiguous_var.set(False)
        self.app.uppercase_var.set(True)
        self.app.lowercase_var.set(False)
        self.app.symbols_var.set(False)
        self.app.numbers_var.set(True)
        self.app.length_var.set(64)
        self.app.batch_count_var.set("3")
        self.app.generate_passwords()
        combined = "".join(self.app.current_batch)
        self.assertTrue(any(ch in AMBIGUOUS_CHARS for ch in combined))

    def test_a05_custom_symbols_respected(self) -> None:
        """Test valid Custom Symbols restriction."""
        self.app.uppercase_var.set(False)
        self.app.lowercase_var.set(False)
        self.app.numbers_var.set(True)
        self.app.symbols_var.set(True)
        self.app.exclude_ambiguous_var.set(True)
        self.app.custom_symbols_var.set("!@#")
        self.app.length_var.set(16)
        self.app.generate_passwords()

        pwd = self.app.password_var.get()
        self.assertEqual(len(pwd), 16)
        self.assertTrue(any(ch in "!@#" for ch in pwd))
        self.assertTrue(all(ch.isdigit() or ch in "!@#" for ch in pwd))

    def test_a06_random_quantities_1_2_10_20_30_50(self) -> None:
        """Test Quantity 1, 2, 10, 20, 30, and 50 in Random mode."""
        for qty in (1, 2, 10, 20, 30, 50):
            self.app.batch_count_var.set(str(qty))
            self.app.generate_passwords()
            self.root.update_idletasks()
            self.assertEqual(len(self.app.current_batch), qty)
            self.assertEqual(len(self.app.batch_entry_widgets), qty)

    def test_a07_show_hide_and_nonblocking_copy_with_fallback(self) -> None:
        """Bug B8: Show/Hide masking and Copy Primary / Copy All without blocking showinfo."""
        self.app.batch_count_var.set("3")
        self.app.generate_passwords()
        self.root.update_idletasks()

        self.assertTrue(self.app.is_password_visible.get())
        self.assertEqual(self.app.entry_password.cget("show"), "")

        self.app.toggle_password_visibility()
        self.assertFalse(self.app.is_password_visible.get())
        self.assertEqual(self.app.entry_password.cget("show"), "●")
        self.assertEqual(self.app.batch_entry_widgets[0].cget("show"), "●")

        self.app.toggle_password_visibility()
        self.assertTrue(self.app.is_password_visible.get())
        self.assertEqual(self.app.entry_password.cget("show"), "")

        with patch("main.pyperclip.copy", side_effect=RuntimeError("no sys clip")), patch(
            "main.messagebox.showinfo"
        ) as mock_info:
            self.app.copy_primary_password()
            self.assertEqual(self.root.clipboard_get(), self.app.password_var.get())
            self.assertIn("copied", self.app.lbl_copy_status.cget("text").lower())

            self.app.copy_all_passwords()
            self.assertEqual(self.root.clipboard_get(), "\n".join(self.app.current_batch))
            self.assertIn("3 items copied", self.app.lbl_copy_status.cget("text"))
            mock_info.assert_not_called()

    # ------------------------------------------------------------------
    # Section B: Mode 2 — Smart Personalized Passphrase Builder (TagInput)
    # ------------------------------------------------------------------

    def test_b01_old_word_count_and_custom_numbers_controls_removed(self) -> None:
        """Verify old word-count Spinbox, custom-numbers box, and multiline text box are gone."""
        self.assertFalse(hasattr(self.app, "spin_word_count"))
        self.assertFalse(hasattr(self.app, "word_count_var"))
        self.assertFalse(hasattr(self.app, "txt_custom_words"))
        self.assertFalse(hasattr(self.app, "entry_custom_numbers"))
        self.assertFalse(hasattr(self.app, "custom_numbers_var"))
        self.assertTrue(hasattr(self.app, "tag_input"))

    def test_b02_tag_input_comma_paste_duplicates_remove_clear_and_counter(self) -> None:
        """Test TagInput interactive comma commit, paste, duplicates, removal, Clear All, and counter."""
        self.app.switch_mode("passphrase")
        ti = self.app.tag_input

        # Placeholder is never counted as content
        self.assertEqual(ti.get_entries(), [])
        self.assertEqual(ti.entry.get(), PLACEHOLDER_TEXT)
        self.assertEqual(ti.lbl_counter.cget("text"), "0 entries added (minimum 2 required)")

        # Comma typing behavior: commit text before comma, keep trailing fragment in entry
        ti._hide_placeholder()
        ti.entry.insert(0, "Cricket, Mum")
        ti._handle_key_release(None)
        self.assertEqual(ti.get_entries(), ["Cricket"])
        self.assertEqual(ti.entry.get(), "Mum")

        # Paste batch of comma-separated entries creates chips immediately
        ti.entry.delete(0, tk.END)
        ti.entry.insert(0, "Mumbai, Coding, 41, Success, 2026")
        ti._process_pasted_content()
        self.assertEqual(
            ti.get_entries(),
            ["Cricket", "Mumbai", "Coding", "41", "Success", "2026"],
        )
        self.assertEqual(ti.lbl_counter.cget("text"), "6 entries added (minimum 2 required)")

        # Duplicate check is case-insensitive and shows inline feedback, not popup
        added, rejected = ti.add_from_text("cricket,  MUMBAI ")
        self.assertEqual(added, [])
        self.assertEqual(len(rejected), 2)
        self.assertIn("already added", ti.lbl_status.cget("text"))

        # Remove individual chip & Backspace on empty entry removes last chip
        ti.remove_at(1)  # removes Mumbai
        self.assertEqual(ti.get_entries(), ["Cricket", "Coding", "41", "Success", "2026"])
        ti._handle_backspace(None)  # removes 2026
        self.assertEqual(ti.get_entries(), ["Cricket", "Coding", "41", "Success"])

        # Clear All resets chips & counter
        ti.clear()
        self.assertEqual(ti.get_entries(), [])
        self.assertEqual(ti.lbl_counter.cget("text"), "0 entries added (minimum 2 required)")

    def test_b03_pending_text_committed_on_generate_and_empty_or_one_entry_rejected(self) -> None:
        """Verify trailing pending text without comma commits on Generate; <2 entries rejected safely."""
        self.app.switch_mode("passphrase")
        ti = self.app.tag_input

        # Seed valid output first
        ti.add_from_text("Alpha, Bravo, Charlie")
        self.app.generate_passwords()
        self.assertEqual(len(self.app.password_history), 1)
        self.assertNotEqual(self.app.password_var.get(), "")

        # Clear then fail with empty input -> stale output cleared, history untouched
        ti.clear()
        with patch("main.messagebox.showerror") as mock_err:
            self.app.generate_passwords()
            mock_err.assert_called_once()
        self.assertEqual(self.app.password_var.get(), "")
        self.assertEqual(self.app.current_batch, [])
        self.assertEqual(len(self.app.password_history), 1)

        # Fail with 1 entry only -> error, output stays cleared
        ti.add_from_text("sujit")
        with patch("main.messagebox.showerror") as mock_err:
            self.app.generate_passwords()
            mock_err.assert_called_once()
        self.assertEqual(self.app.password_var.get(), "")
        self.assertEqual(len(self.app.password_history), 1)

        # Typing second fragment without trailing comma still commits automatically on Generate
        ti._hide_placeholder()
        ti.entry.insert(0, "Coding")
        self.app.generate_passwords()
        self.assertEqual(ti.get_entries(), ["sujit", "Coding"])
        self.assertEqual(len(self.app.current_batch), 1)
        self.assertEqual(len(self.app.password_history), 2)

    def test_b04_mode_switch_preserves_tags_and_reset_clears_tags(self) -> None:
        """Switching modes keeps tags intact; Reset Defaults clears tags and pending entry."""
        self.app.switch_mode("passphrase")
        self.app.tag_input.add_from_text("Cricket, Mumbai, 2026")
        self.app.switch_mode("random")
        self.assertEqual(self.app.tag_input.get_entries(), ["Cricket", "Mumbai", "2026"])

        self.app.switch_mode("passphrase")
        self.assertEqual(self.app.tag_input.get_entries(), ["Cricket", "Mumbai", "2026"])

        self.app.reset_settings()
        self.assertEqual(self.app.tag_input.get_entries(), [])
        self.assertEqual(self.app.batch_count_var.get(), "1")

    def test_b05_separators_random_numbers_symbols_and_quantities_10_20_entries(self) -> None:
        """Test 10 and 20 entries, all separators, digits/symbols toggles, and quantities 1..50."""
        self.app.switch_mode("passphrase")
        self.app.tag_input.add_from_text(
            "One, Two, Three, Four, Five, Six, Seven, Eight, Nine, Ten"
        )
        self.assertEqual(len(self.app.tag_input.get_entries()), 10)

        self.app.passphrase_numbers_var.set(False)
        self.app.passphrase_symbols_var.set(False)
        for sep in ("-", "_", ".", " "):
            self.app.separator_var.set(sep)
            self.app.generate_passwords()
            parts = self.app.password_var.get().split(sep)
            self.assertEqual(len(parts), 10)

        # 20 entries + random numbers & symbols ON + quantities 1, 2, 10, 20, 30, 50
        self.app.tag_input.add_from_text(
            "Eleven, Twelve, Thirteen, Fourteen, Fifteen, Sixteen, Seventeen, Eighteen, Nineteen, Twenty"
        )
        self.assertEqual(len(self.app.tag_input.get_entries()), 20)
        self.app.separator_var.set("-")
        self.app.passphrase_numbers_var.set(True)
        self.app.passphrase_symbols_var.set(True)

        for qty in (1, 2, 10, 20, 30, 50):
            self.app.batch_count_var.set(str(qty))
            self.app.generate_passwords()
            self.assertEqual(len(self.app.current_batch), qty)
            self.assertEqual(len(set(self.app.current_batch)), qty)
            self.assertTrue(any(c.isdigit() for c in self.app.password_var.get()))
            self.assertTrue(any(c in PASSPHRASE_SYMBOLS for c in self.app.password_var.get()))

    def test_b06_exhaustion_shows_one_notice_and_saves_only_produced_items(self) -> None:
        """Bug B5: 2 entries + quantity 10 produces only 2 unique passphrases and saves 2."""
        self.app.switch_mode("passphrase")
        self.app.tag_input.add_from_text("Alpha, Bravo")
        self.app.passphrase_numbers_var.set(False)
        self.app.passphrase_symbols_var.set(False)
        self.app.batch_count_var.set("10")

        with patch("main.messagebox.showinfo") as mock_info:
            self.app.generate_passwords()
            mock_info.assert_called_once()

        self.assertEqual(len(self.app.current_batch), 2)
        self.assertEqual(len(self.app.password_history), 2)
        self.assertIn("2 of 10", self.app.lbl_copy_status.cget("text"))

    def test_b07_random_words_passphrase_source_ui_entropy_and_history(self) -> None:
        """Test Passphrase Source switcher, 4-8 validation, generation, entropy label, and history."""
        self.app.switch_mode("passphrase")
        self.app.tag_input.add_from_text("Cricket, Mumbai, Coding")

        # Switch to Secure Random Words and back preserves Custom Words tags
        self.app.passphrase_source_var.set("random_words")
        self.app._update_passphrase_source_ui()
        self.assertEqual(self.app.tag_input.get_entries(), ["Cricket", "Mumbai", "Coding"])

        # Tkinter key validation on spin_random_words allows 4..8 and rejects invalid input
        spin_rw = self.app.spin_random_words
        for ok_digit in ("4", "6", "8"):
            spin_rw.delete(0, tk.END)
            spin_rw.insert(0, ok_digit)
            self.assertEqual(spin_rw.get(), ok_digit)
        for bad_input in ("0", "3", "9", "45", "abc"):
            spin_rw.delete(0, tk.END)
            spin_rw.insert(0, bad_input)
            self.assertEqual(spin_rw.get(), "")

        # Generate 5 batches of 6 random words with '.' separator, caps, digits, symbols
        spin_rw.delete(0, tk.END)
        spin_rw.insert(0, "6")
        self.app.separator_var.set(".")
        self.app.passphrase_capitalize_var.set(True)
        self.app.passphrase_numbers_var.set(True)
        self.app.passphrase_symbols_var.set(True)
        self.app.batch_count_var.set("15")
        self.app.generate_passwords()

        self.assertEqual(len(self.app.current_batch), 15)
        self.assertEqual(len(self.app.password_history), 15)
        self.assertEqual(self.app.lbl_history_count.cget("text"), "15 saved")
        self.assertIn("Estimated Entropy:", self.app.lbl_strength.cget("text"))
        self.assertIn("bits", self.app.lbl_strength.cget("text"))

        # Programmatic invalid word count rejected cleanly without touching history
        self.app.random_word_count_var.set("3")
        with patch("main.messagebox.showerror") as mock_err:
            self.app.generate_passwords()
            mock_err.assert_called_once()
        self.assertEqual(self.app.password_var.get(), "")
        self.assertEqual(len(self.app.password_history), 15)

        # Switch back to Custom Words -> still has saved 3 entries and generates & appends cleanly
        self.app.passphrase_source_var.set("custom")
        self.app._update_passphrase_source_ui()
        self.app.batch_count_var.set("5")
        self.app.generate_passwords()
        self.assertEqual(len(self.app.password_history), 20)
        self.assertIn("assuming your words are known", self.app.lbl_strength.cget("text"))

    # ------------------------------------------------------------------
    # Section C: Invalid Quantity Validation
    # ------------------------------------------------------------------

    def test_c01_invalid_quantity_rejected_and_clears_stale_output(self) -> None:
        """Verify invalid quantities reject generation, clear stale output, and protect history."""
        self.app.batch_count_var.set("2")
        self.app.generate_passwords()
        self.assertEqual(len(self.app.password_history), 2)

        for bad_qty in ("", "0", "51", "-1", "2.5", "abc"):
            self.app.batch_count_var.set(bad_qty)
            with patch("main.messagebox.showerror") as mock_err:
                self.app.generate_passwords()
                mock_err.assert_called_once()
            self.assertEqual(self.app.password_var.get(), "")
            self.assertEqual(self.app.current_batch, [])
            self.assertEqual(len(self.app.password_history), 2)

    # ------------------------------------------------------------------
    # Section D: Common Session History Window & Lifecycle
    # ------------------------------------------------------------------

    def test_d01_history_saves_complete_batches_1_2_10_20_30_50_both_modes(self) -> None:
        """Verify fresh start (0), cumulative counts 20->30->60, quantities 1..50, and dual modes."""
        # Fresh app begins at zero
        self.assertEqual(len(self.app.password_history), 0)
        self.assertEqual(self.app.lbl_history_count.cget("text"), "0 saved")

        # Exact cumulative progression requested: 20 -> 30 -> 60
        for qty, expected_total in ((20, 20), (10, 30), (30, 60)):
            self.app.batch_count_var.set(str(qty))
            self.app.generate_passwords()
            self.assertEqual(len(self.app.password_history), expected_total)
            self.assertEqual(
                self.app.lbl_history_count.cget("text"), f"{expected_total} saved"
            )

        # Remaining quantities 1, 2, 50 and switching modes never overwrites history
        self.app.switch_mode("passphrase")
        self.app.tag_input.add_from_text("Cricket, Mumbai, Coding, Success, Horizon")
        running = 60
        for qty in (1, 2, 50):
            self.app.batch_count_var.set(str(qty))
            self.app.generate_passwords()
            running += qty
            self.assertEqual(len(self.app.password_history), running)
            self.assertEqual(self.app.lbl_history_count.cget("text"), f"{running} saved")
            self.assertEqual(self.app.history_modes[:qty], ["Passphrase"] * qty)

    def test_d02_save_toggle_off_preserves_previous_history(self) -> None:
        """Verify Save to History OFF stops adding new items without clearing previous entries."""
        self.app.batch_count_var.set("5")
        self.app.generate_passwords()
        self.app.enable_history_var.set(False)
        self.app.batch_count_var.set("10")
        self.app.generate_passwords()
        self.assertEqual(len(self.app.password_history), 5)

    def test_d03_history_window_scroll_filter_and_nonblocking_copy_all(self) -> None:
        """Test History scroll, Last 5 / All filter, independent masking, Copy & Copy All."""
        self.app.batch_count_var.set("50")
        self.app.generate_passwords()
        self.app.open_history_window()
        self.root.update_idletasks()

        self.assertEqual(
            self.app.lbl_hist_window_title.cget("text"),
            "🕒 Session History (50 passwords)",
        )
        self.assertEqual(len(self.app.history_entry_widgets), 50)
        bbox = self.app.history_canvas.bbox("all")
        self.assertIsNotNone(bbox)
        self.assertGreater(bbox[3], 500)

        self.assertFalse(self.app.history_visible_var.get())
        self.assertEqual(self.app.history_entry_widgets[49].cget("show"), "●")

        with patch("main.pyperclip.copy", side_effect=RuntimeError("no sys clip")), patch(
            "main.messagebox.showinfo"
        ) as mock_info:
            self.app.copy_history_item(self.app.password_history[45], 46)
            self.assertEqual(self.root.clipboard_get(), self.app.password_history[45])

            self.app.copy_all_history()
            copied = self.root.clipboard_get().splitlines()
            self.assertEqual(len(copied), 50)
            self.assertEqual(copied, self.app.password_history)
            mock_info.assert_not_called()

        # Optional Last 5 / All view filter
        self.app.history_filter_var.set("last5")
        self.app._refresh_history_window()
        self.root.update_idletasks()
        self.assertEqual(len(self.app.history_entry_widgets), 5)

        self.app.history_filter_var.set("all")
        self.app._refresh_history_window()
        self.root.update_idletasks()
        self.assertEqual(len(self.app.history_entry_widgets), 50)

    def test_d04_history_max_500_cap_enforced_and_noted(self) -> None:
        """Bug B9: Session history caps at MAX_HISTORY_ENTRIES (500) dropping oldest."""
        self.app.password_history = [f"OldPwd{i}" for i in range(495)]
        self.app.history_modes = ["Random"] * 495

        self.app.batch_count_var.set("10")
        self.app.generate_passwords()

        self.assertEqual(len(self.app.password_history), MAX_HISTORY_ENTRIES)
        self.assertTrue(self.app.history_capped)
        self.app.open_history_window()
        self.root.update_idletasks()
        self.assertIn("500", self.app.lbl_hist_window_count.cget("text"))

    def test_d05_history_close_reopen_clear_and_exit_purge(self) -> None:
        """Closing History window keeps entries; Clear requires confirm; on_close purges RAM."""
        self.app.switch_mode("passphrase")
        self.app.tag_input.add_from_text("Alpha, Bravo, Charlie, Delta, Echo")
        self.app.batch_count_var.set("20")
        self.app.generate_passwords()
        self.app.open_history_window()
        self.root.update_idletasks()

        self.app.close_history_window()
        self.assertEqual(len(self.app.password_history), 20)

        self.app.batch_count_var.set("10")
        self.app.generate_passwords()
        self.app.open_history_window()
        self.root.update_idletasks()
        self.assertEqual(
            self.app.lbl_hist_window_title.cget("text"),
            "🕒 Session History (30 passwords)",
        )
        self.assertEqual(len(self.app.history_entry_widgets), 30)

        with patch("main.messagebox.askyesno", return_value=False):
            self.app.clear_history()
        self.assertEqual(len(self.app.password_history), 30)

        with patch("main.messagebox.askyesno", return_value=True):
            self.app.clear_history()
        self.root.update_idletasks()
        self.assertEqual(len(self.app.password_history), 0)

        self.app.batch_count_var.set("5")
        self.app.generate_passwords()
        self.app.on_close()
        self.assertEqual(self.app.password_history, [])
        self.assertEqual(self.app.history_modes, [])
        self.assertEqual(self.app.current_batch, [])
        self.assertEqual(self.app.current_passphrase_entries, [])


if __name__ == "__main__":
    unittest.main()
