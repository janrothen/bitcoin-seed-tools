import pytest

from seed_tools.wordlist import Wordlist, wordlist


@pytest.fixture(scope="session")
def words() -> Wordlist:
    """The wordlist the tools themselves use — loaded once through the cache."""
    return wordlist()
