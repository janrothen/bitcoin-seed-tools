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
    # Every part is checksum-verified here, so a mistyped word is caught before it
    # can silently produce a different — and unrecoverable — wallet.
    parts = [to_entropy(phrase) for phrase in _read_parts(args.stdin)]
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


def _read_parts(use_stdin: bool) -> list[str]:
    read = _read_line_echoed if use_stdin else _read_line_hidden
    parts: list[str] = []
    while True:
        line = read(_prompt(len(parts) + 1))
        if not line.strip():
            return parts
        parts.append(line)


def _prompt(number: int) -> str:
    if number <= MIN_PARTS:
        return f"Part {number}: "
    return f"Part {number} (blank to finish): "


def _read_line_hidden(prompt: str) -> str:
    return getpass.getpass(prompt)


def _read_line_echoed(prompt: str) -> str:
    return sys.stdin.readline()


def _stdin_is_tty() -> bool:
    return sys.stdin.isatty()
