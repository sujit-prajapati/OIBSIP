"""
Core password and personalized passphrase generation engine (GUI-independent).

Contains all cryptographic generation via Python's `secrets` module, input
parsing, strict validation helpers, pattern detection, and honest strength
estimation without importing `tkinter`.
"""

from dataclasses import dataclass, field
import itertools
import math
import re
import secrets
import string
from typing import List, Optional, Tuple

from wordlist import CURATED_WORDS

# ---------------------------------------------------------------------------
# Core Limits & Character Sets
# ---------------------------------------------------------------------------
MIN_LENGTH = 8
MAX_LENGTH = 64
DEFAULT_LENGTH = 16

MIN_QUANTITY = 1
MAX_QUANTITY = 50

MIN_PASSPHRASE_ENTRIES = 2
MIN_RANDOM_WORDS = 4
MAX_RANDOM_WORDS = 8
DEFAULT_RANDOM_WORDS = 5
MAX_ENTRIES = 30
MAX_ENTRY_LENGTH = 32
MAX_CUSTOM_SYMBOLS_LENGTH = 40
MAX_HISTORY_ENTRIES = 500

DEFAULT_SYMBOLS = "!@#$%^&*()-_=+[]{}?"
PASSPHRASE_SYMBOLS = "!@#$%^&*+=?"
AMBIGUOUS_CHARS = "0O1lI|"

SEPARATORS: List[str] = ["-", "_", ".", " "]
SEPARATOR_OPTIONS: List[Tuple[str, str]] = [
    ("-", "Hyphen (-)"),
    ("_", "Underscore (_)"),
    (".", "Dot (.)"),
    (" ", "Space ( )"),
]

# ---------------------------------------------------------------------------
# Tunable Strength Threshold Constants
# ---------------------------------------------------------------------------
PASSPHRASE_WEAK_MAX_BITS = 24.0
PASSPHRASE_FAIR_MAX_BITS = 36.0
PASSPHRASE_STRONG_MAX_BITS = 60.0
PASSPHRASE_VERY_STRONG_MIN_LENGTH = 20
PASSPHRASE_MIN_ENTRIES_FOR_STRONG = 4
PASSPHRASE_SHORT_WEAK_LENGTH = 12
PASSPHRASE_SHORT_FAIR_LENGTH = 16

# Independent random-word entropy bands based strictly on calculated bits
RANDOM_PASSPHRASE_WEAK_MAX_BITS = 40.0
RANDOM_PASSPHRASE_FAIR_MAX_BITS = 55.0
RANDOM_PASSPHRASE_STRONG_MAX_BITS = 70.0

TIER_ORDER: Tuple[str, ...] = ("Weak", "Fair", "Strong", "Very Strong")
TIER_FRACTIONS = {
    "Not Generated": 0.0,
    "Weak": 0.25,
    "Fair": 0.50,
    "Strong": 0.75,
    "Very Strong": 1.0,
}

# Common weak dictionary / keyboard / location markers checked case-insensitively
COMMON_PREDICTABLE_WORDS = (
    "password",
    "pass123",
    "admin",
    "welcome",
    "letmein",
    "iloveyou",
    "dragon",
    "monkey",
    "football",
    "cricket",
    "india",
    "mumbai",
    "qwerty",
    "sunshine",
    "princess",
    "master",
    "123456",
)

KEYBOARD_SEQUENCES = ("qwerty", "qwert", "asdf", "zxcv", "yuiop", "hjkl", "bnm")


@dataclass
class PassphraseBatch:
    """Result container for passphrase batch generation without duplicate padding."""

    items: List[str]
    requested: int
    produced: int
    limited_reason: str = ""


