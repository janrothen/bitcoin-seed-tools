import pytest

from seed_tools.wordlist import WORDLIST_SIZE, Wordlist


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
