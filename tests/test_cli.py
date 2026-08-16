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
    Reading only the first line would print a plausible 12-row plate and exit 0,
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


def test_tinyseed_reverse_reads_two_plates_as_one_phrase(capsys, monkeypatch):
    """A 24-word phrase spans two plates; 24 rows are still one phrase."""
    _feed(monkeypatch, *_plate(XOR_24_RESULT))
    assert main(["tinyseed", "--reverse", "--stdin"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_24_RESULT


def test_tinyseed_reverse_reads_two_plates_written_as_two_blocks(capsys, monkeypatch):
    """Piped, a blank line between the plates is a gap in the paper, not the end.

    The file's own end says where the rows stop, so the natural way to write two
    plates down — twelve rows, a gap, twelve more — has to read back whole.
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

    One full plate is the exception: stopping there is ambiguous, so it takes a
    second blank line to confirm. Anything after that is not read.
    """
    rows = _plate(XOR_12_PARTS[0])
    _rows(monkeypatch, *rows, "\n", "\n", *_plate(XOR_12_PARTS[1]))
    assert main(["tinyseed", "--reverse"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == XOR_12_PARTS[0]


def test_tinyseed_reverse_does_not_end_a_typed_list_at_the_plate_seam(
    capsys, monkeypatch
):
    """A stray Enter while reaching for the second plate must not end the read.

    Twelve rows is where a 24-word phrase changes plates, and the first twelve
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
    assert "one full plate" in capsys.readouterr().err


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
    # One plate ends at row 12, so from there on the prompt says how to stop.
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


def _plate(phrase: str, style: str = tinyseed.DEFAULT_STYLE) -> list[str]:
    """The rows a punched plate shows for a phrase, as they are read back off it."""
    return [tinyseed.dots(word, style) for word in phrase.split()]


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
