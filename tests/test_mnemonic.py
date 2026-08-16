import pytest
from vectors import (
    BIP39_VECTORS,
    XOR_12_PARTS,
    XOR_12_RESULT,
    XOR_24_PARTS,
    XOR_24_RESULT,
)

from seed_tools.mnemonic import (
    ENTROPY_SIZES,
    WORD_COUNTS,
    checksum_bits,
    entropy_bits,
    from_entropy,
    normalize,
    to_entropy,
    xor_entropy,
)


def test_entropy_bits_leaves_room_for_the_checksum():
    assert entropy_bits(12) == 128
    assert entropy_bits(24) == 256


def test_checksum_length_is_one_bit_per_32_entropy_bits():
    assert len(checksum_bits(bytes(16))) == 4
    assert len(checksum_bits(bytes(32))) == 8


def test_normalize_lowercases_and_collapses_whitespace():
    assert normalize("  Abandon\tABOUT\n legal ") == ["abandon", "about", "legal"]


def test_normalize_accepts_a_word_sequence():
    assert normalize(["Abandon", "about"]) == ["abandon", "about"]


@pytest.mark.parametrize(("entropy_hex", "mnemonic"), BIP39_VECTORS)
def test_published_bip39_vectors_round_trip(words, entropy_hex, mnemonic):
    entropy = bytes.fromhex(entropy_hex)
    assert from_entropy(entropy, words) == mnemonic.split()
    assert to_entropy(mnemonic, words) == entropy


@pytest.mark.parametrize("size", ENTROPY_SIZES)
def test_every_entropy_size_round_trips(words, size):
    for entropy in (bytes(size), bytes([0xFF] * size), bytes(range(size))):
        assert to_entropy(from_entropy(entropy, words), words) == entropy


@pytest.mark.parametrize("size", ENTROPY_SIZES)
def test_entropy_size_maps_to_expected_word_count(words, size):
    assert (
        len(from_entropy(bytes(size), words)) == WORD_COUNTS[ENTROPY_SIZES.index(size)]
    )


def test_coldcard_24_word_vector(words):
    parts = [to_entropy(part, words) for part in XOR_24_PARTS]
    assert from_entropy(xor_entropy(parts), words) == XOR_24_RESULT.split()


def test_coldcard_12_word_vector(words):
    parts = [to_entropy(part, words) for part in XOR_12_PARTS]
    assert from_entropy(xor_entropy(parts), words) == XOR_12_RESULT.split()


def test_xor_is_order_independent(words):
    parts = [to_entropy(part, words) for part in XOR_24_PARTS]
    assert xor_entropy(parts[::-1]) == xor_entropy(parts)


def test_xor_is_self_inverse(words):
    a, b = (to_entropy(part, words) for part in XOR_24_PARTS[:2])
    assert xor_entropy([xor_entropy([a, b]), b]) == a


def test_a_single_flipped_bit_changes_the_phrase(words):
    entropy = bytes(range(32))
    flipped = bytes([entropy[0] ^ 0x01, *entropy[1:]])
    assert from_entropy(flipped, words) != from_entropy(entropy, words)


def test_wrong_checksum_rejected(words):
    # "art" is the correct 24th word for all-zero entropy; "arrive" is not.
    phrase = " ".join(["abandon"] * 23 + ["arrive"])
    with pytest.raises(ValueError, match="Invalid checksum"):
        to_entropy(phrase, words)


def test_unknown_word_rejected(words):
    phrase = " ".join(["abandon"] * 23 + ["bitcoin"])
    with pytest.raises(ValueError, match="Word 24 is not a BIP-39 word"):
        to_entropy(phrase, words)


def test_unknown_word_error_does_not_repeat_the_word(words):
    """The position is the diagnostic; the word itself is a piece of a backup."""
    phrase = " ".join(["abandon"] * 23 + ["bitcoin"])
    with pytest.raises(ValueError) as caught:
        to_entropy(phrase, words)
    assert "bitcoin" not in str(caught.value)


def test_bad_word_count_rejected(words):
    with pytest.raises(ValueError, match="must be 12, 15, 18, 21 or 24 words"):
        to_entropy("abandon abandon abandon", words)


def test_bad_entropy_length_rejected(words):
    with pytest.raises(ValueError, match="must be 16, 20, 24, 28 or 32 bytes"):
        from_entropy(bytes(17), words)


def test_xor_needs_two_parts():
    with pytest.raises(ValueError, match="Need at least 2 parts"):
        xor_entropy([bytes(32)])


def test_xor_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="same word count"):
        xor_entropy([bytes(32), bytes(16)])
