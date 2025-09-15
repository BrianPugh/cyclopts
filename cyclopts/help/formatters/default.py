"""Default Rich-based help formatter."""

from typing import TYPE_CHECKING, Any, Optional, Union

from attrs import define

from cyclopts.help.silent import SILENT

if TYPE_CHECKING:
    from rich.console import Console, RenderableType

    from cyclopts.help import HelpPanel
    from cyclopts.help.protocols import ColumnSpecBuilder
    from cyclopts.help.specs import ColumnSpec, PanelSpec, TableSpec


@define(kw_only=True)
class DefaultFormatter:
    """Default help formatter using Rich library with customizable specs.

    Parameters
    ----------
    panel_spec : Optional[PanelSpec]
        Panel specification for the outer box/panel styling.
    table_spec : Optional[TableSpec]
        Table specification for table styling (borders, padding, etc).
    column_specs : Optional[Union[tuple[ColumnSpec, ...], ColumnSpecBuilder]]
        Column specifications or builder function for table columns.

    Notes
    -----
    The relationship between these specs can be visualized as:

    ::

        ╭─ Commands ───────────────────────────────────────────────────────╮  ← panel_spec
        │ serve     Start the development server                           │     (border, title)
        │ --help    Display this message and exit.                         │
        ╰──────────────────────────────────────────────────────────────────╯
         ↑         ↑
         col[0]    col[1]
         (name)    (description)

        ╭─ Parameters ─────────────────────────────────────────────────────╮  ← panel_spec
        │ *  PORT --port        Server port number [required]              │
        │    VERBOSE --verbose  Enable verbose output [default: False]     │
        ╰──────────────────────────────────────────────────────────────────╯
         ↑  ↑                  ↑
         │  col[1]             col[2]
         │  (name/flags)       (description)
         │
         col[0]
         (required marker)

    Where:

    - ``panel_spec`` controls the outer panel appearance (border, title, etc.)
    - ``table_spec`` controls the inner table styling (no visible borders by default)
    - ``column_specs`` defines individual columns (width, style, alignment, etc.)
    """

    panel_spec: Optional["PanelSpec"] = None
    table_spec: Optional["TableSpec"] = None
    column_specs: Optional[Union[tuple["ColumnSpec", ...], "ColumnSpecBuilder"]] = None

    def __call__(
        self,
        panel: "HelpPanel",
        console: "Console",
    ) -> None:
        """Format and render a single help panel using Rich.

        Parameters
        ----------
        panel : HelpPanel
            Help panel to render.
        console : Console
            Console to render to.
        """
        rendered = self._render_panel(panel, console)
        console.print(rendered)

    def render_usage(
        self,
        usage: Any,
        console: "Console",
    ) -> None:
        """Render the usage line.

        Parameters
        ----------
        usage : Any
            The usage line (Text or str).
        console : Console
            Console to render to.
        """
        if usage:
            console.print(usage)

    def render_description(
        self,
        description: Any,
        console: "Console",
    ) -> None:
        """Render the description.

        Parameters
        ----------
        description : Any
            The description (can be various Rich renderables).
        console : Console
            Console to render to.
        """
        if description:
            console.print(description)

    def _render_panel(self, help_panel: "HelpPanel", console: "Console") -> "RenderableType":
        """Render a single help panel."""
        if not help_panel.entries:
            return SILENT

        from rich.console import Group as RichGroup
        from rich.console import NewLine
        from rich.text import Text

        from cyclopts.help.specs import (
            PanelSpec,
            TableSpec,
            get_default_command_columns,
            get_default_parameter_columns,
        )

        panel_description = help_panel.description
        if isinstance(panel_description, Text):
            panel_description.end = ""

            if panel_description.plain:
                panel_description = RichGroup(panel_description, NewLine(2))

        # Get table spec (styling only)
        table_spec = self.table_spec or TableSpec()
        panel_spec = self.panel_spec or PanelSpec()

        # Determine/Resolve column specs
        columns = self.column_specs
        if columns is None:
            # Use default columns based on panel format
            if help_panel.format == "command":
                columns = get_default_command_columns
            else:
                columns = get_default_parameter_columns

        if callable(columns):
            # It's a column builder
            columns = columns(console, console.options, help_panel.entries)

        # Build table with columns and entries
        table = table_spec.build(columns, help_panel.entries)

        # Build the panel
        if panel_spec.title is None:
            panel = panel_spec.build(RichGroup(panel_description, table), title=help_panel.title)
        else:
            panel = panel_spec.build(RichGroup(panel_description, table))

        return panel
