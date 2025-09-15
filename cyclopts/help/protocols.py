from typing import TYPE_CHECKING, Protocol, runtime_checkable

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
    """Protocol for help formatter functions.

    Implementations may optionally provide the following methods for custom rendering:

    .. code-block:: python

        def render_usage(self, usage: Any, console: Console) -> None:
            \"\"\"Render the usage line.\"\"\"
            ...

        def render_description(self, description: Any, console: Console) -> None:
            \"\"\"Render the description.\"\"\"
            ...

    If these methods are not provided, default rendering will be used.
    """

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
