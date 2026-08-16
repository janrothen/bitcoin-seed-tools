import logging
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence

from seed_tools.tools import register_all

logger = logging.getLogger(__name__)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="seed-tools",
        description="Local command-line tools for working with BIP-39 seed phrases.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    register_all(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args: Namespace = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return args.run(args)
    except ValueError as error:
        logger.error("%s", error)
        return 2


if __name__ == "__main__":
    sys.exit(main())
