import pytest

from seed_tools.config import asset, config
from seed_tools.wordlist import Wordlist


@pytest.fixture(scope="session")
def words() -> Wordlist:
    """The real English wordlist from assets/ — it ships with the repo."""
    return Wordlist.from_file(asset(config()["wordlist"]["file"]))