@dataclass
class StrengthResult:
    """Strength estimate with label, bar fraction, bit estimate, and advisory notes."""

    label: str
    fraction: float
    bits: float
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Strict Input Validation & Parsing
# ---------------------------------------------------------------------------
def validate_quantity(raw_value: object) -> Tuple[bool, Optional[int], str]:
    """Validate batch quantity strictly in 1..50 without silent coercion."""
    cleaned = str(raw_value).strip()
    if not cleaned:
        return (
            False,
            None,
            "Quantity to generate cannot be empty. Please enter a whole number between 1 and 50.",
        )
    if not cleaned.isdigit() or cleaned.startswith("0"):
        return (
            False,
            None,
            f"Invalid quantity '{cleaned}'. Please enter a whole number between 1 and 50.",
        )
    qty = int(cleaned)
    if not (MIN_QUANTITY <= qty <= MAX_QUANTITY):
        return (
            False,
            None,
            f"Quantity '{qty}' is out of range. Please enter a whole number between 1 and 50.",
        )
    return (True, qty, "")


def validate_length(raw_value: object) -> Tuple[bool, Optional[int], str]:
    """Validate random password length strictly in 8..64 without silent coercion."""
    cleaned = str(raw_value).strip()
    if not cleaned:
        return (
            False,
            None,
            f"Password length cannot be empty. Please enter a whole number between {MIN_LENGTH} and {MAX_LENGTH}.",
        )
    if not cleaned.isdigit():
        return (
            False,
            None,
            f"Password length '{cleaned}' must be a valid integer between {MIN_LENGTH} and {MAX_LENGTH}.",
        )
    length = int(cleaned)
    if not (MIN_LENGTH <= length <= MAX_LENGTH):
        return (
            False,
            None,
            f"Password length must be between {MIN_LENGTH} and {MAX_LENGTH} characters.",
        )
    return (True, length, "")


def validate_custom_symbols(raw_symbols: str) -> str:
    """
    Validate and deduplicate custom symbol characters.

    Allows only printable, non-alphanumeric, non-space ASCII characters.
    Raises ValueError listing any offending characters without silently dropping them.
    """
    if not raw_symbols:
        raise ValueError("Custom symbols cannot be empty while Symbols is enabled.")

    bad_chars: List[str] = []
    seen_bad = set()
    for ch in raw_symbols:
        is_printable_ascii = 32 <= ord(ch) <= 126
        if not is_printable_ascii or ch.isalnum() or ch.isspace():
            display = "<space>" if ch == " " else repr(ch)
            if display not in seen_bad:
                seen_bad.add(display)
                bad_chars.append(display)

    if bad_chars:
        raise ValueError(
            "Invalid character(s) in Custom Symbols: "
            + ", ".join(bad_chars)
            + ". Only printable ASCII symbols are allowed (no letters, digits, or spaces)."
        )

    deduped = "".join(dict.fromkeys(raw_symbols))
    if len(deduped) > MAX_CUSTOM_SYMBOLS_LENGTH:
        raise ValueError(
            f"Custom symbols cannot exceed {MAX_CUSTOM_SYMBOLS_LENGTH} unique characters "
            f"(currently {len(deduped)})."
        )
    return deduped


def parse_entries(raw_text: str) -> List[str]:
    """
    Parse comma- or newline-separated words/numbers into clean, unique entries.

    Trims whitespace, collapses inner spaces, ignores empty tokens, removes
    case-insensitive duplicates, and preserves original spelling & capitalization
    of the first occurrence.
    """
    tokens = re.split(r"[,\r\n]+", raw_text or "")
    unique_entries: List[str] = []
    seen_lower = set()

    for token in tokens:
        cleaned = " ".join(token.split())
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen_lower:
            seen_lower.add(key)
            unique_entries.append(cleaned)

    return unique_entries


