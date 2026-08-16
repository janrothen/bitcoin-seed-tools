"""BIP-39 seed phrases: entropy ↔ words, checksum, and XOR."""

import hashlib
import unicodedata
from collections.abc import Sequence

from seed_tools.wordlist import INDEX_BITS, Wordlist, wordlist

# BIP-39 appends ENT/32 checksum bits to ENT entropy bits and splits the result
# into 11-bit groups. Only these five sizes divide evenly.
ENTROPY_SIZES = (16, 20, 24, 28, 32)
WORD_COUNTS = (12, 15, 18, 21, 24)
CHECKSUM_DIVISOR = 32

MIN_PARTS = 2


def normalize(phrase: str | Sequence[str]) -> list[str]:
    """Split a phrase into lowercase words, collapsing any whitespace."""
    if not isinstance(phrase, str):
        phrase = " ".join(phrase)
    return unicodedata.normalize("NFKD", phrase).lower().split()


def entropy_bits(word_count: int) -> int:
    """How many of a phrase's bits are entropy rather than checksum."""
    return word_count * INDEX_BITS * CHECKSUM_DIVISOR // (CHECKSUM_DIVISOR + 1)


def checksum_bits(entropy: bytes) -> str:
    """The leading len(entropy) * 8 / 32 bits of SHA-256(entropy)."""
    length = len(entropy) * 8 // CHECKSUM_DIVISOR
    return _to_bits(hashlib.sha256(entropy).digest())[:length]


def to_entropy(phrase: str | Sequence[str], words: Wordlist | None = None) -> bytes:
    """Decode a seed phrase to its entropy, verifying the checksum."""
    words = wordlist() if words is None else words
    mnemonic = normalize(phrase)
    if len(mnemonic) not in WORD_COUNTS:
        raise ValueError(
            f"Seed phrase must be {_options(WORD_COUNTS)} words, got {len(mnemonic)}"
        )
    bits = "".join(_binary(words, mnemonic))
    split = entropy_bits(len(mnemonic))
    entropy = int(bits[:split], 2).to_bytes(split // 8, "big")
    if not bits.endswith(checksum_bits(entropy)):
        raise ValueError("Invalid checksum — check the words and their order")
    return entropy


def from_entropy(entropy: bytes, words: Wordlist | None = None) -> list[str]:
    """Encode entropy as a seed phrase, appending a freshly computed checksum."""
    words = wordlist() if words is None else words
    if len(entropy) not in ENTROPY_SIZES:
        raise ValueError(
            f"Entropy must be {_options(ENTROPY_SIZES)} bytes, got {len(entropy)}"
        )
    bits = _to_bits(entropy) + checksum_bits(entropy)
    return [
        words.word(int(bits[start : start + INDEX_BITS], 2))
        for start in range(0, len(bits), INDEX_BITS)
    ]


def xor_entropy(parts: Sequence[bytes]) -> bytes:
    """XOR the entropy of two or more parts together.

    Checksum bits play no part — callers decode with `to_entropy` first, so each
    part's own checksum has already been verified, and the combined entropy gets
    a fresh checksum from `from_entropy`.
    """
    if len(parts) < MIN_PARTS:
        raise ValueError(f"Need at least {MIN_PARTS} parts to XOR, got {len(parts)}")
    if len({len(part) for part in parts}) > 1:
        raise ValueError("All parts must have the same word count")
    combined = bytearray(len(parts[0]))
    for part in parts:
        for position, byte in enumerate(part):
            combined[position] ^= byte
    return bytes(combined)


def _binary(words: Wordlist, mnemonic: Sequence[str]) -> list[str]:
    """Each word as 11 bits, reporting the position of the first unknown one.

    The position, never the word: this error is logged, and what was typed here
    is someone's seed backup. Where it went wrong is what the reader needs
    anyway — they have the words in front of them.
    """
    bits = []
    for position, word in enumerate(mnemonic, start=1):
        try:
            bits.append(words.binary(word))
        except ValueError:
            raise ValueError(f"Word {position} is not a BIP-39 word") from None
    return bits


def _to_bits(data: bytes) -> str:
    return "".join(format(byte, "08b") for byte in data)


def _options(values: Sequence[int]) -> str:
    return f"{', '.join(str(value) for value in values[:-1])} or {values[-1]}"
