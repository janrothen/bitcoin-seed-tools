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

# One plate holds 12 rows; a 24-word phrase spans two plates.
PLATE_ROWS = 12

# Which pair of glyphs a pattern is drawn with: (zero, one).
STYLES = {
    "circles": (CIRCLE_OFF, CIRCLE_ON),
    "binary": ("0", "1"),
}
DEFAULT_STYLE = "circles"

# Typeable stand-ins accepted when reading a plate back — ● and ○ are not on a
# keyboard. Built from STYLES, so whatever this module can draw it can also read.
EXTRA_OFF = frozenset({".", "o", "O"})
EXTRA_ON = frozenset({"#", "x", "X"})
READ_OFF = frozenset(zero for zero, _ in STYLES.values()) | EXTRA_OFF
READ_ON = frozenset(one for _, one in STYLES.values()) | EXTRA_ON

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


def read_pattern(text: str) -> int:
    """The plate number a punch pattern stands for — the inverse of `pattern`.

    Strict on purpose: a row that is not 12 positions is an error, never a
    guess. The checksum catches only about 15 misreads in 16, so it cannot be
    the only thing standing between a slip of the eye and a wrong word.
    """
    # Whitespace is grouping, not content: ○○○ ○○○ ○○○ ○●● is easier to count.
    marks = "".join(text.split())
    if len(marks) != PLATE_BITS:
        # The count, not the marks: an error is logged, and a row one hole short
        # is still eleven twelfths of a word nobody should write to a log file.
        raise ValueError(f"Expected {PLATE_BITS} positions, got {len(marks)}")

    bits = []
    for position, mark in enumerate(marks, start=1):
        if mark in READ_ON:
            bits.append("1")
        elif mark in READ_OFF:
            bits.append("0")
        else:
            # The position, never the mark: like the errors above and below,
            # this one is logged, and what was really typed at a --reverse
            # prompt could be anything — including a word of a seed phrase
            # fed to the wrong tool.
            raise ValueError(f"Not a punch mark at position {position}")

    number = int("".join(bits), 2)
    if number < MIN_NUMBER:
        # Its own message rather than the range error below: an unpunched row is
        # a row that was skipped or misaligned, not a number that came out small.
        raise ValueError("Row has no holes — every plate row has at least one")
    if number > MAX_NUMBER:
        # 12 bits reach 4095, but the wordlist stops at 2048, so a fifth of the
        # patterns a plate can physically hold name no word at all.
        #
        # Says which position gives it away, never the number: the number *is*
        # the row, and a row one hole off a real one still spells out that word.
        # Same reasoning as the length check above — this is logged too.
        raise ValueError(
            f"Pattern is past the end of the wordlist ({MIN_NUMBER}-{MAX_NUMBER})"
            " — position 1 is punched, which only zoo (2048) does"
        )
    return number


def read_word(text: str, words: Wordlist | None = None) -> str:
    """The BIP-39 word a punch pattern stands for — the inverse of `dots`."""
    words = wordlist() if words is None else words
    # Back over the same off-by-one `plate_number` adds: the plate counts from 1.
    return words.word(read_pattern(text) - MIN_NUMBER)


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
