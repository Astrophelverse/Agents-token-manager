"""
style.py

Small terminal styling helpers, built on plain ANSI escape codes. No
external dependency (no rich, no colorama) on purpose, since this project
should stay a single `pip install .` away from working anywhere, without
pulling in a styling library just to print some color.

If the output is not a real terminal (e.g. piped into a file or another
program), all styling is automatically disabled, so redirected output and
log files stay clean plain text instead of filling up with escape codes.
"""

import sys


_IS_TTY = sys.stdout.isatty()


class _Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"
    GREY = "\033[90m"


def _wrap(text, code):
    if not _IS_TTY:
        return text
    return code + text + _Colors.RESET


def bold(text):
    return _wrap(text, _Colors.BOLD)


def dim(text):
    return _wrap(text, _Colors.DIM)


def cyan(text):
    return _wrap(text, _Colors.CYAN)


def green(text):
    return _wrap(text, _Colors.GREEN)


def yellow(text):
    return _wrap(text, _Colors.YELLOW)


def red(text):
    return _wrap(text, _Colors.RED)


def magenta(text):
    return _wrap(text, _Colors.MAGENTA)


def blue(text):
    return _wrap(text, _Colors.BLUE)


def grey(text):
    return _wrap(text, _Colors.GREY)


def header(title):
    """A bold, boxed title line used for the banner at the start of a scan."""
    bar = "=" * (len(title) + 4)
    lines = [cyan(bar), cyan("  " + title + "  "), cyan(bar)]
    return "\n".join(lines)


def step(label):
    """A single step line, e.g. '-> Scanning ...', printed as the tool works."""
    return cyan("->") + " " + label


def success(label):
    return green("[ok]") + " " + label


def warn(label):
    return yellow("[warn]") + " " + label


def fail(label):
    return red("[error]") + " " + label


def kv(key, value):
    """A key/value summary line, e.g. 'Files found        12'."""
    return dim(key.ljust(28)) + bold(str(value))


def bar(percent, width=24):
    """
    A simple text progress/ratio bar, e.g. [###########.........] 55%
    Used to visualize the compression ratio at the end of a scan.
    """
    filled = int(width * max(0, min(percent, 100)) / 100)
    empty = width - filled
    bar_str = "#" * filled + "." * empty
    return green("[" + bar_str + "]") + " " + bold(str(round(percent)) + "%")
