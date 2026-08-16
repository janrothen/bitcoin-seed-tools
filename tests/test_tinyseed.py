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


@pytest.mark.parametrize("style", sorted(tinyseed.STYLES))
def test_reading_a_pattern_back_recovers_every_plate_number(style):
    """The round trip has to hold for all 2048 rows, not a sample of them."""
    for number in range(tinyseed.MIN_NUMBER, tinyseed.MAX_NUMBER + 1):
        assert tinyseed.read_pattern(tinyseed.pattern(number, style)) == number


def test_known_circle_patterns_read_back_to_their_words(words):
    assert tinyseed.read_word(FIRST, words) == "abandon"
    assert tinyseed.read_word(SECOND, words) == "ability"
    assert tinyseed.read_word(LAST, words) == "zoo"


def test_every_notation_reads_back_to_the_same_word(words):
    """Circles, binary and the typeable stand-ins are one pattern, written three ways."""
    for written in ("○○○○○○○●○○○●", "000000010001", ".......#...#", "oooooooXooo#"):
        assert tinyseed.read_word(written, words) == "acoustic"


def test_notations_may_be_mixed_within_a_row(words):
    """The glyph sets do not overlap, so a half-typed row is still unambiguous."""
    assert tinyseed.read_word("○○○○○○○1ooo#", words) == "acoustic"


def test_spaces_group_a_row_without_changing_it(words):
    assert tinyseed.read_pattern("○○○ ○○○ ○○○ ○○●") == 1
    assert tinyseed.read_word("0000 0001 0001", words) == "acoustic"


@pytest.mark.parametrize("written", ["○○○○○○○○○○●", "○○○○○○○○○○○●○", ""])
def test_reading_rejects_a_row_that_is_not_twelve_positions(written):
    with pytest.raises(ValueError, match="Expected 12 positions"):
        tinyseed.read_pattern(written)


def test_a_rejected_row_is_not_repeated_back_in_the_error():
    """Errors are logged, and a row one hole short is still most of a word."""
    almost = "○○○○○○○●○○●"
    with pytest.raises(ValueError) as raised:
        tinyseed.read_pattern(almost)
    assert almost not in str(raised.value)


def test_reading_rejects_a_mark_it_does_not_know_and_says_where():
    with pytest.raises(ValueError, match="position 5: 'q'"):
        tinyseed.read_pattern("○○○○q○○○○○○●")


def test_reading_rejects_a_row_with_no_holes():
    """An all-blank row means a skipped row, not a word — no word is 0."""
    with pytest.raises(ValueError, match="no holes"):
        tinyseed.read_pattern(tinyseed.CIRCLE_OFF * tinyseed.PLATE_BITS)


def test_reading_rejects_a_pattern_past_the_end_of_the_wordlist():
    """12 bits reach 4095; a fifth of what a plate can hold names no word."""
    with pytest.raises(ValueError, match="past the end of the wordlist"):
        tinyseed.read_pattern("●●●●●●●●●●●●")


def test_an_out_of_range_row_is_not_spelled_out_by_its_number():
    """The number *is* the row: printing it writes the transcription to the log.

    A real row with one hole too many at the front lands here, and it is still
    one bit off the word it was meant to be.
    """
    # `silent` is 1604; a stray hole at position 1 makes it 3652.
    with pytest.raises(ValueError) as raised:
        tinyseed.read_pattern("●●●○○●○○○●○○")
    message = str(raised.value)
    assert "3652" not in message
    assert format(3652, "012b") not in message


def test_every_glyph_that_can_be_drawn_can_also_be_read():
    """A style added later must not be printable but unreadable."""
    for zero, one in tinyseed.STYLES.values():
        assert zero in tinyseed.READ_OFF
        assert one in tinyseed.READ_ON


def test_the_off_and_on_marks_never_overlap():
    """What makes detecting the notation safe rather than a guess."""
    assert not tinyseed.READ_OFF & tinyseed.READ_ON


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
