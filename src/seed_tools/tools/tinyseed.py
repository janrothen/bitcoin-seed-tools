"""Print the TinySeed plate punch pattern for each word of a seed phrase."""

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


def register(subparsers: _SubParsersAction) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        NAME, help=HELP, description=DESCRIPTION
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read the phrase from stdin (input is echoed)",
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
        words = _read_rows()

    # The checksum is what makes this a check and not just a translation: a
    # misread row, or a hole in the wrong place, almost always breaks it.
    to_entropy(words)

    for position, word in enumerate(words, start=1):
        print(f"{position:2d}  {word}")
    # The same words again on one line, unlabelled, for comparing with a backup.
    print()
    print(" ".join(words))
    return 0


def _read_rows() -> list[str]:
    """Read rows until a blank line, decoding each one as it is entered."""
    read = phrase_input.row_reader()
    words: list[str] = []
    while True:
        number = len(words) + 1
        line = read(_prompt(number))
        if not line.strip():
            return words
        # Decoded here rather than once the whole plate is in, so a miscounted
        # row is reported while that row is still the one under the reader's eye.
        try:
            words.append(tinyseed.read_word(line))
        except ValueError as error:
            raise ValueError(f"Row {number}: {error}") from None


def _prompt(number: int) -> str:
    # A 24-word phrase spans two plates, so past the first the list may end.
    if number <= tinyseed.PLATE_ROWS:
        return f"Row {number}: "
    return f"Row {number} (blank to finish): "
