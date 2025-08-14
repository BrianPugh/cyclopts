from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .specs import AbstractTableEntry, ColumnSpec


@runtime_checkable
class Converter(Protocol):
    """Protocol for AbstractTableEntry converters."""

    from rich.console import RenderableType

    def __call__(self, out: RenderableType, entry: AbstractTableEntry) -> RenderableType: ...


@runtime_checkable
class Formatter(Protocol):
    """Protocol for AbstractTableEntry converters."""

    from rich.console import RenderableType

    def __call__(self, out: RenderableType, entry: AbstractTableEntry, col_specs: ColumnSpec) -> RenderableType: ...


@runtime_checkable
class LazyData(Protocol):
    """Protocol for AbstractTableEntry LazyData.

    A member of in a TableData instance can be a callable. This allows for some
    dyanic / lazy data gathering. Because the cell must be rendered, the callable's
    arguments need a protocol. That is, the current "out", and the whole entry
    """

    from rich.console import RenderableType

    def __call__(self, entry: AbstractTableEntry) -> RenderableType: ...