# ---------------------------------------------------------------------------
# Random Password Generation
# ---------------------------------------------------------------------------
def build_character_groups(
    upper: bool,
    lower: bool,
    digits: bool,
    symbols_on: bool,
    custom_symbols: str,
    exclude_ambiguous: bool,
) -> List[str]:
    """
    Build validated character pools for random password generation.

    Requires at least 2 selected character types and strictly validates custom
    symbols (raising ValueError rather than silently dropping categories).
    """
    selected_count = int(bool(upper)) + int(bool(lower)) + int(bool(digits)) + int(bool(symbols_on))
    if selected_count == 0:
        raise ValueError("Please select at least 2 character categories.")
    if selected_count < 2:
        raise ValueError(
            "Please select at least 2 character categories (e.g., Uppercase and Lowercase, "
            "or Letters and Numbers)."
        )

    groups: List[str] = []

    if upper:
        pool = string.ascii_uppercase
        if exclude_ambiguous:
            pool = "".join(c for c in pool if c not in AMBIGUOUS_CHARS)
        groups.append(pool)

    if lower:
        pool = string.ascii_lowercase
        if exclude_ambiguous:
            pool = "".join(c for c in pool if c not in AMBIGUOUS_CHARS)
        groups.append(pool)

    if digits:
        pool = string.digits
        if exclude_ambiguous:
            pool = "".join(c for c in pool if c not in AMBIGUOUS_CHARS)
        groups.append(pool)

    if symbols_on:
        if not custom_symbols:
            raise ValueError("Custom symbols cannot be empty while Symbols is enabled.")
        validated_syms = validate_custom_symbols(custom_symbols)
        if exclude_ambiguous:
            validated_syms = "".join(c for c in validated_syms if c not in AMBIGUOUS_CHARS)
        if not validated_syms:
            raise ValueError(
                "No usable symbols remain after excluding ambiguous characters."
            )
        groups.append(validated_syms)

    return groups


def generate_password(length: int, groups: List[str]) -> str:
    """
    Generate a single cryptographically random password guaranteeing at least
    one character from every selected category via Python's `secrets` module.
    """
    if not (MIN_LENGTH <= length <= MAX_LENGTH):
        raise ValueError(f"Password length must be between {MIN_LENGTH} and {MAX_LENGTH}.")
    if len(groups) < 2:
        raise ValueError("At least 2 character groups are required.")

    selected_chars = [secrets.choice(group) for group in groups]
    all_chars = "".join(groups)

    for _ in range(length - len(selected_chars)):
        selected_chars.append(secrets.choice(all_chars))

    secrets.SystemRandom().shuffle(selected_chars)
    return "".join(selected_chars)


# ---------------------------------------------------------------------------
# Smart Personalized Passphrase Generation
# ---------------------------------------------------------------------------
def _format_passphrase_tokens(entries: List[str], capitalize: bool) -> List[str]:
    """Apply optional leading capitalization while leaving numeric tokens intact."""
    if not capitalize:
        return list(entries)
    formatted: List[str] = []
    for entry in entries:
        if entry and entry[0].isalpha():
            formatted.append(entry[0].upper() + entry[1:])
        else:
            formatted.append(entry)
    return formatted


def validate_random_word_count(raw_value: object) -> Tuple[bool, Optional[int], str]:
    """Validate Secure Random Words count strictly in 4..8 without silent coercion."""
    cleaned = str(raw_value).strip()
    if not cleaned:
        return (
            False,
            None,
            f"Word count cannot be empty. Please enter a whole number between {MIN_RANDOM_WORDS} and {MAX_RANDOM_WORDS}.",
        )
    if not cleaned.isdigit() or cleaned not in {"4", "5", "6", "7", "8"}:
        return (
            False,
            None,
            f"Invalid word count '{cleaned}'. Only integers 4, 5, 6, 7, or 8 are allowed.",
        )
    return (True, int(cleaned), "")


def _append_passphrase_suffix(
    base: str,
    add_digits: bool,
    add_symbols: bool,
    safe_syms: List[str],
) -> str:
    """Append optional secrets-generated 3-digit component and trailing symbol cleanly."""
    suffix = ""
    if add_digits:
        digits_str = "".join(secrets.choice(string.digits) for _ in range(3))
        suffix = f"-{digits_str}"
    if add_symbols and safe_syms:
        sym_char = secrets.choice(safe_syms)
        suffix = f"{suffix}{sym_char}"
    return f"{base}{suffix}"


