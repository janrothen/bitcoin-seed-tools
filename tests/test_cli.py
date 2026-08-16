import pytest

from seed_tools.cli import main


def test_lookup_by_word(capsys):
    assert main(["lookup", "abandon"]) == 0
    assert capsys.readouterr().out == "   0  00000000000  abandon\n"


def test_lookup_by_index(capsys):
    assert main(["lookup", "2047"]) == 0
    assert "zoo" in capsys.readouterr().out


def test_lookup_by_prefix_lists_all_matches(capsys):
    assert main(["lookup", "zeb"]) == 0
    assert capsys.readouterr().out.count("\n") == 1


def test_unknown_term_reports_and_exits_nonzero(capsys):
    assert main(["lookup", "bitcoin"]) == 1
    assert "no match" in capsys.readouterr().out


def test_out_of_range_index_reports_no_match(capsys):
    assert main(["lookup", "2048"]) == 1
    assert "no match" in capsys.readouterr().out


def test_value_error_is_reported_not_raised(monkeypatch, caplog):
    def boom(_args):
        raise ValueError("bad input")

    monkeypatch.setattr("seed_tools.tools.lookup.run", boom)
    assert main(["lookup", "abandon"]) == 2
    assert "bad input" in caplog.text


def test_missing_command_exits():
    with pytest.raises(SystemExit):
        main([])
