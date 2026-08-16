import os
import tomllib
from pathlib import Path

# Prefer an explicit env var so regular (non-editable) installs work correctly.
# Falls back to three-levels-up, which is correct for editable dev installs
# (src/seed_tools/config.py → project root), but wrong for site-packages installs.
_PROJECT_ROOT = (
    Path(os.environ["BITCOIN_SEED_TOOLS_HOME"])
    if "BITCOIN_SEED_TOOLS_HOME" in os.environ
    else Path(__file__).parent.parent.parent
)

_config: dict | None = None


def _load() -> dict:
    path = _PROJECT_ROOT / "config.toml"
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except OSError as error:
        # A missing or unreadable config is bad input to the process, not a
        # crash: raise the ValueError that `cli.main` reports like any other.
        raise ValueError(
            f"Cannot read {path}: {error} — set BITCOIN_SEED_TOOLS_HOME to the "
            "directory that holds config.toml and assets/"
        ) from None


def config() -> dict:
    global _config
    if _config is None:
        _config = _load()
    return _config


def project_root() -> Path:
    return _PROJECT_ROOT


def asset(relative_path: str) -> Path:
    """Resolve a path from config.toml against the project root."""
    return _PROJECT_ROOT / relative_path
