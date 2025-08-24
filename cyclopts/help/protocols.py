from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderableType

    from .help import TableEntry
    from .specs import ColumnSpec


@runtime_checkable
class Converter(Protocol):
    """Protocol for TableEntry converters."""

    def __call__(self, out: "RenderableType", entry: "TableEntry") -> "RenderableType": ...


@runtime_checkable
class Formatter(Protocol):
    """Protocol for TableEntry converters."""

    def __call__(self, out: "RenderableType", entry: "TableEntry", col_spec: "ColumnSpec") -> "RenderableType": ...


@runtime_checkable
class LazyData(Protocol):
    """Protocol for TableEntry LazyData.

    A member of in a TableData instance can be a callable. This allows for some
    dyanic / lazy data gathering. Because the cell must be rendered, the callable's
    arguments need a protocol. That is, the current "out", and the whole entry
    """

    def __call__(self, entry: "TableEntry") -> "RenderableType": ...


@runtime_checkable
class ColumnSpecBuilder(Protocol):
    """Protocol for ColumnSpecBuilders.

    Some `ColumnSpecs` depends on rich.console.Console and
    rich.console.ConsoleOptions. Thus, builder are enforced
    to accept these arguments.
    """

    def __call__(
        self, console: "Console", options: "ConsoleOptions", entries: list["TableEntry"]
    ) -> tuple["ColumnSpec", ...]: ...
