"""TinySeed plate patterns: BIP-39 word ↔ 12-bit punch pattern.

A TinySeed plate stores a seed phrase as punched holes rather than letters. It
numbers the wordlist 1-2048 and punches that number in 12 bits, most significant
bit first. Note this is *not* the 11-bit index the rest of BIP-39 uses — it is
that index plus one, and only `zoo` (2048) sets the leading bit.
"""

from seed_tools.wordlist import WORDLIST_SIZE, Wordlist, wordlist

CIRCLE_OFF = "○"  # U+25CB WHITE CIRCLE — leave this position alone
CIRCLE_ON = "●"  # U+25CF BLACK CIRCLE — punch this position

# 2048 needs 12 bits, so every pattern is 12 positions wide.
PLATE_BITS = 12

# Which pair of glyphs a pattern is drawn with: (zero, one).
STYLES = {
    "circles": (CIRCLE_OFF, CIRCLE_ON),
    "binary": ("0", "1"),
}
DEFAULT_STYLE = "circles"

MIN_NUMBER = 1
MAX_NUMBER = WORDLIST_SIZE

# The longest BIP-39 English word. Padding to it keeps a column of words square.
WORD_WIDTH = 8


def plate_number(word: str, words: Wordlist | None = None) -> int:
    """The 1-based number TinySeed prints next to a word."""
    words = wordlist() if words is None else words
    return words.index(word) + 1


def pattern(number: int, style: str = DEFAULT_STYLE) -> str:
    """Draw a plate number as its 12-position punch pattern."""
    if style not in STYLES:
        raise ValueError(
            f"Unknown style: {style} (expected {' or '.join(sorted(STYLES))})"
        )
    if not MIN_NUMBER <= number <= MAX_NUMBER:
        raise ValueError(
            f"Plate number out of range ({MIN_NUMBER}-{MAX_NUMBER}): {number}"
        )
    zero, one = STYLES[style]
    return "".join(
        one if bit == "1" else zero for bit in format(number, f"0{PLATE_BITS}b")
    )


def dots(word: str, style: str = DEFAULT_STYLE, words: Wordlist | None = None) -> str:
    """The punch pattern for a BIP-39 word."""
    return pattern(plate_number(word, words), style)


def table_text(words: Wordlist | None = None) -> str:
    """The translation table as the text of the shipped asset file.

    The word is padded to a fixed width rather than merely tabbed past: the 88
    eight-letter words would otherwise spill over the next tab stop and leave
    the binary column zigzagging in a plain editor.
    """
    return "".join(
        f"{number}\t{word:<{WORD_WIDTH}}\t{binary}\t{circles}\n"
        for number, word, binary, circles in table(words)
    )


def table(words: Wordlist | None = None) -> list[tuple[int, str, str, str]]:
    """The whole translation table as (number, word, binary, circles) rows."""
    words = wordlist() if words is None else words
    rows = []
    for index in range(len(words)):
        number = index + MIN_NUMBER
        rows.append(
            (
                number,
                words.word(index),
                pattern(number, "binary"),
                pattern(number, "circles"),
            )
        )
    return rows