def generate_random_words_batch(
    word_count: int,
    separator: str = "-",
    capitalize: bool = True,
    add_digits: bool = False,
    add_symbols: bool = False,
    quantity: int = 1,
    word_pool: Tuple[str, ...] = CURATED_WORDS,
) -> PassphraseBatch:
    """
    Generate unique passphrases by selecting `word_count` (4-8) words
    independently via `secrets.choice()` from a large curated wordlist.
    Avoids predictable adjacent-repeat or strictly sorted word sequences.
    """
    if not (MIN_RANDOM_WORDS <= word_count <= MAX_RANDOM_WORDS):
        raise ValueError(
            f"Word count must be between {MIN_RANDOM_WORDS} and {MAX_RANDOM_WORDS}."
        )
    if separator not in SEPARATORS:
        raise ValueError(f"Unsupported separator {separator!r}.")
    if not (MIN_QUANTITY <= quantity <= MAX_QUANTITY):
        raise ValueError(f"Quantity must be between {MIN_QUANTITY} and {MAX_QUANTITY}.")
    if len(word_pool) < word_count:
        raise ValueError("Curated wordlist is smaller than requested word count.")

    safe_syms = [c for c in PASSPHRASE_SYMBOLS if c != separator]
    seen = set()
    items: List[str] = []
    max_attempts = max(200, 20 * quantity)

    for _ in range(max_attempts):
        if len(items) >= quantity:
            break

        # Independent random draw per word position with guard against predictable sequences
        chosen: List[str] = []
        for _draw in range(4):
            candidate_words = [secrets.choice(word_pool) for _ in range(word_count)]
            has_adjacent_dup = any(
                candidate_words[i] == candidate_words[i - 1]
                for i in range(1, len(candidate_words))
            )
            is_monotonic = candidate_words == sorted(candidate_words) or (
                candidate_words == sorted(candidate_words, reverse=True)
            )
            chosen = candidate_words
            if not has_adjacent_dup and not is_monotonic:
                break

        formatted = _format_passphrase_tokens(chosen, capitalize)
        base = separator.join(formatted)
        phrase = _append_passphrase_suffix(base, add_digits, add_symbols, safe_syms)
        if phrase not in seen:
            seen.add(phrase)
            items.append(phrase)

    limited_reason = ""
    if len(items) < quantity:
        limited_reason = (
            f"Generated {len(items)} unique random-word passphrases out of {quantity} requested."
        )

    return PassphraseBatch(
        items=items,
        requested=quantity,
        produced=len(items),
        limited_reason=limited_reason,
    )


def estimate_random_passphrase_strength(
    word_count: int,
    pool_size: int = len(CURATED_WORDS),
    has_digits: bool = False,
    has_symbols: bool = False,
) -> StrengthResult:
    """
    Calculate passphrase entropy from exact independent random word selection:
        bits = word_count * log2(pool_size) [+ log2(1000) if digits] [+ log2(len(PASSPHRASE_SYMBOLS)) if symbol]
    Assigns tier strictly from calculated bit entropy without arbitrary labels.
    """
    safe_pool = max(pool_size, 2)
    bits = word_count * math.log2(safe_pool)
    if has_digits:
        bits += math.log2(1000)
    if has_symbols:
        bits += math.log2(len(PASSPHRASE_SYMBOLS))

    if bits < RANDOM_PASSPHRASE_WEAK_MAX_BITS:
        label = "Weak"
    elif bits < RANDOM_PASSPHRASE_FAIR_MAX_BITS:
        label = "Fair"
    elif bits < RANDOM_PASSPHRASE_STRONG_MAX_BITS:
        label = "Strong"
    else:
        label = "Very Strong"

    return StrengthResult(
        label=label,
        fraction=TIER_FRACTIONS[label],
        bits=bits,
        notes=[],
    )


