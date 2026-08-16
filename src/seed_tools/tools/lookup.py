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
    matched_any = False
    for term in args.terms:
        matches = _resolve(words, term)
        if not matches:
            print(f"{term}: no match")
            continue
        matched_any = True
        for word in matches:
            print(f"{words.index(word):4d}  {words.binary(word)}  {word}")
    # Like grep: finding anything at all is success, finding nothing is 1.
    return 0 if matched_any else 1


def _resolve(words: Wordlist, term: str) -> list[str]:
    # BIP-39 words are lowercase; accept them typed any way, as the phrase
    # paths already do through `normalize`.
    term = term.lower()
    if not term:
        # `startswith("")` is true of every word; an empty term matches nothing.
        return []
    # `isascii` first: `isdigit` is also true of superscripts and other digit
    # characters `int` will not parse, and those belong in the prefix search
    # that reports "no match" rather than in an error about literals.
    if term.isascii() and term.isdigit():
        try:
            index = int(term)
        except ValueError:
            # More digits than CPython will parse as one int — however it is
            # read, it is past 2047, and out of range means "no match".
            return []
        return [words.word(index)] if 0 <= index < len(words) else []
    # A prefix search finds an exact word too, and lists it first — the list is
    # sorted, so a word sorts ahead of everything it prefixes. `car` must not
    # hide carbon or cargo from someone reading a smudged backup.
    return words.starting_with(term)
