import io

import pytest
from vectors import XOR_12_PARTS, XOR_12_RESULT, XOR_24_PARTS, XOR_24_RESULT

from seed_tools.cli import main


def _feed(monkeypatch, *phrases: str) -> io.StringIO:
    """Queue phrases on stdin for `xor --stdin`; EOF ends the list."""
    stream = io.StringIO("".join(f"{p}\n" for p in phrases))
    monkeypatch.setattr("sys.stdin", stream)
    return stream


def _prompts(monkeypatch, *replies: str) -> list[str]:
    """Drive the interactive prompts with canned replies; returns prompts seen."""
    seen: list[str] = []

    def prompt(text: str) -> str:
        seen.append(text)
        return replies[len(seen) - 1] if len(seen) <= len(replies) else ""

    monkeypatch.setattr("seed_tools.tools.xor._stdin_is_tty", lambda: True)
    monkeypatch.setattr("seed_tools.tools.xor._read_line_hidden", prompt)
    return seen


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


def test_xor_matches_the_published_coldcard_vector(capsys, monkeypatch):
    _feed(monkeypatch, *XOR_24_PARTS)
    assert main(["xor", "--stdin"]) == 0
    numbered = capsys.readouterr().out.splitlines()[:24]
    assert [line.split()[1] for line in numbered] == XOR_24_RESULT.split()


def test_xor_output_is_numbered(capsys, monkeypatch):
    _feed(monkeypatch, *XOR_24_PARTS)
    assert main(["xor", "--stdin"]) == 0
    assert capsys.readouterr().out.startswith(" 1  silent\n 2  toe\n")


def test_xor_ends_with_the_whole_phrase_on_one_line(capsys, monkeypatch):
    _feed(monkeypatch, *XOR_24_PARTS)
    assert main(["xor", "--stdin"]) == 0
    blank, phrase = capsys.readouterr().out.splitlines()[-2:]
    assert blank == ""
    assert phrase == XOR_24_RESULT


def test_xor_phrase_line_is_present_with_the_entropy_flag(capsys, monkeypatch):
    _feed(monkeypatch, *XOR_12_PARTS)
    assert main(["xor", "--stdin", "--entropy"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_12_RESULT


def test_xor_entropy_flag_prints_hex_first(capsys, monkeypatch):
    _feed(monkeypatch, *XOR_24_PARTS)
    assert main(["xor", "--stdin", "--entropy"]) == 0
    first, second = capsys.readouterr().out.splitlines()[:2]
    assert len(first.split()[1]) == 64
    assert second == " 1  silent"


def test_xor_rejects_identical_parts(monkeypatch, caplog):
    _feed(monkeypatch, XOR_24_PARTS[0], XOR_24_PARTS[0])
    assert main(["xor", "--stdin"]) == 2
    assert "all-zero entropy" in caplog.text


def test_xor_rejects_parts_that_cancel_out(monkeypatch, caplog):
    # a XOR a XOR b == b, so the other two parts contribute nothing.
    _feed(monkeypatch, XOR_24_PARTS[0], XOR_24_PARTS[0], XOR_24_PARTS[1])
    assert main(["xor", "--stdin"]) == 2
    assert "identical to one of the parts" in caplog.text


def test_xor_needs_at_least_two_parts(monkeypatch, caplog):
    _feed(monkeypatch, XOR_24_PARTS[0])
    assert main(["xor", "--stdin"]) == 2
    assert "at least 2 parts" in caplog.text


def test_xor_rejects_mixed_word_counts(monkeypatch, caplog):
    _feed(monkeypatch, XOR_24_PARTS[0], XOR_12_PARTS[0])
    assert main(["xor", "--stdin"]) == 2
    assert "same word count" in caplog.text


def test_xor_rejects_a_mistyped_word(monkeypatch, caplog):
    _feed(monkeypatch, XOR_24_PARTS[0].replace("romance", "romanse"), XOR_24_PARTS[1])
    assert main(["xor", "--stdin"]) == 2
    assert "Not a BIP-39 word" in caplog.text


def test_xor_rejects_a_part_whose_checksum_is_wrong(monkeypatch, caplog):
    swapped = " ".join([*XOR_24_PARTS[0].split()[:-1], "zoo"])
    _feed(monkeypatch, swapped, XOR_24_PARTS[1])
    assert main(["xor", "--stdin"]) == 2
    assert "Invalid checksum" in caplog.text


def test_xor_prompts_without_echo_on_a_terminal(monkeypatch):
    prompts = _prompts(monkeypatch, *XOR_24_PARTS)
    assert main(["xor"]) == 0
    assert prompts[:2] == ["Part 1: ", "Part 2: "]
    assert "blank to finish" in prompts[2]


def test_xor_refuses_a_non_terminal_without_the_stdin_flag(monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.tools.xor._stdin_is_tty", lambda: False)
    assert main(["xor"]) == 2
    assert "not a terminal" in caplog.text


def test_xor_names_the_part_that_failed(monkeypatch, caplog):
    swapped = " ".join([*XOR_24_PARTS[1].split()[:-1], "zoo"])
    _feed(monkeypatch, XOR_24_PARTS[0], swapped, XOR_24_PARTS[2])
    assert main(["xor", "--stdin"]) == 2
    assert "Part 2: Invalid checksum" in caplog.text


def test_xor_rejects_a_part_before_reading_the_rest(monkeypatch, caplog):
    swapped = " ".join([*XOR_24_PARTS[0].split()[:-1], "zoo"])
    stream = _feed(monkeypatch, swapped, XOR_24_PARTS[1], XOR_24_PARTS[2])
    assert main(["xor", "--stdin"]) == 2
    assert "Part 1: Invalid checksum" in caplog.text
    # The remaining parts are still unread — the failure surfaced on entry.
    assert stream.readline().startswith("lion misery")


def test_xor_stops_prompting_after_a_bad_part(capsys, monkeypatch, caplog):
    swapped = " ".join([*XOR_24_PARTS[1].split()[:-1], "zoo"])
    prompts = _prompts(monkeypatch, XOR_24_PARTS[0], swapped, XOR_24_PARTS[2])
    assert main(["xor"]) == 2
    assert "Part 2: Invalid checksum" in caplog.text
    # Part 3 is never asked for, and nothing is printed.
    assert prompts == ["Part 1: ", "Part 2: "]
    assert capsys.readouterr().out == ""


def test_xor_aborts_cleanly_on_end_of_input(monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.tools.xor._stdin_is_tty", lambda: True)
    monkeypatch.setattr("seed_tools.tools.xor._read_line_hidden", _raise(EOFError))
    assert main(["xor"]) == 2
    assert "Aborted" in caplog.text


def test_xor_aborts_cleanly_on_interrupt(monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.tools.xor._stdin_is_tty", lambda: True)
    monkeypatch.setattr(
        "seed_tools.tools.xor._read_line_hidden", _raise(KeyboardInterrupt)
    )
    assert main(["xor"]) == 2
    assert "Aborted" in caplog.text


def test_xor_prompts_on_stderr_with_the_stdin_flag(capsys, monkeypatch):
    _feed(monkeypatch, *XOR_12_PARTS)
    assert main(["xor", "--stdin"]) == 0
    captured = capsys.readouterr()
    assert captured.err.startswith("Part 1: Part 2: ")
    # Prompts stay out of stdout, which carries the result.
    assert "Part 1:" not in captured.out


def _raise(error: type[BaseException]):
    def read(_prompt: str) -> str:
        raise error

    return read
