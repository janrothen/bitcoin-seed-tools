import pytest

from seed_tools import tinyseed
from seed_tools.config import asset, config

# Read off the printable card in assets/bip-0039-tinyseed_io.pdf.
FIRST = "○○○○○○○○○○○●"
SECOND = "○○○○○○○○○○●○"
LAST = "●○○○○○○○○○○○"


def test_plate_numbers_are_the_index_plus_one(words):
    assert tinyseed.plate_number("abandon", words) == 1
    assert tinyseed.plate_number("zoo", words) == 2048
    assert tinyseed.plate_number("aim", words) == words.index("aim") + 1


def test_known_circle_patterns(words):
    assert tinyseed.dots("abandon", words=words) == FIRST
    assert tinyseed.dots("ability", words=words) == SECOND
    assert tinyseed.dots("zoo", words=words) == LAST


def test_known_binary_patterns(words):
    assert tinyseed.dots("abandon", "binary", words) == "000000000001"
    assert tinyseed.dots("ability", "binary", words) == "000000000010"
    assert tinyseed.dots("zoo", "binary", words) == "100000000000"


def test_pattern_is_the_bip39_index_shifted_by_one(words):
    # The 11-bit index the rest of BIP-39 uses is *not* what TinySeed punches.
    for word in ("abandon", "aim", "language", "zoo"):
        shifted = format(words.index(word) + 1, "012b")
        assert tinyseed.dots(word, "binary", words) == shifted


@pytest.mark.parametrize("style", sorted(tinyseed.STYLES))
def test_every_pattern_is_twelve_positions_of_the_right_glyphs(style):
    zero, one = tinyseed.STYLES[style]
    for number in (tinyseed.MIN_NUMBER, 1234, tinyseed.MAX_NUMBER):
        drawn = tinyseed.pattern(number, style)
        assert len(drawn) == tinyseed.PLATE_BITS
        assert set(drawn) <= {zero, one}


@pytest.mark.parametrize("number", [0, 2049, -1])
def test_pattern_rejects_a_number_off_the_plate(number):
    with pytest.raises(ValueError, match="out of range"):
        tinyseed.pattern(number)


def test_pattern_rejects_an_unknown_style():
    with pytest.raises(ValueError, match="Unknown style"):
        tinyseed.pattern(1, "dots")


def test_table_covers_the_whole_wordlist(words):
    rows = tinyseed.table(words)
    assert len(rows) == len(words)
    assert rows[0] == (1, "abandon", "000000000001", FIRST)
    assert rows[-1] == (2048, "zoo", "100000000000", LAST)


def test_table_text_pads_the_word_to_a_fixed_width(words):
    lines = tinyseed.table_text(words).splitlines()
    assert lines[0] == "1\tabandon \t000000000001\t" + FIRST
    assert lines[1] == "2\tability \t000000000010\t" + SECOND
    # An eight-letter word gets no padding, and still ends at the same column.
    assert lines[16] == "17\tacoustic\t000000010001\t○○○○○○○●○○○●"


def test_table_text_columns_line_up_at_every_tab_width(words):
    """Padding, not tabbing, is what squares the column up for the longest words."""
    for line in tinyseed.table_text(words).splitlines():
        _, word, binary, circles = line.split("\t")
        assert len(word) == tinyseed.WORD_WIDTH
        assert len(binary) == len(circles) == tinyseed.PLATE_BITS


def test_table_matches_the_checked_in_asset(words):
    """The shipped table is generated, so pin it — a drifted asset is a wrong plate."""
    path = asset(config()["tinyseed"]["file"])
    assert path.read_text(encoding="utf-8") == tinyseed.table_text(words)
