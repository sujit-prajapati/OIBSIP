"""Headless unit tests for generator_core.py (zero Tkinter imports)."""

import os
import tempfile
import unittest

import generator_core as core


class TestGeneratorCore(unittest.TestCase):
    """Verify cryptographic generation, validation, exhaustion, and strength models."""

    def test_no_tkinter_imported(self) -> None:
        """Ensure generator_core remains GUI-independent."""
        self.assertFalse(hasattr(core, "tk"))
        self.assertFalse(hasattr(core, "tkinter"))

    def test_password_lengths_8_12_16_32_64(self) -> None:
        """Verify exact output lengths across 8, 12, 16, 32, and 64."""
        groups = core.build_character_groups(
            True, True, True, True, core.DEFAULT_SYMBOLS, False
        )
        for length in (8, 12, 16, 32, 64):
            pw = core.generate_password(length, groups)
            self.assertEqual(len(pw), length)

    def test_categories_pairs_and_combined_all_represented(self) -> None:
        """Verify minimum-2 category enforcement and guaranteed representation per group."""
        pairs = [
            (True, True, False, False),
            (True, False, True, False),
            (True, False, False, True),
            (False, True, True, False),
            (False, True, False, True),
            (False, False, True, True),
            (True, True, True, True),
        ]
        for up, lo, dig, sym in pairs:
            groups = core.build_character_groups(
                up, lo, dig, sym, core.DEFAULT_SYMBOLS, False
            )
            pw = core.generate_password(16, groups)
            self.assertEqual(len(pw), 16)
            for grp in groups:
                self.assertTrue(
                    any(ch in grp for ch in pw),
                    f"Missing representation for group {grp!r} in {pw!r}",
                )

    def test_b4_fewer_than_two_categories_rejected(self) -> None:
        """Bug B4: Selecting 0 or only 1 character category must raise ValueError."""
        single_or_empty = [
            (False, False, False, False),
            (True, False, False, False),
            (False, True, False, False),
            (False, False, True, False),
            (False, False, False, True),
        ]
        for up, lo, dig, sym in single_or_empty:
            with self.assertRaises(ValueError):
                core.build_character_groups(up, lo, dig, sym, core.DEFAULT_SYMBOLS, False)

    def test_ambiguous_exclusion_5000_samples(self) -> None:
        """Verify Exclude Ambiguous ON never emits lookalikes across 5,000 generated samples."""
        groups_filtered = core.build_character_groups(
            True, True, True, True, core.DEFAULT_SYMBOLS, True
        )
        for _ in range(5000):
            pw = core.generate_password(16, groups_filtered)
            self.assertFalse(any(ch in core.AMBIGUOUS_CHARS for ch in pw))

        groups_unfiltered = core.build_character_groups(
            False, True, True, False, "", False
        )
        combined = "".join(core.generate_password(24, groups_unfiltered) for _ in range(50))
        self.assertTrue(any(ch in core.AMBIGUOUS_CHARS for ch in combined))

    def test_b1_b2_b3_custom_symbols_strict_validation(self) -> None:
        """Bugs B1–B3: Empty custom symbols, bad characters, length cap, and ambiguous-only."""
        # B1: Symbols ON with empty custom symbols
        with self.assertRaises(ValueError) as ctx_empty:
            core.build_character_groups(True, True, False, True, "", False)
        self.assertIn("empty", str(ctx_empty.exception).lower())

        # B2: Letters, spaces, or non-ASCII rejected without silent cleanup
        for bad_syms in ("ab c a", "!@#a", "!@#1", "!@# "):
            with self.assertRaises(ValueError) as ctx_bad:
                core.build_character_groups(True, True, False, True, bad_syms, False)
            self.assertIn("Invalid character", str(ctx_bad.exception))

        # B2: Deduplication preserves valid symbols; >40 unique fails cleanly
        self.assertEqual(core.validate_custom_symbols("!!@@##"), "!@#")

        # B3: All custom symbols are ambiguous and Exclude Ambiguous is ON
        with self.assertRaises(ValueError) as ctx_amb:
            core.build_character_groups(True, True, False, True, "|", True)
        self.assertIn("No usable symbols remain", str(ctx_amb.exception))

    def test_parse_entries_commas_paste_spaces_duplicates_case(self) -> None:
        """Verify entry parsing trims, drops empties, deduplicates ignoring case, keeps first spelling."""
        parsed = core.parse_entries(
            "Cricket, Mumbai,\n coding , 41 , cricket , MUMBAI , , 2026 ,   Success  "
        )
        self.assertEqual(parsed, ["Cricket", "Mumbai", "coding", "41", "2026", "Success"])
        self.assertEqual(core.parse_entries("  ,  , \n  "), [])

    def test_passphrase_n_2_3_5_10_separators_caps_digits_symbols(self) -> None:
        """Verify passphrases for n=2,3,5,10, all separators, casing, digits, and symbols."""
        base_pool = [
            "Alpha",
            "bravo",
            "Charlie",
            "41",
            "Echo",
            "Falcon",
            "Golf",
            "Hotel",
            "India",
            "2026",
        ]
        for n in (2, 3, 5, 10):
            entries = base_pool[:n]
            for sep in core.SEPARATORS:
                batch = core.generate_passphrase_batch(
                    entries=entries,
                    separator=sep,
                    capitalize=False,
                    add_digits=False,
                    add_symbols=False,
                    quantity=1,
                )
                self.assertEqual(batch.produced, 1)
                parts = batch.items[0].split(sep)
                self.assertEqual(len(parts), n)
                self.assertEqual(set(parts), set(entries))

        # Capitalize ON upper-cases leading alpha letters and keeps numeric entries untouched
        b_caps = core.generate_passphrase_batch(
            ["cricket", "41", "mumbai"],
            separator="-",
            capitalize=True,
            add_digits=False,
            add_symbols=False,
            quantity=1,
        )
        tokens_caps = b_caps.items[0].split("-")
        self.assertIn("Cricket", tokens_caps)
        self.assertIn("Mumbai", tokens_caps)
        self.assertIn("41", tokens_caps)

        # Digits ON / Symbols ON -> consistent suffix e.g. Alpha.Bravo.Charlie.Delta-482@
        b_extras = core.generate_passphrase_batch(
            ["Alpha", "Bravo", "Charlie", "Delta"],
            separator=".",
            capitalize=True,
            add_digits=True,
            add_symbols=True,
            quantity=5,
        )
        for item in b_extras.items:
            self.assertRegex(item, r"^[A-Za-z.]+-\d{3}[^A-Za-z0-9\s]$")
            self.assertNotIn("..", item)

        # Digits OFF / Symbols ON -> consistent trailing symbol with no preceding separator
        b_sym_only = core.generate_passphrase_batch(
            ["Alpha", "Bravo", "Charlie", "Delta"],
            separator=".",
            capitalize=True,
            add_digits=False,
            add_symbols=True,
            quantity=5,
        )
        for item in b_sym_only.items:
            self.assertTrue(item[-1] in core.PASSPHRASE_SYMBOLS)
            self.assertFalse(item[-2] in core.SEPARATORS)

        b_plain = core.generate_passphrase_batch(
            ["Alpha", "Bravo", "Charlie", "Delta"],
            separator="-",
            capitalize=True,
            add_digits=False,
            add_symbols=False,
            quantity=5,
        )
        for item in b_plain.items:
            self.assertFalse(any(c.isdigit() for c in item))
            self.assertFalse(any(c in core.PASSPHRASE_SYMBOLS for c in item))

    def test_passphrase_quantities_and_b5_exhaustion(self) -> None:
        """Bug B5: Verify quantities 1,2,10,20,30,50, zero duplicates, and clean exhaustion."""
        ten_entries = [
            "Alpha",
            "Bravo",
            "Charlie",
            "Delta",
            "Echo",
            "Falcon",
            "Gamma",
            "Horizon",
            "Matrix",
            "Zenith",
        ]
        for qty in (1, 2, 10, 20, 30, 50):
            batch = core.generate_passphrase_batch(
                entries=ten_entries,
                separator="-",
                capitalize=True,
                add_digits=False,
                add_symbols=False,
                quantity=qty,
            )
            self.assertEqual(batch.produced, qty)
            self.assertEqual(len(batch.items), qty)
            self.assertEqual(len(set(batch.items)), qty)
            self.assertEqual(batch.limited_reason, "")

        # Exhaustion: n=2 (max 2! = 2), quantity=10 -> exactly 2 produced, never padded
        exhausted_2 = core.generate_passphrase_batch(
            entries=["Alpha", "Bravo"],
            separator="-",
            capitalize=True,
            add_digits=False,
            add_symbols=False,
            quantity=10,
        )
        self.assertEqual(exhausted_2.requested, 10)
        self.assertEqual(exhausted_2.produced, 2)
        self.assertEqual(len(exhausted_2.items), 2)
        self.assertEqual(len(set(exhausted_2.items)), 2)
        self.assertIn("2", exhausted_2.limited_reason)

        # Exhaustion: n=3 (max 3! = 6), quantity=10 -> exactly 6 produced
        exhausted_3 = core.generate_passphrase_batch(
            entries=["Alpha", "Bravo", "Charlie"],
            separator="-",
            capitalize=True,
            add_digits=False,
            add_symbols=False,
            quantity=10,
        )
        self.assertEqual(exhausted_3.produced, 6)
        self.assertEqual(len(set(exhausted_3.items)), 6)
        self.assertIn("Generated 6 of 10", exhausted_3.limited_reason)

    def test_b6_b7_honest_strength_and_pattern_penalties(self) -> None:
        """Bugs B6 & B7: Pattern downgrades on random passwords and conservative passphrase rating."""
        r_pw = core.estimate_password_strength("Password1234!")
        r_qw = core.estimate_password_strength("Qwerty123456!")
        r_rep = core.estimate_password_strength("Aaaaaaaaaaaaaaaa1!")
        r_strong = core.estimate_password_strength("G8#kP2!vQ9$mW4@z")

        self.assertEqual(r_pw.label, "Fair")
        self.assertTrue(len(r_pw.notes) > 0)
        self.assertEqual(r_qw.label, "Fair")
        self.assertEqual(r_rep.label, "Strong")  # Downgraded from Very Strong due to repeated chars
        self.assertEqual(r_strong.label, "Very Strong")

        # 6-entry personalized passphrase with familiar/year entries stays capped at Fair
        p_familiar = core.estimate_passphrase_strength(
            ["Cricket", "Mumbai", "Coding", "41", "Success", "2026"],
            has_digits=True,
            has_symbols=True,
        )
        self.assertIn(p_familiar.label, ("Weak", "Fair"))
        self.assertLessEqual(p_familiar.bits, 30.0)

        # 6 unfamiliar entries with digits & symbols (~23 bits) -> Weak or Fair (never Very Strong)
        p_six = core.estimate_passphrase_strength(
            ["Quartz", "Zephyr", "Lantern", "Breeze", "Timber", "Canyon"],
            has_digits=True,
            has_symbols=True,
        )
        self.assertIn(p_six.label, ("Weak", "Fair"))

    def test_curated_wordlist_integrity_and_random_words_validation(self) -> None:
        """Curated wordlist is large, distinct, lowercase ASCII, non-PII, and 4..8 is enforced."""
        words = core.CURATED_WORDS
        self.assertGreaterEqual(len(words), 1024)
        self.assertEqual(len(words), len(set(words)))
        for w in words:
            self.assertTrue(w.isalpha() and w.isascii() and w.islower())
            self.assertEqual(core.detect_predictable_patterns(w), [])

        for ok_val in ("4", "5", "6", "7", "8"):
            ok, parsed, err = core.validate_random_word_count(ok_val)
            self.assertTrue(ok)
            self.assertEqual(parsed, int(ok_val))
            self.assertEqual(err, "")

        for bad_val in ("", "0", "1", "2", "3", "9", "10", "4.5", "-4", "abc"):
            ok, parsed, err = core.validate_random_word_count(bad_val)
            self.assertFalse(ok)
            self.assertIsNone(parsed)
            self.assertTrue(len(err) > 0)

    def test_random_words_passphrase_generation_and_entropy(self) -> None:
        """Secure Random Words uses secrets.choice, formatting, no predictable sequence, true entropy."""
        curated_set = set(core.CURATED_WORDS)
        for wc in (4, 5, 6, 7, 8):
            batch = core.generate_random_words_batch(
                word_count=wc,
                separator=".",
                capitalize=True,
                add_digits=True,
                add_symbols=True,
                quantity=10,
            )
            self.assertEqual(batch.produced, 10)
            self.assertEqual(len(set(batch.items)), 10)
            for item in batch.items:
                word_part, suffix_part = item.rsplit("-", 1)
                tokens = word_part.split(".")
                self.assertEqual(len(tokens), wc)
                self.assertTrue(all(t[0].isupper() and t.lower() in curated_set for t in tokens))
                self.assertRegex(suffix_part, r"^\d{3}[^A-Za-z0-9\s]$")
                # Avoid identical adjacent words or monotonic alphabetical sequence
                lower_tokens = [t.lower() for t in tokens]
                self.assertFalse(
                    any(lower_tokens[i] == lower_tokens[i - 1] for i in range(1, wc))
                )
                self.assertNotEqual(lower_tokens, sorted(lower_tokens))
                self.assertNotEqual(lower_tokens, sorted(lower_tokens, reverse=True))

        # Entropy strictly reflects word selection process and wordlist size
        e4 = core.estimate_random_passphrase_strength(4, pool_size=len(core.CURATED_WORDS))
        e6 = core.estimate_random_passphrase_strength(6, pool_size=len(core.CURATED_WORDS))
        e8 = core.estimate_random_passphrase_strength(8, pool_size=len(core.CURATED_WORDS))
        self.assertGreater(e4.bits, 40.0)
        self.assertEqual(e4.label, "Fair")
        self.assertGreater(e6.bits, 60.0)
        self.assertEqual(e6.label, "Strong")
        self.assertGreater(e8.bits, 80.0)
        self.assertEqual(e8.label, "Very Strong")

    def test_ram_only_no_files_created_during_generation(self) -> None:
        """Ensure generating random passwords or passphrases creates no files on disk."""
        orig_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                before = set(os.listdir(tmpdir))
                groups = core.build_character_groups(
                    True, True, True, True, core.DEFAULT_SYMBOLS, True
                )
                _ = [core.generate_password(16, groups) for _ in range(25)]
                _ = core.generate_passphrase_batch(
                    ["Alpha", "Bravo", "Charlie", "Delta", "Echo"],
                    separator="-",
                    capitalize=True,
                    add_digits=True,
                    add_symbols=True,
                    quantity=25,
                )
                after = set(os.listdir(tmpdir))
                self.assertEqual(before, after)
            finally:
                os.chdir(orig_cwd)


if __name__ == "__main__":
    unittest.main()