def generate_passphrase_batch(
    entries: List[str],
    separator: str = "-",
    capitalize: bool = True,
    add_digits: bool = False,
    add_symbols: bool = False,
    quantity: int = 1,
) -> PassphraseBatch:
    """
    Generate a batch of unique shuffled passphrases using ALL valid custom entries.

    Never pads exhausted combination spaces with duplicate passphrases.
    """
    if len(entries) < MIN_PASSPHRASE_ENTRIES:
        raise ValueError(
            f"Please add at least {MIN_PASSPHRASE_ENTRIES} distinct entries to build a passphrase."
        )
    if separator not in SEPARATORS:
        raise ValueError(f"Unsupported separator {separator!r}.")
    if not (MIN_QUANTITY <= quantity <= MAX_QUANTITY):
        raise ValueError(f"Quantity must be between {MIN_QUANTITY} and {MAX_QUANTITY}.")

    formatted_base = _format_passphrase_tokens(entries, capitalize)
    entry_count = len(formatted_base)
    sys_rng = secrets.SystemRandom()

    items: List[str] = []
    limited_reason = ""

    # When no random extras are enabled, maximum unique orderings is entry_count!
    if not add_digits and not add_symbols:
        max_possible = math.factorial(entry_count)
        target = min(quantity, max_possible)

        if max_possible <= 120:
            # Enumerate exact unique permutations and shuffle so 100% of n! are obtainable cleanly
            all_unique = list({separator.join(p) for p in itertools.permutations(formatted_base)})
            sys_rng.shuffle(all_unique)
            items = all_unique[:target]
        else:
            seen = set()
            max_attempts = max(200, 20 * target)
            for _ in range(max_attempts):
                if len(items) >= target:
                    break
                shuffled = list(formatted_base)
                sys_rng.shuffle(shuffled)
                phrase = separator.join(shuffled)
                if phrase not in seen:
                    seen.add(phrase)
                    items.append(phrase)

        if len(items) < quantity:
            limited_reason = (
                f"Only {len(items)} unique passphrases are possible with {entry_count} entries. "
                f"Generated {len(items)} of {quantity}. Add more entries or reduce the quantity."
            )
    else:
        seen = set()
        safe_syms = [c for c in PASSPHRASE_SYMBOLS if c != separator]
        max_attempts = max(200, 20 * quantity)
        for _ in range(max_attempts):
            if len(items) >= quantity:
                break
            words = list(formatted_base)
            sys_rng.shuffle(words)
            base = separator.join(words)
            phrase = _append_passphrase_suffix(base, add_digits, add_symbols, safe_syms)
            if phrase not in seen:
                seen.add(phrase)
                items.append(phrase)

        if len(items) < quantity:
            limited_reason = (
                f"Only {len(items)} unique passphrases could be produced with {entry_count} entries. "
                f"Generated {len(items)} of {quantity}. Add more entries or reduce the quantity."
            )

    return PassphraseBatch(
        items=items,
        requested=quantity,
        produced=len(items),
        limited_reason=limited_reason,
    )


# ---------------------------------------------------------------------------
# Predictable Pattern Detection & Honest Strength Estimation
# ---------------------------------------------------------------------------
def _has_sequential_run(text: str, run_length: int = 4) -> bool:
    """Return True if text contains ascending/descending alphanumeric runs >= run_length."""
    lower = text.lower()
    if len(lower) < run_length:
        return False

    for i in range(len(lower) - run_length + 1):
        window = lower[i : i + run_length]
        if not (window.isdigit() or (window.isalpha() and window.isascii())):
            continue
        diffs = [ord(window[j + 1]) - ord(window[j]) for j in range(run_length - 1)]
        if all(d == 1 for d in diffs) or all(d == -1 for d in diffs):
            return True
    return False


def detect_predictable_patterns(text: str) -> List[str]:
    """Detect predictable password/entry patterns and return human-readable reasons."""
    if not text:
        return []

    reasons: List[str] = []
    lower = text.lower()

    if re.search(r"(.)\1\1", text):
        reasons.append("Contains 3+ repeated characters in a row")

    if _has_sequential_run(text, 4):
        reasons.append("Contains sequential letters or digits (e.g. abcd or 1234)")

    if any(seq in lower or seq[::-1] in lower for seq in KEYBOARD_SEQUENCES):
        reasons.append("Contains keyboard row pattern (e.g. qwerty/asdf)")

    matched_words = [w for w in COMMON_PREDICTABLE_WORDS if w in lower]
    if matched_words:
        reasons.append(f"Contains common or familiar word ('{matched_words[0]}')")

    if re.search(r"(19[5-9]\d|20[0-3]\d)", text):
        reasons.append("Contains a 4-digit year (1950-2039)")

    stripped = text.strip()
    if stripped.isdigit() and len(stripped) <= 4:
        reasons.append("Short numeric-only entry (4 digits or fewer)")

    return list(dict.fromkeys(reasons))


