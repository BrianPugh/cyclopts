from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderableType

    from .help import HelpEntry, HelpPanel
    from .specs import ColumnSpec


@runtime_checkable
class Renderer(Protocol):
    """Protocol for column renderers that transform HelpEntry to display content."""

    def __call__(self, entry: "HelpEntry") -> "RenderableType": ...


@runtime_checkable
class ColumnSpecBuilder(Protocol):
    """Protocol for ColumnSpecBuilders.

    Some `ColumnSpecs` depends on rich.console.Console and
    rich.console.ConsoleOptions. Thus, builder are enforced
    to accept these arguments.
    """

    def __call__(
        self, console: "Console", options: "ConsoleOptions", entries: list["HelpEntry"]
    ) -> tuple["ColumnSpec", ...]: ...


@runtime_checkable
class HelpFormatter(Protocol):
    """Protocol for help formatter functions."""

    def __call__(
        self,
        panel: "HelpPanel",
        console: "Console",
    ) -> None:
        """Format and render a single help panel.

        Parameters
        ----------
        panel : HelpPanel
            Help panel to render (commands, parameters, etc).
        console : Console
            Console to render to.
        """
        ...

    def render_usage(
        self,
        usage: Any,
        console: "Console",
    ) -> None:
        """Render the usage line.

        Parameters
        ----------
        usage : Any
            The usage line to display.
        console : Console
            Console to render to.
        """
        ...

    def render_description(
        self,
        description: Any,
        console: "Console",
    ) -> None:
        """Render the description.

        Parameters
        ----------
        description : Any
            The app/command description to display.
        console : Console
            Console to render to.
        """
        ...
