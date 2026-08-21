import hashlib

import pytest

from seed_tools.config import asset, config
from seed_tools.wordlist import UNIQUE_PREFIX, WORDLIST_SIZE, Wordlist

# The published BIP-39 English wordlist. Pinned because every other check in
# this file passes just as happily against a wrong list: nothing here can tell
# that 2048 sorted unique words are *the* 2048 words, and a phrase encoded
# against a substituted list round-trips cleanly and is still unrecoverable in
# every other wallet.
BIP39_ENGLISH_SHA256 = (
    "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"
)


def _entries(words: Wordlist) -> list[str]:
    return [words.word(index) for index in range(len(words))]


def test_wordlist_has_2048_words(words):
    assert len(words) == WORDLIST_SIZE


def test_first_and_last_word(words):
    assert words.word(0) == "abandon"
    assert words.word(WORDLIST_SIZE - 1) == "zoo"


def test_index_round_trip(words):
    assert words.index(words.word(1337)) == 1337


def test_binary_is_11_bits(words):
    assert words.binary("abandon") == "00000000000"
    assert words.binary("zoo") == "11111111111"


def test_unknown_word_raises(words):
    with pytest.raises(ValueError, match="Not a BIP-39 word"):
        words.index("bitcoin")


def test_index_out_of_range_raises(words):
    with pytest.raises(ValueError, match="Index out of range"):
        words.word(WORDLIST_SIZE)


def test_starting_with_returns_all_matches(words):
    assert words.starting_with("abstr") == ["abstract"]
    assert words.starting_with("zzz") == []


def test_wrong_size_rejected():
    with pytest.raises(ValueError, match="must contain 2048 words"):
        Wordlist(["abandon", "ability"])


def test_duplicate_word_rejected(words):
    """A repeated entry breaks the word ↔ index bijection the encoding rests on."""
    entries = _entries(words)
    entries[1] = entries[0]
    with pytest.raises(ValueError, match="duplicate words"):
        Wordlist(entries)


def test_unsorted_wordlist_rejected(words):
    """A transposed pair keeps the bijection, so only the order gives it away.

    The phrase it produces round-trips cleanly here and matches no other BIP-39
    implementation — the one corruption that is otherwise entirely silent.
    """
    entries = _entries(words)
    entries[0], entries[1] = entries[1], entries[0]
    with pytest.raises(ValueError, match="not in sorted order"):
        Wordlist(entries)


def test_missing_wordlist_file_is_bad_input_not_a_crash(tmp_path):
    """A deleted or misplaced asset must report cleanly, not traceback."""
    with pytest.raises(ValueError, match="Cannot read wordlist"):
        Wordlist.from_file(tmp_path / "missing.txt")


def test_shipped_wordlist_is_the_published_one():
    digest = hashlib.sha256(
        asset(config()["wordlist"]["file"]).read_bytes()
    ).hexdigest()
    assert digest == BIP39_ENGLISH_SHA256


def test_the_first_four_letters_identify_a_word(words):
    """What lets a backup print four letters and stop — checked, not assumed.

    `expand` rests on this: four letters off a pill or a stamped plate come back
    as exactly one word. If a wordlist were ever swapped for one without the
    property, every truncated backup made against it would be ambiguous.
    """
    entries = _entries(words)
    prefixes = {word[:UNIQUE_PREFIX] for word in entries}
    assert len(prefixes) == len(entries)


def test_every_long_word_is_recovered_from_its_first_four_letters(words):
    """The round trip a truncated backup makes, for all 2048 words at once."""
    for word in _entries(words):
        if len(word) >= UNIQUE_PREFIX:
            assert words.starting_with(word[:UNIQUE_PREFIX]) == [word]


def test_a_short_word_prints_whole_and_sorts_ahead_of_what_it_starts(words):
    """Why a three-letter print is not ambiguous the way three letters are.

    A word shorter than four letters is printed in full, so the letters *are*
    the word — even though longer words begin with them. Sorted, the word itself
    comes first, which is what `expand` says out loud when `--pick` is used.
    """
    for word in _entries(words):
        if len(word) < UNIQUE_PREFIX:
            assert words.starting_with(word)[0] == word


def test_shortest_word_is_measured_from_the_list(words):
    assert words.shortest_word() == min(len(word) for word in _entries(words))


def test_shortest_english_word_is_three_letters(words):
    """The floor `expand` enforces: fewer letters is a word missing letters."""
    assert words.shortest_word() == 3
