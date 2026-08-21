"""The demo files in `examples/` still say what `examples/README.md` claims.

They exist to be run by hand, which is exactly why nothing else would notice
them going stale — a demo that decodes to the wrong phrase teaches the wrong
thing about the tool that is supposed to catch wrong phrases.
"""

import io
import re
from pathlib import Path

import pytest
from vectors import XOR_12_RESULT, XOR_24_RESULT

from seed_tools.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _piped(monkeypatch, name: str) -> None:
    """Feed an example file to a tool the way `--stdin < file` does."""
    text = (EXAMPLES / name).read_text(encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: False)


@pytest.mark.parametrize(
    ("name", "phrase"),
    [
        ("plate-12.txt", XOR_12_RESULT),
        ("plate-12-typed.txt", XOR_12_RESULT),
        ("plate-24.txt", XOR_24_RESULT),
    ],
)
def test_example_plate_reads_back_to_its_documented_phrase(capsys, name, phrase):
    assert main(["tinyseed", "--reverse", "--file", str(EXAMPLES / name)]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == phrase


def test_the_misread_example_still_fails_the_checksum(capsys, caplog):
    """The one demo that must not work — a hole in the wrong place, caught."""
    plate = EXAMPLES / "plate-24-misread.txt"
    assert main(["tinyseed", "--reverse", "--file", str(plate)]) == 2
    assert "Invalid checksum" in caplog.text
    assert capsys.readouterr().out == ""


def test_the_misread_example_differs_from_the_good_one_by_one_hole(capsys):
    """Otherwise it demonstrates something else — a bad row, or a second slip."""
    good = (EXAMPLES / "plate-24.txt").read_text(encoding="utf-8")
    bad = (EXAMPLES / "plate-24-misread.txt").read_text(encoding="utf-8")
    assert len(good) == len(bad)
    assert sum(a != b for a, b in zip(good, bad, strict=True)) == 1


def test_the_backup_example_punches_the_phrase_it_documents(capsys, monkeypatch):
    """Wrapped four words to a line, and still one phrase — that is its point."""
    _piped(monkeypatch, "backup.txt")
    assert main(["tinyseed", "--stdin"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in lines] == XOR_24_RESULT.split()


def test_the_parts_example_combines_to_the_backup_phrase(capsys, monkeypatch):
    """The circle the examples make: parts XOR to the phrase the plate holds."""
    _piped(monkeypatch, "parts.txt")
    assert main(["xor", "--stdin"]) == 0
    out = capsys.readouterr()
    assert out.out.splitlines()[-1] == XOR_24_RESULT
    # The blank lines between the parts are gaps, not ends: all three are read.
    assert "Combined 3 parts of 24 words." in out.err


def test_the_23_word_example_is_completed_by_the_backup_phrase(capsys, monkeypatch):
    _piped(monkeypatch, "first-23-words.txt")
    assert main(["checksum", "--stdin"]) == 0
    candidates = [line.split()[1] for line in capsys.readouterr().out.splitlines()]
    assert len(candidates) == 8
    assert XOR_24_RESULT.split()[-1] in candidates


def test_the_readme_only_points_at_files_that_exist():
    """Every command in the README runs as written, or it teaches a broken one."""
    readme = (EXAMPLES.parent / "README.md").read_text(encoding="utf-8")
    named = set(re.findall(r"examples/[\w.-]+", readme))
    assert named, "the README no longer mentions the examples at all"
    for path in sorted(named):
        assert (EXAMPLES.parent / path).exists(), path


def test_every_example_file_is_covered_by_a_test():
    """A new example without a test is one nobody notices going stale."""
    documented = {
        "README.md",
        "backup.txt",
        "first-23-words.txt",
        "parts.txt",
        "plate-12-typed.txt",
        "plate-12.txt",
        "plate-24-misread.txt",
        "plate-24.txt",
    }
    assert {path.name for path in EXAMPLES.iterdir()} == documented
