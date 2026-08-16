"""Look up BIP-39 words by word, index or prefix."""

from argparse import ArgumentParser, Namespace, _SubParsersAction

from seed_tools.wordlist import Wordlist, wordlist

NAME = "lookup"
HELP = "look up BIP-39 words by word, index or prefix"


def register(subparsers: _SubParsersAction) -> None:
    parser: ArgumentParser = subparsers.add_parser(NAME, help=HELP, description=HELP)
    parser.add_argument(
        "terms",
        nargs="+",
        metavar="TERM",
        help="a word, a word prefix, or an index (0-2047)",
    )
    parser.set_defaults(run=run)


def run(args: Namespace) -> int:
    words = wordlist()
    exit_code = 0
    for term in args.terms:
        matches = _resolve(words, term)
        if not matches:
            print(f"{term}: no match")
            exit_code = 1
            continue
        for word in matches:
            print(f"{words.index(word):4d}  {words.binary(word)}  {word}")
    return exit_code


def _resolve(words: Wordlist, term: str) -> list[str]:
    if term.isdigit():
        index = int(term)
        return [words.word(index)] if 0 <= index < len(words) else []
    if words.contains(term):
        return [term]
    return words.starting_with(term)
