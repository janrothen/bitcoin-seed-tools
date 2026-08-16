import pytest

from seed_tools.config import asset, config, project_root


def test_project_root_contains_config_file():
    assert (project_root() / "config.toml").is_file()


def test_config_declares_wordlist_files():
    wordlist = config()["wordlist"]
    assert asset(wordlist["file"]).is_file()
    assert asset(wordlist["printable_file"]).is_file()


def test_config_declares_tinyseed_files():
    tinyseed = config()["tinyseed"]
    assert asset(tinyseed["file"]).is_file()
    assert asset(tinyseed["reference_file"]).is_file()


def test_config_is_cached():
    assert config() is config()


def test_missing_config_is_bad_input_not_a_crash(monkeypatch, tmp_path):
    """A wrong BITCOIN_SEED_TOOLS_HOME must report cleanly, not traceback."""
    monkeypatch.setattr("seed_tools.config._PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("seed_tools.config._config", None)
    with pytest.raises(ValueError, match="BITCOIN_SEED_TOOLS_HOME"):
        config()
