"""Reading seed phrases from a terminal, shared by the tools that ask for one.

Hidden by default: a phrase typed at a prompt is never echoed, never written
anywhere, and never taken from argv, where the shell would keep it in history.
The one exception is `row_reader` — see the reasoning there.
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


def row_reader() -> Callable[[str], str]:
    """How to read one row of a plate being read back — echoed, typed or piped.

    The exception to hiding input. What is entered here is a pattern of holes
    being checked against the plate in the reader's hand, and a transcription
    that cannot be seen cannot be proofread — which is the whole point of
    reading a plate back. The words it decodes to are printed anyway.

    Takes no `use_stdin`: at end of input `readline` returns an empty string,
    which ends the list exactly as a blank line typed at a prompt does.
    """
    return read_line_echoed


def require_interactive_or_stdin(use_stdin: bool, stdin_reads: str) -> None:
    """Refuse to prompt when nobody is there to type, and to read a typed pipe.

    `stdin_reads` completes "pass --stdin to read ..." — what the flag means
    differs per tool, so each one describes its own input.

    Both directions are checked. Without --stdin, a pipe has nobody to prompt.
    With it, a terminal would echo whatever is typed straight into scrollback
    and any session recording — the exposure the hidden prompt exists to
    prevent, reachable by one slipped flag.
    """
    if not use_stdin and not stdin_is_tty():
        raise ValueError(
            "stdin is not a terminal — rerun interactively, or pass --stdin to read "
            f"{stdin_reads}"
        )
    if use_stdin and stdin_is_tty():
        raise ValueError(
            "stdin is a terminal — drop --stdin to be prompted, or pipe in "
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
