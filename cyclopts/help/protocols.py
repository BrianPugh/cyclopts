from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderableType

    from .help import HelpPanel, TableEntry
    from .specs import ColumnSpec


@runtime_checkable
class Converter(Protocol):
    """Protocol for TableEntry converters."""

    def __call__(self, entry: "TableEntry") -> "RenderableType": ...


@runtime_checkable
class TableEntryFormatter(Protocol):
    """Protocol for TableEntry converters."""

    def __call__(self, entry: "TableEntry", col_spec: "ColumnSpec") -> "RenderableType": ...


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


@runtime_checkable
class HelpFormatter(Protocol):
    """Protocol for help formatter functions."""

    def __call__(
        self,
        help_panels: list["HelpPanel"],
        usage: Any,
        description: Any,
        console: "Console",
    ) -> None:
        """Format and render all help components.

        Parameters
        ----------
        help_panels : list[HelpPanel]
            List of help panels to render (commands, parameters, etc).
        usage : Any
            The usage line to display.
        description : Any
            The app/command description to display.
        console : Console
            Console to render to.
        """
        ...
