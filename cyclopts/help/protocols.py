from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from rich.console import RenderableType

    from .help import AbstractTableEntry
    from .specs import ColumnSpec


@runtime_checkable
class Converter(Protocol):
    """Protocol for AbstractTableEntry converters."""

    def __call__(self, out: "RenderableType", entry: "AbstractTableEntry") -> "RenderableType": ...


@runtime_checkable
class Formatter(Protocol):
    """Protocol for AbstractTableEntry converters."""

    def __call__(
        self, out: "RenderableType", entry: "AbstractTableEntry", col_spec: "ColumnSpec"
    ) -> "RenderableType": ...


@runtime_checkable
class LazyData(Protocol):
    """Protocol for AbstractTableEntry LazyData.

    A member of in a TableData instance can be a callable. This allows for some
    dyanic / lazy data gathering. Because the cell must be rendered, the callable's
    arguments need a protocol. That is, the current "out", and the whole entry
    """

    def __call__(self, entry: "AbstractTableEntry") -> "RenderableType": ...
