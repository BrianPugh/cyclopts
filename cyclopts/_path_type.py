"""StdioPath - A Path subclass that treats "-" as stdin/stdout.

Requires Python 3.12+ for proper Path subclassing support.
"""

import sys
from pathlib import Path
from typing import IO, TYPE_CHECKING

from cyclopts.parameter import Parameter

if TYPE_CHECKING:
    from collections.abc import Buffer


class _NonClosingIOWrapper:
    """Wrapper around an IO stream that doesn't close on context exit.

    This is used to wrap stdin/stdout so they can be used as context managers
    without being closed when the context exits.
    """

    def __init__(self, stream: IO):
        self._stream = stream

    def __enter__(self):
        return self._stream

    def __exit__(self, *args):
        pass  # Don't close the stream

    def __getattr__(self, name):
        return getattr(self._stream, name)


def _get_stream(mode: str) -> IO:
    """Get the appropriate stdio stream based on mode."""
    is_write = "w" in mode or "a" in mode
    is_binary = "b" in mode
    if is_write:
        return sys.stdout.buffer if is_binary else sys.stdout
    return sys.stdin.buffer if is_binary else sys.stdin


@Parameter(allow_leading_hyphen=True)
class StdioPath(Path):
    """A Path subclass that treats "-" as stdin (for reading) or stdout (for writing).

    Requires Python 3.12+ for proper Path subclassing support.

    This enables the common Unix convention where "-" represents stdin/stdout
    in command-line applications, while also allowing regular file paths.

    Examples
    --------
    >>> p = StdioPath("-")
    >>> with p.open("r") as f:
    ...     data = f.read()  # Reads from stdin

    >>> p = StdioPath("output.txt")
    >>> with p.open("w") as f:
    ...     f.write("hello")  # Writes to output.txt
    """

    __slots__ = ("_is_stdio",)

    def __new__(cls, *args, **kwargs):
        if args and str(args[0]) == "-":
            obj = object.__new__(cls)
            obj._is_stdio = True
            return obj
        obj = super().__new__(cls, *args, **kwargs)
        obj._is_stdio = False
        return obj

    @property
    def is_stdio(self) -> bool:
        """Return True if this represents stdin/stdout (created from '-')."""
        return self._is_stdio

    def __str__(self):
        return "-" if self._is_stdio else super().__str__()

    def __repr__(self):
        return f"StdioPath({str(self)!r})"

    def __fspath__(self):
        return "-" if self._is_stdio else super().__fspath__()

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        """Return True if path exists. Always True for stdio."""
        return True if self._is_stdio else super().exists(follow_symlinks=follow_symlinks)

    def open(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ):
        """Open the file or return stdin/stdout.

        For stdio paths, returns a wrapper around the appropriate stream
        (stdin for reading, stdout for writing) that doesn't close on context exit.
        For regular paths, behaves like the standard Path.open().
        """
        if self._is_stdio:
            return _NonClosingIOWrapper(_get_stream(mode))
        return super().open(mode, buffering, encoding, errors, newline)

    def read_text(self, encoding: str | None = None, errors: str | None = None, newline: str | None = None) -> str:
        """Read entire contents as text."""
        if self._is_stdio:
            return sys.stdin.buffer.read().decode(encoding or "utf-8", errors or "strict")
        return super().read_text(encoding=encoding, errors=errors, newline=newline)

    def read_bytes(self) -> bytes:
        """Read entire contents as bytes."""
        if self._is_stdio:
            return sys.stdin.buffer.read()
        return super().read_bytes()

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        """Write text data."""
        if self._is_stdio:
            sys.stdout.buffer.write(data.encode(encoding or "utf-8", errors or "strict"))
            return len(data)
        return super().write_text(data, encoding=encoding, errors=errors, newline=newline)

    def write_bytes(self, data: "Buffer") -> int:
        """Write binary data."""
        if self._is_stdio:
            return sys.stdout.buffer.write(data)
        return super().write_bytes(data)