def _downgrade_one_tier(label: str) -> str:
    """Shift a strength tier down by one level, stopping at Weak."""
    if label not in TIER_ORDER:
        return label
    idx = TIER_ORDER.index(label)
    return TIER_ORDER[max(0, idx - 1)]


def _cap_tier(label: str, max_label: str) -> str:
    """Cap a strength tier so it does not exceed max_label."""
    if label not in TIER_ORDER or max_label not in TIER_ORDER:
        return label
    idx = min(TIER_ORDER.index(label), TIER_ORDER.index(max_label))
    return TIER_ORDER[idx]


def estimate_password_strength(pw: str) -> StrengthResult:
    """
    Estimate random password strength from length, diversity, and patterns.

    Downgrades by one tier whenever predictable patterns are detected.
    """
    if not pw:
        return StrengthResult("Not Generated", 0.0, 0.0, [])

    length = len(pw)
    categories = 0
    pool_size = 0

    if any(c.islower() for c in pw):
        categories += 1
        pool_size += 26
    if any(c.isupper() for c in pw):
        categories += 1
        pool_size += 26
    if any(c.isdigit() for c in pw):
        categories += 1
        pool_size += 10
    if any(c in DEFAULT_SYMBOLS or not c.isalnum() for c in pw):
        categories += 1
        pool_size += 30

    bits = length * math.log2(max(pool_size, 2))

    if length >= 16 and categories >= 3 and bits >= 80:
        label = "Very Strong"
    elif length >= 12 and categories >= 2 and bits >= 55:
        label = "Strong"
    elif length >= 10 and categories >= 2:
        label = "Fair"
    else:
        label = "Weak"

    notes = detect_predictable_patterns(pw)
    if notes:
        label = _downgrade_one_tier(label)

    return StrengthResult(
        label=label,
        fraction=TIER_FRACTIONS[label],
        bits=bits,
        notes=notes,
    )


def estimate_passphrase_strength(
    entries: List[str],
    has_digits: bool = False,
    has_symbols: bool = False,
    sample_phrase: str = "",
) -> StrengthResult:
    """
    Honestly estimate custom passphrase strength assuming an attacker may already
    know the user's custom entries (entries contribute 0 bits; randomness comes
    from shuffling order plus optional secrets-generated digits/symbols).
    """
    n = max(len(entries), 1)
    bits = math.log2(math.factorial(n))

    if has_digits:
        bits += math.log2(1000)
    if has_symbols:
        bits += math.log2(len(PASSPHRASE_SYMBOLS))

    total_len = len(sample_phrase) if sample_phrase else (
        sum(len(e) for e in entries) + max(0, n - 1) + (4 if has_digits else 0) + (1 if has_symbols else 0)
    )

    predictable_notes: List[str] = []
    for entry in entries:
        for reason in detect_predictable_patterns(entry):
            if reason not in predictable_notes:
                predictable_notes.append(reason)

    if bits < PASSPHRASE_WEAK_MAX_BITS:
        label = "Weak"
    elif bits < PASSPHRASE_FAIR_MAX_BITS:
        label = "Fair"
    elif bits < PASSPHRASE_STRONG_MAX_BITS:
        label = "Strong"
    else:
        if total_len >= PASSPHRASE_VERY_STRONG_MIN_LENGTH and not predictable_notes:
            label = "Very Strong"
        else:
            label = "Strong"

    if total_len < PASSPHRASE_SHORT_WEAK_LENGTH:
        label = _cap_tier(label, "Weak")
    elif total_len < PASSPHRASE_SHORT_FAIR_LENGTH:
        label = _cap_tier(label, "Fair")

    if n < PASSPHRASE_MIN_ENTRIES_FOR_STRONG or predictable_notes:
        label = _cap_tier(label, "Fair")

    return StrengthResult(
        label=label,
        fraction=TIER_FRACTIONS[label],
        bits=bits,
        notes=predictable_notes,
    )

