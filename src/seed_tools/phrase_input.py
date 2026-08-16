"""Reading seed phrases from a terminal, shared by the tools that ask for one.

Hidden by default: a phrase typed at a prompt is never echoed, never written
anywhere, and never taken from argv, where the shell would keep it in history.
"""

import getpass
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager


def stdin_is_tty() -> bool:
    return sys.stdin.isatty()


def read_line_hidden(prompt: str) -> str:
    return getpass.getpass(prompt)


def read_line_echoed(prompt: str) -> str:
    # Prompt on stderr: stdout carries the result, which is often redirected.
    print(prompt, end="", file=sys.stderr, flush=True)
    return sys.stdin.readline()


def read_all_echoed(prompt: str) -> str:
    # Prompt on stderr: stdout carries the result, which is often redirected.
    print(prompt, end="", file=sys.stderr, flush=True)
    return sys.stdin.read()


def line_reader(use_stdin: bool) -> Callable[[str], str]:
    """Pick how to read one line of several — a newline separates the entries.

    Looked up on call so tests can patch either one.
    """
    return read_line_echoed if use_stdin else read_line_hidden


def phrase_reader(use_stdin: bool) -> Callable[[str], str]:
    """Pick how to read a single phrase, which is all the input there is.

    A newline carries no meaning inside a phrase — `normalize` collapses any
    whitespace — so a piped phrase may wrap across lines and all of it counts.
    Reading only the first line would silently drop the rest of a backup that
    was stored wrapped, and half a plate can still pass the checksum.
    """
    return read_all_echoed if use_stdin else read_line_hidden


def require_interactive_or_stdin(use_stdin: bool, stdin_reads: str) -> None:
    """Refuse to prompt when nobody is there to type, unless --stdin was passed.

    `stdin_reads` completes "pass --stdin to read ..." — what the flag means
    differs per tool, so each one describes its own input.
    """
    if not use_stdin and not stdin_is_tty():
        raise ValueError(
            "stdin is not a terminal — rerun interactively, or pass --stdin to read "
            f"{stdin_reads}"
        )


@contextmanager
def aborting() -> Iterator[None]:
    """Turn Ctrl-D or Ctrl-C at a prompt into an ordinary input error.

    Close the half-written line, then report it like any other input problem
    instead of unwinding as a traceback.
    """
    try:
        yield
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
        raise ValueError("Aborted — no result was produced") from None
