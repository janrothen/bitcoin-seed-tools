from seed_tools.config import asset, config, project_root


def test_project_root_contains_config_file():
    assert (project_root() / "config.toml").is_file()


def test_config_declares_wordlist_files():
    wordlist = config()["wordlist"]
    assert asset(wordlist["file"]).is_file()
    assert asset(wordlist["printable_file"]).is_file()


def test_config_is_cached():
    assert config() is config()
