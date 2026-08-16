"""Print the TinySeed plate punch pattern for each word of a seed phrase."""

from argparse import ArgumentParser, Namespace, _SubParsersAction

from seed_tools import phrase_input, tinyseed
from seed_tools.mnemonic import normalize, to_entropy

NAME = "tinyseed"
HELP = "print the TinySeed plate punch pattern for each word of a seed phrase"

PROMPT = "Seed phrase: "

# One phrase, however it is wrapped — all of stdin is that phrase.
STDIN_READS = "the whole phrase from stdin"


def register(subparsers: _SubParsersAction) -> None:
    parser: ArgumentParser = subparsers.add_parser(NAME, help=HELP, description=HELP)
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read the phrase from stdin (input is echoed)",
    )
    parser.add_argument(
        "--style",
        choices=sorted(tinyseed.STYLES),
        default=tinyseed.DEFAULT_STYLE,
        help="how to draw each pattern (default: %(default)s)",
    )
    parser.set_defaults(run=run)


def run(args: Namespace) -> int:
    phrase_input.require_interactive_or_stdin(args.stdin, STDIN_READS)
    with phrase_input.aborting():
        text = phrase_input.phrase_reader(args.stdin)(PROMPT)

    words = normalize(text)
    # Decoding is what validates: it enforces the word count and, crucially, the
    # checksum — so a mistyped word is caught before any of it reaches the plate,
    # where a wrong hole cannot be un-punched.
    to_entropy(words)

    width = tinyseed.WORD_WIDTH
    for position, word in enumerate(words, start=1):
        print(f"{position:2d}  {word:<{width}}  {tinyseed.dots(word, args.style)}")
    return 0
