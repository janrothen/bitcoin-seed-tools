import hashlib

import pytest

from seed_tools.config import asset, config
from seed_tools.wordlist import WORDLIST_SIZE, Wordlist

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


def test_shipped_wordlist_is_the_published_one():
    digest = hashlib.sha256(
        asset(config()["wordlist"]["file"]).read_bytes()
    ).hexdigest()
    assert digest == BIP39_ENGLISH_SHA256
