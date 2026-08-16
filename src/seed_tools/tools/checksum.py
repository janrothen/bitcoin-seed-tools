"""List the final words that complete a seed phrase with a valid checksum."""

import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction

from seed_tools import phrase_input
from seed_tools.mnemonic import final_word_entropy_bits, final_words, normalize

NAME = "checksum"
HELP = "list the final words that complete a seed phrase with a valid checksum"
DESCRIPTION = (
    "Given every word of a seed phrase but the last, list the final words that "
    "make the checksum come out right. There is always more than one: the last "
    "word carries entropy as well as the checksum, so each candidate completes a "
    "valid phrase for a different wallet."
)

PROMPT = "Seed phrase without its last word: "

# One phrase, however it is wrapped — all of stdin is that phrase.
STDIN_READS = "the whole phrase from stdin"


def register(subparsers: _SubParsersAction) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        NAME, help=HELP, description=DESCRIPTION
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read the phrase from stdin",
    )
    parser.set_defaults(run=run)


def run(args: Namespace) -> int:
    phrase_input.require_interactive_or_stdin(args.stdin, STDIN_READS)
    with phrase_input.aborting():
        text = phrase_input.phrase_reader(args.stdin)(PROMPT)

    given = normalize(text)
    candidates = final_words(given)
    free_bits = final_word_entropy_bits(len(given) + 1)

    # How many words went in, on stderr, ahead of the candidates on stdout. A
    # phrase read from a file that lost or gained a word still lands on one of
    # the accepted lengths often enough, and the count is what shows it — the
    # candidates themselves look exactly as convincing either way.
    print(
        f"{len(given)} words read; {len(candidates)} valid final words.",
        file=sys.stderr,
    )
    # Which one to take is a choice of entropy, not a formality: taking the
    # first — or the prettiest — throws away the free bits and makes the phrase
    # that much easier to guess for anyone who knows the habit.
    print(
        f"Each completes a different wallet. The last word carries {free_bits} bits "
        f"of entropy besides the checksum, so pick a number at random "
        f"({free_bits} coin flips) rather than taking the first.",
        file=sys.stderr,
    )

    # Numbered from 0, unlike the word positions the other tools print: this
    # number is not a place in the phrase but the value to draw, and the draw is
    # exactly `free_bits` bits.
    for number, word in enumerate(candidates):
        print(f"{number:3d}  {word}")
    return 0
