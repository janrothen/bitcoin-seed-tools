import io

import pytest
from vectors import XOR_12_PARTS, XOR_12_RESULT, XOR_24_PARTS, XOR_24_RESULT

from seed_tools import tinyseed
from seed_tools.cli import main
from seed_tools.mnemonic import from_entropy
from seed_tools.wordlist import wordlist


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

    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr("seed_tools.phrase_input.read_line_hidden", prompt)
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


def test_lookup_accepts_a_word_typed_uppercase(capsys):
    """The other subcommands lowercase their input; lookup must agree with them."""
    assert main(["lookup", "ABANDON"]) == 0
    assert capsys.readouterr().out == "   0  00000000000  abandon\n"


def test_lookup_succeeds_when_any_term_matches(capsys):
    """Like grep: finding anything is success, even if another term missed."""
    assert main(["lookup", "abandon", "bitcoin"]) == 0
    out = capsys.readouterr().out
    assert "abandon" in out
    assert "bitcoin: no match" in out


def test_lookup_of_a_word_that_prefixes_others_lists_them_all(capsys):
    """`car` is a word, but a smudged backup needs carbon..cart offered too."""
    assert main(["lookup", "car"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].endswith("  car")
    assert len(lines) == 7  # car, carbon, card, cargo, carpet, carry, cart


def test_lookup_of_an_empty_term_reports_no_match(capsys):
    """Every word starts with "" — an unset shell variable must not match all."""
    assert main(["lookup", ""]) == 1
    assert "no match" in capsys.readouterr().out


def test_lookup_of_an_absurdly_long_index_reports_no_match(capsys):
    """Past CPython's int-parsing limit; out of range either way."""
    assert main(["lookup", "9" * 5000]) == 1
    assert "no match" in capsys.readouterr().out


def test_unknown_term_reports_and_exits_nonzero(capsys):
    assert main(["lookup", "bitcoin"]) == 1
    assert "no match" in capsys.readouterr().out


def test_out_of_range_index_reports_no_match(capsys):
    assert main(["lookup", "2048"]) == 1
    assert "no match" in capsys.readouterr().out


def test_non_ascii_digit_reports_no_match(capsys):
    """`isdigit` is true of superscripts too, but `int` will not parse them."""
    assert main(["lookup", "²"]) == 1
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
    assert "Part 1: Word 1 is not a BIP-39 word" in caplog.text


def test_xor_does_not_log_the_mistyped_word(monkeypatch, caplog):
    """Errors reach a log, and what was typed at a seed prompt stays out of it."""
    _feed(monkeypatch, XOR_24_PARTS[0].replace("romance", "romanse"), XOR_24_PARTS[1])
    assert main(["xor", "--stdin"]) == 2
    assert "romanse" not in caplog.text


def test_xor_reads_parts_written_as_separated_blocks(capsys, monkeypatch):
    """Piped, a blank line between parts is a gap in the file, not the end.

    Stopping there would combine the first two parts alone, and their XOR is a
    different phrase carrying a valid checksum of its own — so neither the
    round-trip self-check nor the reader has anything to notice.
    """
    _feed(monkeypatch, *XOR_24_PARTS[:2], "", XOR_24_PARTS[2])
    assert main(["xor", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_24_RESULT


def test_xor_ignores_blank_lines_around_the_parts(capsys, monkeypatch):
    _feed(monkeypatch, "", *XOR_12_PARTS, "", "")
    assert main(["xor", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_12_RESULT


def test_xor_reports_how_many_parts_it_combined(capsys, monkeypatch):
    """A phrase wrapped across lines reads as short parts; the counts show it."""
    _feed(monkeypatch, *XOR_24_PARTS)
    assert main(["xor", "--stdin"]) == 0
    assert "Combined 3 parts of 24 words." in capsys.readouterr().err


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
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: False)
    assert main(["xor"]) == 2
    assert "not a terminal" in caplog.text
    # xor's --stdin takes several phrases, so the newline is a separator here.
    assert "one phrase per line" in caplog.text


def test_xor_refuses_the_stdin_flag_at_a_terminal(monkeypatch, caplog):
    """Typed under --stdin, a phrase would be echoed into scrollback."""
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    assert main(["xor", "--stdin"]) == 2
    assert "stdin is a terminal" in caplog.text
    assert "drop --stdin" in caplog.text


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
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr("seed_tools.phrase_input.read_line_hidden", _raise(EOFError))
    assert main(["xor"]) == 2
    assert "Aborted" in caplog.text


def test_xor_aborts_cleanly_on_interrupt(monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr(
        "seed_tools.phrase_input.read_line_hidden", _raise(KeyboardInterrupt)
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


def test_tinyseed_prints_a_line_per_word(capsys, monkeypatch):
    _feed(monkeypatch, XOR_24_RESULT)
    assert main(["tinyseed", "--stdin"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 24
    assert lines[0] == " 1  silent    ○●●○○●○○○●○○"
    assert lines[-1] == "24  indoor    ○○●●●○○●●○○●"


def test_tinyseed_reads_a_phrase_wrapped_across_lines(capsys, monkeypatch):
    """A backup stored as two lines of 12 is one phrase, not the first half of one."""
    words = XOR_24_RESULT.split()
    _feed(monkeypatch, " ".join(words[:12]), " ".join(words[12:]))
    assert main(["tinyseed", "--stdin"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in lines] == words


def test_tinyseed_reads_a_phrase_written_one_word_per_line(capsys, monkeypatch):
    _feed(monkeypatch, *XOR_24_RESULT.split())
    assert main(["tinyseed", "--stdin"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in lines] == XOR_24_RESULT.split()


def test_tinyseed_does_not_silently_punch_half_a_plate(capsys, monkeypatch):
    """The worst case for reading one line: the first 12 words checksum too.

    A 24-word phrase can begin with a valid 12-word one — roughly 1 in 16 do.
    Reading only the first line would print a plausible 12-row side and exit 0,
    and a hole cannot be un-punched. Built here rather than pasted, so no phrase
    that has not already been published enters the repo.
    """
    words = _phrase_of_24_starting_with(XOR_12_RESULT).split()
    assert words[:12] == XOR_12_RESULT.split()

    _feed(monkeypatch, " ".join(words[:12]), " ".join(words[12:]))
    assert main(["tinyseed", "--stdin"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in lines] == words


def test_tinyseed_rejects_two_phrases_run_together(monkeypatch, caplog):
    """Consuming all of stdin means a second phrase joins the first, not vanishes."""
    _feed(monkeypatch, XOR_12_PARTS[0], XOR_12_PARTS[1])
    assert main(["tinyseed", "--stdin"]) == 2
    assert "Invalid checksum" in caplog.text


def test_tinyseed_pattern_is_twelve_positions_of_circles(capsys, monkeypatch):
    _feed(monkeypatch, XOR_12_PARTS[0])
    assert main(["tinyseed", "--stdin"]) == 0
    patterns = [line.split()[2] for line in capsys.readouterr().out.splitlines()]
    assert len(patterns) == 12
    assert all(len(p) == 12 and set(p) <= {"○", "●"} for p in patterns)


def test_tinyseed_binary_style_agrees_with_the_circles(capsys, monkeypatch):
    _feed(monkeypatch, XOR_12_PARTS[0])
    assert main(["tinyseed", "--stdin"]) == 0
    circles = [line.split()[2] for line in capsys.readouterr().out.splitlines()]

    _feed(monkeypatch, XOR_12_PARTS[0])
    assert main(["tinyseed", "--stdin", "--style", "binary"]) == 0
    binary = [line.split()[2] for line in capsys.readouterr().out.splitlines()]

    translated = ["".join("1" if c == "●" else "0" for c in p) for p in circles]
    assert translated == binary


def test_tinyseed_number_is_one_more_than_the_lookup_index(capsys, monkeypatch):
    _feed(monkeypatch, XOR_24_RESULT)
    assert main(["tinyseed", "--stdin", "--style", "binary"]) == 0
    first = capsys.readouterr().out.splitlines()[0].split()[2]

    assert main(["lookup", "silent"]) == 0
    index = int(capsys.readouterr().out.split()[0])
    assert int(first, 2) == index + 1


def test_tinyseed_rejects_a_phrase_whose_checksum_is_wrong(monkeypatch, caplog):
    # Two words transposed — the transcription slip this check exists to catch.
    first, second, *rest = XOR_24_RESULT.split()
    _feed(monkeypatch, " ".join([second, first, *rest]))
    assert main(["tinyseed", "--stdin"]) == 2
    assert "Invalid checksum" in caplog.text


def test_tinyseed_rejects_a_wrong_word_count(monkeypatch, caplog):
    _feed(monkeypatch, " ".join(XOR_24_RESULT.split()[:13]))
    assert main(["tinyseed", "--stdin"]) == 2
    assert "must be 12, 15, 18, 21 or 24 words" in caplog.text


def test_tinyseed_rejects_an_unknown_style():
    with pytest.raises(SystemExit):
        main(["tinyseed", "--stdin", "--style", "squares"])


def test_tinyseed_refuses_a_non_terminal_without_the_stdin_flag(monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: False)
    assert main(["tinyseed"]) == 2
    assert "not a terminal" in caplog.text
    # tinyseed's --stdin takes one phrase, so it must not promise xor's format.
    assert "the whole phrase from stdin" in caplog.text
    assert "per line" not in caplog.text


def test_tinyseed_refuses_the_stdin_flag_at_a_terminal(monkeypatch, caplog):
    """Typed under --stdin, a phrase would be echoed into scrollback."""
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    assert main(["tinyseed", "--stdin"]) == 2
    assert "stdin is a terminal" in caplog.text
    assert "drop --stdin" in caplog.text


def test_tinyseed_prompts_without_echo_on_a_terminal(capsys, monkeypatch):
    prompts = _prompts(monkeypatch, XOR_12_PARTS[0])
    assert main(["tinyseed"]) == 0
    assert prompts == ["Seed phrase: "]
    assert len(capsys.readouterr().out.splitlines()) == 12


def test_tinyseed_prompts_on_stderr_with_the_stdin_flag(capsys, monkeypatch):
    _feed(monkeypatch, XOR_12_PARTS[0])
    assert main(["tinyseed", "--stdin"]) == 0
    captured = capsys.readouterr()
    assert captured.err.startswith("Seed phrase: ")
    # The prompt stays out of stdout, which carries the patterns.
    assert "Seed phrase" not in captured.out


def test_tinyseed_aborts_cleanly_on_end_of_input(capsys, monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr("seed_tools.phrase_input.read_line_hidden", _raise(EOFError))
    assert main(["tinyseed"]) == 2
    assert "Aborted" in caplog.text
    assert capsys.readouterr().out == ""


def test_tinyseed_reverse_decodes_a_punched_plate(capsys, monkeypatch):
    _feed(monkeypatch, *_plate(XOR_12_PARTS[0]))
    assert main(["tinyseed", "--reverse", "--stdin"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in lines[:12]] == XOR_12_PARTS[0].split()
    # Then a blank line and the phrase again, for comparing against a backup.
    assert lines[12] == ""
    assert lines[13] == " ".join(XOR_12_PARTS[0].split())


def test_tinyseed_survives_the_round_trip_through_a_plate(capsys, monkeypatch):
    """Punch it, read it back, get the same phrase — the point of the feature."""
    _feed(monkeypatch, XOR_24_RESULT)
    assert main(["tinyseed", "--stdin"]) == 0
    patterns = [line.split()[2] for line in capsys.readouterr().out.splitlines()]

    _feed(monkeypatch, *patterns)
    assert main(["tinyseed", "--reverse", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_24_RESULT


def test_tinyseed_reverse_reads_both_sides_as_one_phrase(capsys, monkeypatch):
    """A 24-word phrase fills both sides of a plate; 24 rows are still one phrase."""
    _feed(monkeypatch, *_plate(XOR_24_RESULT))
    assert main(["tinyseed", "--reverse", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_24_RESULT


def test_tinyseed_reverse_reads_both_sides_written_as_two_blocks(capsys, monkeypatch):
    """Piped, a blank line between the sides is a gap in the paper, not the end.

    The file's own end says where the rows stop, so the natural way to write both
    sides down — twelve rows, a gap, twelve more — has to read back whole.
    """
    rows = _plate(XOR_24_RESULT)
    _feed(monkeypatch, *rows[:12], "", *rows[12:])
    assert main(["tinyseed", "--reverse", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_24_RESULT


def test_tinyseed_reverse_does_not_stop_at_a_gap_that_checksums(capsys, monkeypatch):
    """The reason the gap cannot end the list: stopping early can look like success.

    Roughly one 24-word phrase in sixteen opens with twelve words that are a
    valid phrase in their own right. Stopping at the gap would then print those
    twelve and exit 0 — a clean read of a backup nobody has.
    """
    phrase = _phrase_of_24_starting_with(XOR_12_PARTS[0])
    rows = _plate(phrase)
    _feed(monkeypatch, *rows[:12], "", *rows[12:])
    assert main(["tinyseed", "--reverse", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == phrase


def test_tinyseed_reverse_ends_a_typed_list_at_a_blank_line(capsys, monkeypatch):
    """Typed, a blank line is still the only way to say "that was the last row".

    One full side is the exception: stopping there is ambiguous, so it takes a
    second blank line to confirm. Anything after that is not read.
    """
    rows = _plate(XOR_12_PARTS[0])
    _rows(monkeypatch, *rows, "\n", "\n", *_plate(XOR_12_PARTS[1]))
    assert main(["tinyseed", "--reverse"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_12_PARTS[0]


def test_tinyseed_reverse_does_not_end_a_typed_list_at_the_plate_seam(
    capsys, monkeypatch
):
    """A stray Enter while turning the plate over must not end the read.

    Twelve rows is where a 24-word phrase changes sides, and the first twelve
    words pass the checksum once in sixteen — so ending there can look like a
    clean read of a phrase nobody has.
    """
    rows = _plate(XOR_24_RESULT)
    _rows(monkeypatch, *rows[:12], "\n", *rows[12:])
    assert main(["tinyseed", "--reverse"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_24_RESULT


def test_tinyseed_reverse_says_why_it_kept_prompting_at_the_seam(capsys, monkeypatch):
    rows = _plate(XOR_24_RESULT)
    _rows(monkeypatch, *rows[:12], "\n", *rows[12:])
    assert main(["tinyseed", "--reverse"]) == 0
    assert "one full side of the plate" in capsys.readouterr().err


def test_tinyseed_reverse_does_not_end_a_typed_list_at_eof_at_the_seam(
    capsys, monkeypatch
):
    """Ctrl-D while turning the plate over must not end the read either.

    `readline` returns "" for Ctrl-D at a prompt, which must face the same seam
    check as a stray Enter — the truncated read it would otherwise allow passes
    the checksum once in sixteen and prints as a clean 12-word phrase.
    """
    rows = _plate(XOR_24_RESULT)
    _rows(monkeypatch, *rows[:12], "", *rows[12:])
    assert main(["tinyseed", "--reverse"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_24_RESULT


@pytest.mark.parametrize("style", sorted(tinyseed.STYLES))
def test_tinyseed_reverse_reads_any_notation(capsys, monkeypatch, style):
    _feed(monkeypatch, *_plate(XOR_12_PARTS[0], style))
    assert main(["tinyseed", "--reverse", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_12_PARTS[0]


def test_tinyseed_reverse_reads_typed_stand_ins_for_the_circles(capsys, monkeypatch):
    """What you can actually type: ● and ○ are not on a keyboard."""
    typed = [
        "".join("#" if mark == tinyseed.CIRCLE_ON else "." for mark in row)
        for row in _plate(XOR_12_PARTS[0])
    ]
    _feed(monkeypatch, *typed)
    assert main(["tinyseed", "--reverse", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_12_PARTS[0]


def test_tinyseed_reverse_accepts_rows_grouped_with_spaces(capsys, monkeypatch):
    """Twelve holes are easier to count in threes."""
    grouped = [
        " ".join(row[start : start + 3] for start in range(0, 12, 3))
        for row in _plate(XOR_12_PARTS[0])
    ]
    _feed(monkeypatch, *grouped)
    assert main(["tinyseed", "--reverse", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_12_PARTS[0]


def test_tinyseed_reverse_catches_a_single_hole_in_the_wrong_place(
    capsys, monkeypatch, caplog
):
    """The whole reason to read a plate back — one wrong hole, caught."""
    rows = _plate(XOR_12_PARTS[0])
    wrong = (
        tinyseed.CIRCLE_ON if rows[4][3] == tinyseed.CIRCLE_OFF else tinyseed.CIRCLE_OFF
    )
    rows[4] = rows[4][:3] + wrong + rows[4][4:]

    _feed(monkeypatch, *rows)
    assert main(["tinyseed", "--reverse", "--stdin"]) == 2
    assert "Invalid checksum" in caplog.text
    # Nothing is printed, so a bad plate cannot be mistaken for a good reading.
    assert capsys.readouterr().out == ""


def test_tinyseed_reverse_says_which_row_it_could_not_read(monkeypatch, caplog):
    rows = _plate(XOR_12_PARTS[0])
    rows[2] = "○○○○q○○○○○○●"
    _feed(monkeypatch, *rows)
    assert main(["tinyseed", "--reverse", "--stdin"]) == 2
    assert "Row 3:" in caplog.text
    assert "position 5" in caplog.text
    # The position, never the mark: what was really typed could be a fragment
    # of a seed phrase fed to the wrong tool, and this error is logged.
    assert "q" not in caplog.text


def test_tinyseed_reverse_rejects_a_row_with_a_hole_miscounted(monkeypatch, caplog):
    rows = _plate(XOR_12_PARTS[0])
    rows[0] = rows[0][:-1]
    _feed(monkeypatch, *rows)
    assert main(["tinyseed", "--reverse", "--stdin"]) == 2
    assert "Row 1: Expected 12 positions, got 11" in caplog.text


def test_tinyseed_reverse_rejects_a_skipped_row(monkeypatch, caplog):
    """An unpunched row is a row that was missed — no word is number zero."""
    rows = _plate(XOR_12_PARTS[0])
    rows[6] = tinyseed.CIRCLE_OFF * tinyseed.PLATE_BITS
    _feed(monkeypatch, *rows)
    assert main(["tinyseed", "--reverse", "--stdin"]) == 2
    assert "Row 7: Row has no holes" in caplog.text


def test_tinyseed_reverse_rejects_a_short_plate(monkeypatch, caplog):
    _feed(monkeypatch, *_plate(XOR_12_PARTS[0])[:11])
    assert main(["tinyseed", "--reverse", "--stdin"]) == 2
    assert "must be 12, 15, 18, 21 or 24 words" in caplog.text


def test_tinyseed_reverse_prompts_row_by_row(capsys, monkeypatch):
    prompts = _rows(monkeypatch, *_plate(XOR_24_RESULT))
    assert main(["tinyseed", "--reverse"]) == 0
    assert prompts[0] == "Row 1: "
    assert prompts[11] == "Row 12: "
    # A side ends at row 12, so from there on the prompt says how to stop.
    assert prompts[12] == "Row 13 (blank to finish): "
    assert prompts[-1] == "Row 25 (blank to finish): "
    assert capsys.readouterr().out.splitlines()[-1] == XOR_24_RESULT


def test_tinyseed_reverse_echoes_what_is_typed(capsys, monkeypatch):
    """The exception to hiding input: an unseen transcription cannot be checked."""
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr(
        "seed_tools.phrase_input.read_line_hidden", _raise(AssertionError)
    )
    _feed(monkeypatch, *_plate(XOR_12_PARTS[0]))
    assert main(["tinyseed", "--reverse"]) == 0
    assert capsys.readouterr().err.startswith("Row 1: ")


def test_tinyseed_reverse_refuses_a_non_terminal_without_the_stdin_flag(
    monkeypatch, caplog
):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: False)
    assert main(["tinyseed", "--reverse"]) == 2
    assert "not a terminal" in caplog.text
    # Reading back, a newline separates the rows — not tinyseed's usual format.
    assert "one plate row per line" in caplog.text


def test_tinyseed_reverse_refuses_a_style_instead_of_ignoring_it(monkeypatch, caplog):
    _feed(monkeypatch, *_plate(XOR_12_PARTS[0]))
    assert main(["tinyseed", "--reverse", "--stdin", "--style", "binary"]) == 2
    assert "no effect with --reverse" in caplog.text


def test_tinyseed_reverse_aborts_cleanly_on_interrupt(capsys, monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr(
        "seed_tools.phrase_input.read_line_echoed", _raise(KeyboardInterrupt)
    )
    assert main(["tinyseed", "--reverse"]) == 2
    assert "Aborted" in caplog.text
    assert capsys.readouterr().out == ""


def test_tinyseed_reverse_reads_the_rows_from_a_file(capsys, tmp_path):
    """A plate copied down once can be checked without retyping it."""
    plate = _plate_file(tmp_path, _plate(XOR_12_PARTS[0]))
    assert main(["tinyseed", "--reverse", "--file", str(plate)]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[1] for line in lines[:12]] == XOR_12_PARTS[0].split()
    assert lines[-1] == XOR_12_PARTS[0]


def test_tinyseed_reverse_reads_a_file_of_both_sides_split_by_a_gap(capsys, tmp_path):
    """A file ends itself, so a blank line in it is the gap between the sides.

    The phrase here is one whose first twelve words checksum on their own, which
    is what makes stopping at the gap dangerous: it would exit 0 on a clean read
    of a backup nobody has.
    """
    phrase = _phrase_of_24_starting_with(XOR_12_PARTS[0])
    rows = _plate(phrase)
    plate = _plate_file(tmp_path, [*rows[:12], "", *rows[12:]])
    assert main(["tinyseed", "--reverse", "--file", str(plate)]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == phrase


def test_tinyseed_reverse_reads_a_file_at_a_terminal(capsys, monkeypatch, tmp_path):
    """The file is the input, so neither the prompt nor stdin is involved."""
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr(
        "seed_tools.phrase_input.read_line_hidden", _raise(AssertionError)
    )
    monkeypatch.setattr(
        "seed_tools.phrase_input.read_line_echoed", _raise(AssertionError)
    )
    plate = _plate_file(tmp_path, _plate(XOR_24_RESULT))
    assert main(["tinyseed", "--reverse", "--file", str(plate)]) == 0

    out = capsys.readouterr()
    assert out.out.splitlines()[-1] == XOR_24_RESULT
    # Nobody is at the keyboard, so nothing asks for a row.
    assert "Row 1: " not in out.err


def test_tinyseed_reverse_says_which_row_of_a_file_it_could_not_read(tmp_path, caplog):
    rows = _plate(XOR_12_PARTS[0])
    rows[2] = rows[2][:-1]
    plate = _plate_file(tmp_path, rows)
    assert main(["tinyseed", "--reverse", "--file", str(plate)]) == 2
    assert "Row 3: Expected 12 positions, got 11" in caplog.text


def test_tinyseed_reverse_reports_a_file_it_cannot_read(capsys, tmp_path, caplog):
    missing = tmp_path / "nowhere.txt"
    assert main(["tinyseed", "--reverse", "--file", str(missing)]) == 2
    assert f"Cannot read {missing}" in caplog.text
    assert capsys.readouterr().out == ""


def test_tinyseed_reverse_reports_a_file_that_is_not_text(tmp_path, caplog):
    """A wrong path can land on anything; it must not come back as a traceback."""
    plate = tmp_path / "plate.bin"
    plate.write_bytes(bytes(range(256)))
    assert main(["tinyseed", "--reverse", "--file", str(plate)]) == 2
    assert "is not a text file" in caplog.text


def test_tinyseed_refuses_a_file_in_the_punching_direction(tmp_path, caplog):
    """Punching reads a phrase, not rows — the flag would read the wrong thing."""
    plate = _plate_file(tmp_path, _plate(XOR_12_PARTS[0]))
    assert main(["tinyseed", "--file", str(plate)]) == 2
    assert "--file only applies with --reverse" in caplog.text


def test_tinyseed_refuses_a_file_and_stdin_together():
    with pytest.raises(SystemExit):
        main(["tinyseed", "--reverse", "--stdin", "--file", "plate.txt"])


def test_checksum_lists_every_valid_final_word(capsys, monkeypatch):
    _feed(monkeypatch, " ".join(XOR_12_RESULT.split()[:11]))
    assert main(["checksum", "--stdin"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 128
    assert XOR_12_RESULT.split()[-1] in [line.split()[1] for line in lines]


def test_checksum_of_a_23_word_phrase_offers_eight_words(capsys, monkeypatch):
    _feed(monkeypatch, " ".join(XOR_24_RESULT.split()[:23]))
    assert main(["checksum", "--stdin"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 8
    assert XOR_24_RESULT.split()[-1] in [line.split()[1] for line in lines]


def test_checksum_candidates_are_numbered_from_zero(capsys, monkeypatch):
    """The number is the value to draw, not a position in the phrase."""
    _feed(monkeypatch, " ".join(XOR_24_RESULT.split()[:23]))
    assert main(["checksum", "--stdin"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [int(line.split()[0]) for line in lines] == list(range(8))


def test_checksum_candidates_complete_a_phrase_the_tools_accept(capsys, monkeypatch):
    """Feed each completion back to a tool that verifies the checksum itself."""
    head = XOR_24_RESULT.split()[:23]
    _feed(monkeypatch, " ".join(head))
    assert main(["checksum", "--stdin"]) == 0
    for line in capsys.readouterr().out.splitlines():
        _feed(monkeypatch, " ".join([*head, line.split()[1]]))
        assert main(["tinyseed", "--stdin"]) == 0


def test_checksum_reports_the_word_count_it_read(capsys, monkeypatch):
    """A phrase that lost or gained a word can still be an accepted length."""
    _feed(monkeypatch, " ".join(XOR_12_RESULT.split()[:11]))
    assert main(["checksum", "--stdin"]) == 0
    assert "11 words read; 128 valid final words." in capsys.readouterr().err


def test_checksum_says_the_last_word_is_a_choice_of_entropy(capsys, monkeypatch):
    """Taking the first candidate every time throws the free bits away."""
    _feed(monkeypatch, " ".join(XOR_12_RESULT.split()[:11]))
    assert main(["checksum", "--stdin"]) == 0
    assert "7 bits of entropy" in capsys.readouterr().err


def test_checksum_reads_a_phrase_wrapped_across_lines(capsys, monkeypatch):
    """All of stdin is the phrase — a backup may be written however it fits."""
    head = XOR_24_RESULT.split()[:23]
    _feed(monkeypatch, " ".join(head[:12]), " ".join(head[12:]))
    assert main(["checksum", "--stdin"]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 8


def test_checksum_rejects_a_complete_phrase(monkeypatch, caplog):
    _feed(monkeypatch, XOR_12_RESULT)
    assert main(["checksum", "--stdin"]) == 2
    assert "must be 11, 14, 17, 20 or 23 words" in caplog.text
    assert "every word but the last" in caplog.text


def test_checksum_rejects_a_mistyped_word(monkeypatch, caplog):
    words = XOR_12_RESULT.split()[:11]
    words[0] = "cannonn"
    _feed(monkeypatch, " ".join(words))
    assert main(["checksum", "--stdin"]) == 2
    assert "Word 1 is not a BIP-39 word" in caplog.text
    # Errors reach a log, and what was typed at a seed prompt stays out of it.
    assert "cannonn" not in caplog.text


def test_checksum_prompts_without_echo_on_a_terminal(capsys, monkeypatch):
    prompts = _prompts(monkeypatch, " ".join(XOR_12_RESULT.split()[:11]))
    assert main(["checksum"]) == 0
    assert prompts == ["Seed phrase without its last word: "]
    assert len(capsys.readouterr().out.splitlines()) == 128


def test_checksum_refuses_a_non_terminal_without_the_stdin_flag(monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: False)
    assert main(["checksum"]) == 2
    assert "not a terminal" in caplog.text
    # One phrase, so it must not promise xor's line-per-phrase format.
    assert "the whole phrase from stdin" in caplog.text
    assert "per line" not in caplog.text


def test_checksum_refuses_the_stdin_flag_at_a_terminal(monkeypatch, caplog):
    """Typed under --stdin, a phrase would be echoed into scrollback."""
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    assert main(["checksum", "--stdin"]) == 2
    assert "stdin is a terminal" in caplog.text
    assert "drop --stdin" in caplog.text


def test_checksum_prompts_on_stderr_with_the_stdin_flag(capsys, monkeypatch):
    _feed(monkeypatch, " ".join(XOR_12_RESULT.split()[:11]))
    assert main(["checksum", "--stdin"]) == 0
    captured = capsys.readouterr()
    assert captured.err.startswith("Seed phrase without its last word: ")
    # The prompt stays out of stdout, which carries the candidates.
    assert "Seed phrase" not in captured.out


def test_checksum_aborts_cleanly_on_interrupt(capsys, monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr(
        "seed_tools.phrase_input.read_line_hidden", _raise(KeyboardInterrupt)
    )
    assert main(["checksum"]) == 2
    assert "Aborted" in caplog.text
    assert capsys.readouterr().out == ""


def test_expand_completes_a_four_letter_print(capsys, monkeypatch):
    """Four letters identify a word, so this is the whole job most of the time."""
    _feed(monkeypatch, "abso")
    assert main(["expand", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[0].split()[1:] == ["abso", "absorb"]


def test_expand_lists_every_word_when_the_letters_are_short(capsys, monkeypatch):
    _feed(monkeypatch, "abs")
    assert main(["expand", "--stdin"]) == 0
    line = capsys.readouterr().out.splitlines()[0]
    assert line.split()[2:] == ["absent", "absorb", "abstract", "absurd"]


def test_expand_reads_a_whole_bag_of_pills_back(capsys, monkeypatch):
    """The point of the tool: 24 prints of four letters, one phrase out."""
    _feed(monkeypatch, *(word[:4] for word in XOR_24_RESULT.split()))
    assert main(["expand", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_24_RESULT


def test_expand_prints_no_phrase_while_anything_is_ambiguous(capsys, monkeypatch):
    """Half a decision is not a phrase — printing one would invent the rest."""
    _feed(monkeypatch, "abso", "abs")
    assert main(["expand", "--stdin"]) == 0
    out = capsys.readouterr()
    assert "1 of 2 sets match more than one word" in out.err
    assert not out.out.splitlines()[-1].startswith("absorb")


def test_expand_reports_how_many_sets_it_read(capsys, monkeypatch):
    """A file that lost an entry still expands cleanly; the count is the tell."""
    _feed(monkeypatch, "abso", "acti")
    assert main(["expand", "--stdin"]) == 0
    assert "2 sets of letters read." in capsys.readouterr().err


def test_expand_pick_settles_on_one_word_per_set(capsys, monkeypatch):
    _feed(monkeypatch, "abs", "act")
    assert main(["expand", "--stdin", "--pick"]) == 0
    out = capsys.readouterr()
    picked = out.out.splitlines()[-1].split()
    assert len(picked) == 2
    assert picked[0] in ["absent", "absorb", "abstract", "absurd"]
    assert "picked 1 of 4 at random" in out.err


def test_expand_pick_draws_from_secrets_not_random(capsys, monkeypatch):
    """What this picks becomes a word of a seed, so it needs the good source."""
    drawn: list[list[str]] = []

    def choice(matches: list[str]) -> str:
        drawn.append(matches)
        return matches[0]

    monkeypatch.setattr("secrets.choice", choice)
    _feed(monkeypatch, "abs")
    assert main(["expand", "--stdin", "--pick"]) == 0
    assert drawn == [["absent", "absorb", "abstract", "absurd"]]
    assert capsys.readouterr().out.splitlines()[-1] == "absent"


def test_expand_pick_says_when_the_letters_are_a_word_themselves(capsys, monkeypatch):
    """A pill printing three letters shows a three-letter word, not a prefix."""
    _feed(monkeypatch, "act")
    assert main(["expand", "--stdin", "--pick"]) == 0
    assert "themselves a word" in capsys.readouterr().err


def test_expand_pick_is_silent_when_nothing_is_ambiguous(capsys, monkeypatch):
    _feed(monkeypatch, "abso")
    assert main(["expand", "--stdin", "--pick"]) == 0
    assert "picked" not in capsys.readouterr().err


def test_expand_pick_warns_that_it_is_a_draw(capsys, monkeypatch):
    """Right for making a seed, wrong for reading one back — and it looks alike."""
    _feed(monkeypatch, "abso")
    assert main(["expand", "--stdin", "--pick"]) == 0
    assert "--pick chooses at random" in capsys.readouterr().err


def test_expand_rejects_fewer_letters_than_the_shortest_word(monkeypatch, caplog):
    _feed(monkeypatch, "ab")
    assert main(["expand", "--stdin"]) == 2
    assert "Letters 1: at least 3" in caplog.text


def test_expand_rejects_more_letters_than_a_truncated_backup_shows(monkeypatch, caplog):
    _feed(monkeypatch, "absor")
    assert main(["expand", "--stdin"]) == 2
    assert "Letters 1: at most 4" in caplog.text


def test_expand_rejects_letters_no_word_starts_with(monkeypatch, caplog):
    _feed(monkeypatch, "abso", "qqq")
    assert main(["expand", "--stdin"]) == 2
    assert "Letters 2: no BIP-39 word starts with them" in caplog.text


def test_expand_never_repeats_the_letters_in_an_error(monkeypatch, caplog):
    """Four letters name one word, and errors are logged — same rule as lookup."""
    _feed(monkeypatch, "zebr")
    # Accepted, then made to fail on the next entry, so the log covers a run
    # where real letters were read.
    _feed(monkeypatch, "zebr", "qqq")
    assert main(["expand", "--stdin"]) == 2
    assert "zebr" not in caplog.text


def test_expand_rejects_an_empty_list(monkeypatch, caplog):
    _feed(monkeypatch, "")
    assert main(["expand", "--stdin"]) == 2
    assert "No letters were entered" in caplog.text


def test_expand_accepts_letters_typed_uppercase(capsys, monkeypatch):
    _feed(monkeypatch, "ABSO")
    assert main(["expand", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "absorb"


def test_expand_skips_a_gap_in_a_piped_list(capsys, monkeypatch):
    """Piped, only the end of the input ends the list — a blank line is a gap."""
    _feed(monkeypatch, "abso", "", "acti")
    assert main(["expand", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "absorb action"


def test_expand_ends_a_typed_list_at_a_blank_line(capsys, monkeypatch):
    """Typed, a blank line is the only way to say "that was the last pill"."""
    _prompts(monkeypatch, "abso", "acti", "", "zebr")
    assert main(["expand"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "absorb action"


def test_expand_ends_a_typed_list_at_a_line_of_spaces(capsys, monkeypatch):
    """A blank line is blank however it was made — `getpass` keeps the spaces."""
    _prompts(monkeypatch, "abso", "   ", "zebr")
    assert main(["expand"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "absorb"


def test_expand_prompts_without_echo_on_a_terminal(capsys, monkeypatch):
    """Letters off a pill are a word of a seed, so they are typed hidden."""
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr(
        "seed_tools.phrase_input.read_line_echoed", _raise(AssertionError)
    )
    prompts = _prompts(monkeypatch, "abso", "")
    assert main(["expand"]) == 0
    assert prompts[0] == "Letters 1: "
    # From the second on, ending the list is a real choice, so the prompt says how.
    assert prompts[1] == "Letters 2 (blank to finish): "
    assert capsys.readouterr().out.splitlines()[-1] == "absorb"


def test_expand_refuses_a_non_terminal_without_the_stdin_flag(monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: False)
    assert main(["expand"]) == 2
    assert "one set of letters per line" in caplog.text


def test_expand_refuses_the_stdin_flag_at_a_terminal(monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    assert main(["expand", "--stdin"]) == 2
    assert "stdin is a terminal" in caplog.text


def test_expand_aborts_cleanly_on_end_of_input(capsys, monkeypatch, caplog):
    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr(
        "seed_tools.phrase_input.read_line_hidden", _raise(KeyboardInterrupt)
    )
    assert main(["expand"]) == 2
    assert "Aborted" in caplog.text
    assert capsys.readouterr().out == ""


def _plate(phrase: str, style: str = tinyseed.DEFAULT_STYLE) -> list[str]:
    """The rows a punched plate shows for a phrase, as they are read back off it."""
    return [tinyseed.dots(word, style) for word in phrase.split()]


def _plate_file(tmp_path, rows: list[str], name: str = "plate.txt"):
    """Write rows out the way someone copying a plate down would, and hand back the path."""
    path = tmp_path / name
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def _rows(monkeypatch, *replies: str) -> list[str]:
    """Drive the interactive row prompts with canned rows; returns prompts seen."""
    seen: list[str] = []

    def prompt(text: str) -> str:
        seen.append(text)
        return replies[len(seen) - 1] if len(seen) <= len(replies) else ""

    monkeypatch.setattr("seed_tools.phrase_input.stdin_is_tty", lambda: True)
    monkeypatch.setattr("seed_tools.phrase_input.read_line_echoed", prompt)
    return seen


def _phrase_of_24_starting_with(phrase: str) -> str:
    """A valid 24-word phrase whose first 12 words are the given 12-word phrase.

    Twelve words are 132 bits, and a 24-word phrase takes its first 132 bits from
    entropy alone — so any 12-word phrase can open one. Zero-fill the remaining
    124 bits and let `from_entropy` compute the checksum over the whole thing.
    """
    bits = "".join(wordlist().binary(word) for word in phrase.split())
    return " ".join(from_entropy(int(bits.ljust(256, "0"), 2).to_bytes(32, "big")))


def _raise(error: type[BaseException]):
    def read(_prompt: str) -> str:
        raise error

    return read
