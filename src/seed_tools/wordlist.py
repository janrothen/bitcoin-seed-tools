from functools import cache
from pathlib import Path

from seed_tools.config import asset, config

WORDLIST_SIZE = 2048
INDEX_BITS = 11


class Wordlist:
    """The BIP-39 wordlist: word ↔ index ↔ 11-bit binary."""

    def __init__(self, words: list[str]) -> None:
        if len(words) != WORDLIST_SIZE:
            raise ValueError(
                f"Wordlist must contain {WORDLIST_SIZE} words, got {len(words)}"
            )
        # The count alone does not make a wordlist, and the two ways it can be
        # wrong while still counting to 2048 both fail silently. A duplicated
        # entry breaks the word ↔ index bijection. A transposed pair keeps the
        # bijection intact, so a phrase encoded against it round-trips cleanly
        # here and is still unrecoverable in every other wallet — the worst
        # possible failure for this tool, and invisible without these two lines.
        if len(set(words)) != WORDLIST_SIZE:
            raise ValueError("Wordlist contains duplicate words")
        if words != sorted(words):
            raise ValueError("Wordlist is not in sorted order")
        self._words = words
        self._indices = {word: index for index, word in enumerate(words)}

    @classmethod
    def from_file(cls, path: Path) -> "Wordlist":
        try:
            words = path.read_text(encoding="utf-8").split()
        except OSError as error:
            # Same reasoning as `config._load`: a missing asset is bad input,
            # reported through `cli.main`, never a traceback.
            raise ValueError(f"Cannot read wordlist: {error}") from None
        return cls(words)

    def __len__(self) -> int:
        return len(self._words)

    def word(self, index: int) -> str:
        if not 0 <= index < WORDLIST_SIZE:
            raise ValueError(f"Index out of range (0-{WORDLIST_SIZE - 1}): {index}")
        return self._words[index]

    def index(self, word: str) -> int:
        try:
            return self._indices[word]
        except KeyError:
            # The word is not repeated back. Errors reach a log, and a word
            # typed at a seed prompt is a near-miss of a real one — naming it
            # pins that position to a single candidate. Callers that know where
            # the word sat (`mnemonic.to_entropy`) report the position instead,
            # the same way `tinyseed.read_pattern` names a position and never a
            # number.
            raise ValueError("Not a BIP-39 word") from None

    def binary(self, word: str) -> str:
        return format(self.index(word), f"0{INDEX_BITS}b")

    def contains(self, word: str) -> bool:
        return word in self._indices

    def starting_with(self, prefix: str) -> list[str]:
        return [word for word in self._words if word.startswith(prefix)]


@cache
def wordlist() -> Wordlist:
    """The English wordlist configured in config.toml (loaded once)."""
    try:
        file = config()["wordlist"]["file"]
    except KeyError as error:
        raise ValueError(
            f"config.toml is missing the {error} entry that locates the wordlist"
        ) from None
    return Wordlist.from_file(asset(file))
