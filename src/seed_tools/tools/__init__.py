from argparse import _SubParsersAction

from seed_tools.tools import checksum, lookup, tinyseed, xor

# Every tool module registers its own subcommand. Add new tools here.
TOOLS = [checksum, lookup, tinyseed, xor]


def register_all(subparsers: _SubParsersAction) -> None:
    for tool in TOOLS:
        tool.register(subparsers)
