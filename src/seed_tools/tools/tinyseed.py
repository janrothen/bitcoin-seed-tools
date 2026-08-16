"""Print the TinySeed plate punch pattern for each word of a seed phrase."""

import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction

from seed_tools import phrase_input, tinyseed
from seed_tools.mnemonic import normalize, to_entropy

NAME = "tinyseed"
HELP = "print the TinySeed plate punch pattern for each word of a seed phrase"
DESCRIPTION = (
    "Print the TinySeed plate punch pattern for each word of a seed phrase, or "
    "with --reverse read a punched plate back: rows of holes in, words out."
)

PROMPT = "Seed phrase: "

# One phrase, however it is wrapped — all of stdin is that phrase.
STDIN_READS = "the whole phrase from stdin"

# Reading back, a newline separates one row of the plate from the next.
REVERSE_STDIN_READS = "one plate row per line"

# Shown when a typed list stops at exactly one full plate — see `_read_rows`.
SEAM_NOTICE = (
    f"— {tinyseed.PLATE_ROWS} rows read, which is one full plate. A 24-word "
    "phrase spans two: carry on with the next plate, or press Enter again to "
    "finish here."
)


def register(subparsers: _SubParsersAction) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        NAME, help=HELP, description=DESCRIPTION
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read the phrase from stdin",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="read a punched plate back: one row of holes per line, words out",
    )
    parser.add_argument(
        "--style",
        choices=sorted(tinyseed.STYLES),
        # Left unset so --reverse can tell "not given" from "given the default"
        # and refuse the flag rather than quietly ignore it.
        default=None,
        help=f"how to draw each pattern (default: {tinyseed.DEFAULT_STYLE})",
    )
    parser.set_defaults(run=run)


def run(args: Namespace) -> int:
    if args.reverse:
        return _read_plate(args)
    return _punch_plate(args)


def _punch_plate(args: Namespace) -> int:
    """Phrase in, holes out — what to punch."""
    phrase_input.require_interactive_or_stdin(args.stdin, STDIN_READS)
    with phrase_input.aborting():
        text = phrase_input.phrase_reader(args.stdin)(PROMPT)

    words = normalize(text)
    # Decoding is what validates: it enforces the word count and, crucially, the
    # checksum — so a mistyped word is caught before any of it reaches the plate,
    # where a wrong hole cannot be un-punched.
    to_entropy(words)

    style = args.style or tinyseed.DEFAULT_STYLE
    width = tinyseed.WORD_WIDTH
    for position, word in enumerate(words, start=1):
        print(f"{position:2d}  {word:<{width}}  {tinyseed.dots(word, style)}")
    return 0


def _read_plate(args: Namespace) -> int:
    """Holes in, phrase out — what a punched plate actually says."""
    if args.style is not None:
        raise ValueError(
            "--style has no effect with --reverse: the marks are recognised as "
            "they come, whichever way you write them"
        )
    phrase_input.require_interactive_or_stdin(args.stdin, REVERSE_STDIN_READS)
    with phrase_input.aborting():
        words = _read_rows(args.stdin)

    # The checksum is what makes this a check and not just a translation: a
    # misread row, or a hole in the wrong place, almost always breaks it.
    to_entropy(words)

    for position, word in enumerate(words, start=1):
        print(f"{position:2d}  {word}")
    # The same words again on one line, unlabelled, for comparing with a backup.
    print()
    print(" ".join(words))
    return 0


def _read_rows(use_stdin: bool) -> list[str]:
    """Read rows until the input ends, decoding each one as it is entered.

    What ends the list depends on where the rows come from. Typed at a prompt
    there is nothing but a blank line to say "that was the last row". Piped, the
    file's own end says it, so a blank line there is only the gap between two
    plates and is skipped: a 24-word phrase written out as two blocks of twelve
    must not read back as its first twelve, which is a valid phrase in its own
    right and passes the checksum once in sixteen — the tool would then report
    success on a phrase that is not what the plates say, which is precisely the
    mistake reading a plate back exists to catch.
    """
    read = phrase_input.row_reader()
    words: list[str] = []
    seam_seen = False
    while True:
        number = len(words) + 1
        line = read(_prompt(number, use_stdin))
        if not line.strip():
            if use_stdin:
                if not line:
                    # End of the pipe — no more rows are coming.
                    return words
                # A blank line in a pipe is only the gap between two plates.
                continue
            # Typed, a blank line and Ctrl-D land here alike: `readline` returns
            # "" at end of input, and both mean "that was the last row" — so
            # both must face the seam check below, or a Ctrl-D at the seam
            # would end the read that a stray Enter is stopped from ending.
            # One full plate is the single ambiguous place to stop: a 12-word
            # phrase ends here, and so does the first half of a 24-word one.
            # Reading two plates means a pause at the seam to pick up the
            # second, and an Enter pressed in that pause would otherwise end
            # the list — leaving twelve words that pass the checksum once in
            # sixteen and get printed as the whole phrase. That is the misread
            # this subcommand exists to catch, so say so once and keep the
            # prompt open; a second blank line means it really was one plate.
            if len(words) == tinyseed.PLATE_ROWS and not seam_seen:
                seam_seen = True
                print(SEAM_NOTICE, file=sys.stderr)
                continue
            return words
        # Decoded here rather than once the whole plate is in, so a miscounted
        # row is reported while that row is still the one under the reader's eye.
        try:
            words.append(tinyseed.read_word(line))
        except ValueError as error:
            raise ValueError(f"Row {number}: {error}") from None


def _prompt(number: int, use_stdin: bool) -> str:
    # A 24-word phrase spans two plates, so past the first the list may end.
    # Piped, a blank line is not what ends it, so the hint would be a lie.
    if use_stdin or number <= tinyseed.PLATE_ROWS:
        return f"Row {number}: "
    return f"Row {number} (blank to finish): "
