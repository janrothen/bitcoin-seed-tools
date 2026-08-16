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

# A phrase one word short of any valid length — what `final_words` completes.
PARTIAL_WORD_COUNTS = tuple(count - 1 for count in WORD_COUNTS)

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


def final_word_entropy_bits(word_count: int) -> int:
    """How many entropy bits the last word of a phrase carries, beside the checksum.

    `word_count` is the length of the finished phrase. The rest of the word's 11
    bits are the checksum, so this is never 0: the last word is not a checksum
    word, and the choice of which one to use is a choice of entropy.
    """
    return entropy_bits(word_count) - (word_count - 1) * INDEX_BITS


def final_words(
    phrase: str | Sequence[str], words: Wordlist | None = None
) -> list[str]:
    """Every last word that completes a phrase with a valid checksum, sorted.

    The last word is not a checksum on its own. Only its trailing ENT/32 bits
    are; the ones before them are the final bits of the entropy. So a phrase one
    word short has 2**`final_word_entropy_bits` completions — 128 for a 12-word
    phrase, 8 for a 24-word one — and each is a valid phrase for a *different*
    wallet. Which one to take is the caller's problem, not this function's.
    """
    words = wordlist() if words is None else words
    mnemonic = normalize(phrase)
    if len(mnemonic) not in PARTIAL_WORD_COUNTS:
        raise ValueError(
            f"Seed phrase must be {_options(PARTIAL_WORD_COUNTS)} words — every "
            f"word but the last — got {len(mnemonic)}"
        )
    word_count = len(mnemonic) + 1
    prefix = "".join(_binary(words, mnemonic))
    split = entropy_bits(word_count)
    # The same count the tools quote as coin flips, from the same expression —
    # a list of 2**missing candidates and the advice on how to draw one of them
    # cannot end up describing different numbers of bits.
    missing = final_word_entropy_bits(word_count)
    # Each candidate is built by encoding a whole phrase and keeping its last
    # word, rather than assembling that word from the tail bits and a checksum
    # here. The completions then come off exactly the path that encodes every
    # other phrase in this project, so they cannot drift away from it.
    return sorted(
        from_entropy(
            int(prefix + format(tail, f"0{missing}b"), 2).to_bytes(split // 8, "big"),
            words,
        )[-1]
        for tail in range(1 << missing)
    )


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
