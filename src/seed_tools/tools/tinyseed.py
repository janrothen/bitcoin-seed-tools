"""Print the TinySeed plate punch pattern for each word of a seed phrase."""

import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from collections.abc import Callable

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

# Shown when a typed list stops at exactly one full side — see `_read_rows`.
SEAM_NOTICE = (
    f"— {tinyseed.SIDE_ROWS} rows read, which is one full side of the plate. A "
    "24-word phrase fills both: turn the plate over and carry on, or press "
    "Enter again to finish here."
)


def register(subparsers: _SubParsersAction) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        NAME, help=HELP, description=DESCRIPTION
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--stdin",
        action="store_true",
        help="read the phrase from stdin",
    )
    source.add_argument(
        "--file",
        metavar="PATH",
        # Left unset so --reverse can tell "not given" from "given the default",
        # the same as --style below.
        default=None,
        help="with --reverse, read the rows of the plate from a file",
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
    if args.file is not None:
        raise ValueError(
            "--file only applies with --reverse, which reads rows of holes. "
            "This direction reads a phrase — pipe one in with --stdin"
        )
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
    with phrase_input.aborting():
        if args.file is not None:
            # A file ends itself, so nothing is typed and nothing is prompted
            # for — the terminal checks below are about a prompt that never
            # happens here.
            with phrase_input.file_reader(args.file) as read:
                words = _read_rows(read, typed=False)
        else:
            phrase_input.require_interactive_or_stdin(args.stdin, REVERSE_STDIN_READS)
            words = _read_rows(phrase_input.row_reader(), typed=not args.stdin)

    # The checksum is what makes this a check and not just a translation: a
    # misread row, or a hole in the wrong place, almost always breaks it.
    to_entropy(words)

    for position, word in enumerate(words, start=1):
        print(f"{position:2d}  {word}")
    # The same words again on one line, unlabelled, for comparing with a backup.
    print()
    print(" ".join(words))
    return 0


def _read_rows(read: Callable[[str], str], typed: bool) -> list[str]:
    """Read rows until the input ends, decoding each one as it is entered.

    What ends the list depends on where the rows come from. Typed at a prompt
    there is nothing but a blank line to say "that was the last row". Piped or
    read from a file, the input's own end says it, so a blank line there is only
    the gap between the front and the back of the plate and is skipped: a
    24-word phrase written out as two blocks of twelve must not read back as its
    first twelve, which is a valid phrase in its own right and passes the
    checksum once in sixteen — the tool would then report success on a phrase
    that is not what the plate says, which is precisely the mistake reading a
    plate back exists to catch.
    """
    words: list[str] = []
    seam_seen = False
    while True:
        number = len(words) + 1
        line = read(_prompt(number, typed))
        if not line.strip():
            if not typed:
                if not line:
                    # End of the input — no more rows are coming.
                    break
                # A blank line there is only the gap between the two sides.
                continue
            # Typed, a blank line and Ctrl-D land here alike: `readline` returns
            # "" at end of input, and both mean "that was the last row" — so
            # both must face the seam check below, or a Ctrl-D at the seam
            # would end the read that a stray Enter is stopped from ending.
            # One full side is the single ambiguous place to stop: a 12-word
            # phrase ends here, and so does the first half of a 24-word one.
            # Reading both sides means a pause at the seam to turn the plate
            # over, and an Enter pressed in that pause would otherwise end
            # the list — leaving twelve words that pass the checksum once in
            # sixteen and get printed as the whole phrase. That is the misread
            # this subcommand exists to catch, so say so once and keep the
            # prompt open; a second blank line means it really was one side.
            if len(words) == tinyseed.SIDE_ROWS and not seam_seen:
                seam_seen = True
                print(SEAM_NOTICE, file=sys.stderr)
                continue
            break
        # Decoded here rather than once every row is in, so a miscounted
        # row is reported while that row is still the one under the reader's eye.
        try:
            words.append(tinyseed.read_word(line))
        except ValueError as error:
            raise ValueError(f"Row {number}: {error}") from None
    return words


def _prompt(number: int, typed: bool) -> str:
    # A 24-word phrase carries on over the back, so past the front side the
    # list may end. Only a typed list ends at a blank line — anywhere else the
    # hint would lie. (A file is not prompted at all; the text is dropped.)
    if not typed or number <= tinyseed.SIDE_ROWS:
        return f"Row {number}: "
    return f"Row {number} (blank to finish): "
