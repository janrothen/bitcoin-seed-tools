"""Combine seed phrases by XOR-ing their entropy and recomputing the checksum."""

import getpass
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction

from seed_tools.mnemonic import MIN_PARTS, from_entropy, to_entropy, xor_entropy

NAME = "xor"
HELP = "combine seed phrases by XOR-ing their entropy and recomputing the checksum"


def register(subparsers: _SubParsersAction) -> None:
    parser: ArgumentParser = subparsers.add_parser(NAME, help=HELP, description=HELP)
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read parts from stdin, one phrase per line (input is echoed)",
    )
    parser.add_argument(
        "--entropy",
        action="store_true",
        help="also print the combined entropy as hex",
    )
    parser.set_defaults(run=run)


def run(args: Namespace) -> int:
    if not args.stdin and not _stdin_is_tty():
        raise ValueError(
            "stdin is not a terminal — rerun interactively, or pass --stdin to read "
            "one phrase per line"
        )
    try:
        parts = _read_parts(args.stdin)
    except (EOFError, KeyboardInterrupt):
        # Ctrl-D or Ctrl-C at a prompt. Close the half-written line, then report
        # it like any other input problem instead of unwinding as a traceback.
        print(file=sys.stderr)
        raise ValueError("Aborted — no result was produced") from None

    combined = xor_entropy(parts)
    _reject_degenerate(combined, parts)

    words = from_entropy(combined)
    if to_entropy(words) != combined:
        raise ValueError("Self-check failed: the result did not round-trip")

    if args.entropy:
        print(f"entropy  {combined.hex()}")
    for number, word in enumerate(words, start=1):
        print(f"{number:2d}  {word}")
    # The same words again on one line, unlabelled, for transcribing in one go.
    print()
    print(" ".join(words))
    return 0


def _reject_degenerate(combined: bytes, parts: list[bytes]) -> None:
    if not any(combined):
        raise ValueError(
            "Parts cancel out to all-zero entropy — the result would be a "
            "well-known weak seed. Use independent parts."
        )
    if combined in parts:
        raise ValueError(
            "Parts cancel out — the result is identical to one of the parts, so "
            "the others add nothing. Use independent parts."
        )


def _read_parts(use_stdin: bool) -> list[bytes]:
    """Read parts until a blank line, decoding each one as it is entered."""
    read = _read_line_echoed if use_stdin else _read_line_hidden
    parts: list[bytes] = []
    while True:
        number = len(parts) + 1
        line = read(_prompt(number))
        if not line.strip():
            return parts
        # Decoded here rather than after the whole list is in, so a mistyped word
        # is caught while this part is still the one in front of the user, before
        # the remaining parts are typed.
        try:
            parts.append(to_entropy(line))
        except ValueError as error:
            raise ValueError(f"Part {number}: {error}") from None


def _prompt(number: int) -> str:
    if number <= MIN_PARTS:
        return f"Part {number}: "
    return f"Part {number} (blank to finish): "


def _read_line_hidden(prompt: str) -> str:
    return getpass.getpass(prompt)


def _read_line_echoed(prompt: str) -> str:
    # Prompt on stderr: stdout carries the result, which is often redirected.
    print(prompt, end="", file=sys.stderr, flush=True)
    return sys.stdin.readline()


def _stdin_is_tty() -> bool:
    return sys.stdin.isatty()
