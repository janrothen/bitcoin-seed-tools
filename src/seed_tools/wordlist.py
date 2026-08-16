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
        self._words = words
        self._indices = {word: index for index, word in enumerate(words)}

    @classmethod
    def from_file(cls, path: Path) -> "Wordlist":
        words = path.read_text(encoding="utf-8").split()
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
            raise ValueError(f"Not a BIP-39 word: {word}") from None

    def binary(self, word: str) -> str:
        return format(self.index(word), f"0{INDEX_BITS}b")

    def contains(self, word: str) -> bool:
        return word in self._indices

    def starting_with(self, prefix: str) -> list[str]:
        return [word for word in self._words if word.startswith(prefix)]


@cache
def wordlist() -> Wordlist:
    """The English wordlist configured in config.toml (loaded once)."""
    return Wordlist.from_file(asset(config()["wordlist"]["file"]))
