"""Complete BIP-39 words from the first few letters of each one."""

import secrets
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction

from seed_tools import phrase_input
from seed_tools.wordlist import UNIQUE_PREFIX, Wordlist, wordlist

NAME = "expand"
HELP = "complete BIP-39 words from their first letters (SeedPills, stamped plates)"
DESCRIPTION = (
    "Complete BIP-39 words from the first few letters of each one. A backup that "
    f"cannot fit a whole word prints {UNIQUE_PREFIX} letters and stops — a "
    "SeedPills pill, a stamped plate, a cramped column on paper — because in "
    f"BIP-39 the first {UNIQUE_PREFIX} letters identify a word uniquely. Enter "
    "the letters one set per line; every word that starts with them is printed."
)

# Several sets of letters, so here a newline is a separator and a blank line
# ends the list — the same shape as `xor`, not `checksum`.
STDIN_READS = "one set of letters per line"

# Said once when --pick is used, because the flag is right in one situation and
# wrong in the other, and the output looks identical either way.
PICK_NOTICE = (
    "--pick chooses at random. That is right when you are drawing pills to make "
    "a new seed, and wrong when you are reading a backup you already have: there "
    "the word is whichever one is really on the pill, not one of its neighbours."
)

# Said when the letters entered are themselves a word. Positions, never the
# letters: this goes out beside errors that are logged.
EXACT_NOTICE = (
    "these letters are themselves a word — a backup that prints fewer than "
    f"{UNIQUE_PREFIX} letters is showing a whole short word, so that is the one "
    "to take rather than a longer word it happens to start"
)


def register(subparsers: _SubParsersAction) -> None:
    parser: ArgumentParser = subparsers.add_parser(
        NAME, help=HELP, description=DESCRIPTION
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read the letters from stdin, one set per line",
    )
    parser.add_argument(
        "--pick",
        action="store_true",
        help="when several words match, pick one of them at random",
    )
    parser.set_defaults(run=run)


def run(args: Namespace) -> int:
    words = wordlist()
    phrase_input.require_interactive_or_stdin(args.stdin, STDIN_READS)
    with phrase_input.aborting():
        entries = _read_entries(words, args.stdin)

    if args.pick:
        print(PICK_NOTICE, file=sys.stderr)

    # How many sets went in, on stderr, ahead of the words on stdout — the same
    # count the other tools print, and for the same reason: a list read from a
    # file that lost or gained an entry looks entirely convincing without it.
    print(f"{len(entries)} sets of letters read.", file=sys.stderr)

    chosen: list[str] = []
    for number, (letters, matches) in enumerate(entries, start=1):
        if len(matches) > 1 and args.pick:
            if words.contains(letters):
                print(f"Letters {number}: {EXACT_NOTICE}.", file=sys.stderr)
            print(
                f"Letters {number}: picked 1 of {len(matches)} at random.",
                file=sys.stderr,
            )
            # `secrets`, not `random`: whatever this picks becomes a word of a
            # seed phrase, so it has to be as unguessable as the draw it stands
            # in for. Drawn from a bag at random and then picked from at random,
            # every word of the list stays equally likely.
            matches = [secrets.choice(matches)]
        if len(matches) == 1:
            chosen.append(matches[0])
        print(f"{number:2d}  {letters:<{UNIQUE_PREFIX}}  {' '.join(matches)}")

    if len(chosen) == len(entries):
        # Every set came down to one word, so the phrase can be read off in one
        # line — the shape `xor` and `tinyseed` print for transcribing.
        print()
        print(" ".join(chosen))
    else:
        undecided = len(entries) - len(chosen)
        print(
            f"{undecided} of {len(entries)} sets match more than one word, so "
            "there is no single phrase to print. Take the word your backup "
            "really shows, or pass --pick if you are drawing pills at random.",
            file=sys.stderr,
        )
    return 0


def _read_entries(words: Wordlist, use_stdin: bool) -> list[tuple[str, list[str]]]:
    """Read sets of letters until the input ends, resolving each as it arrives.

    What ends the list depends on where the letters come from, the same way it
    does in `xor._read_parts`. Typed at a prompt there is nothing but a blank
    line to say "that was the last one". Piped, the input's own end says it, so a
    blank line there is only a gap in the file and is skipped.
    """
    read = phrase_input.line_reader(use_stdin)
    entries: list[tuple[str, list[str]]] = []
    while True:
        number = len(entries) + 1
        line = read(_prompt(number, use_stdin))
        if not line:
            # End of input — no more letters are coming, however they were fed in.
            break
        if not line.strip():
            if use_stdin:
                continue
            break
        # Resolved here rather than once the whole list is in, so letters that
        # match nothing are reported while that pill is still in the reader's
        # hand and the rest have yet to be typed.
        letters = _letters(words, line, number)
        try:
            matches = _matches(words, letters)
        except ValueError as error:
            raise ValueError(f"Letters {number}: {error}") from None
        entries.append((letters, matches))
    if not entries:
        raise ValueError("No letters were entered — nothing to expand")
    return entries


def _letters(words: Wordlist, line: str, number: int) -> str:
    """One entry, checked for a length a truncated word can actually have.

    Every message here names the position and never the letters: they reach a
    log through `cli.main`, and a few letters of a seed word narrow that word to
    a handful of candidates — the same reasoning as `Wordlist.index`.
    """
    letters = line.strip().lower()
    shortest = words.shortest_word()
    if len(letters) < shortest:
        raise ValueError(
            f"Letters {number}: at least {shortest} are needed — no BIP-39 word "
            "is shorter than that, so fewer letters means some were missed"
        )
    if len(letters) > UNIQUE_PREFIX:
        raise ValueError(
            f"Letters {number}: at most {UNIQUE_PREFIX} — a backup that truncates "
            f"prints {UNIQUE_PREFIX}, because that is what identifies a word. For "
            "a longer prefix, or a whole word, use lookup"
        )
    return letters


def _matches(words: Wordlist, letters: str) -> list[str]:
    matches = words.starting_with(letters)
    if not matches:
        # No position here: this is called with letters that `_letters` has
        # already accepted, and the caller adds the position it knows.
        raise ValueError("no BIP-39 word starts with them")
    return matches


def _prompt(number: int, use_stdin: bool) -> str:
    # Piped, a blank line is not what ends the list, so the hint would be a lie.
    # Typed, the first set cannot be the blank one — there would be nothing to
    # expand — so the hint starts once ending the list is a real choice.
    if use_stdin or number == 1:
        return f"Letters {number}: "
    return f"Letters {number} (blank to finish): "
