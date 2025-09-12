"""Default Rich-based help formatter."""

from typing import TYPE_CHECKING, Any, Optional

from attrs import define

from cyclopts.help.silent import SILENT

if TYPE_CHECKING:
    from rich.console import Console, RenderableType

    from cyclopts.help import HelpPanel
    from cyclopts.help.specs import PanelSpec, TableSpec


@define
class DefaultFormatter:
    """Default help formatter using Rich library with customizable table and panel specs.

    Parameters
    ----------
    table_spec : Optional[TableSpec]
        Table specification for rendering parameter/command tables.
        If not provided, a default TableSpec will be created based on panel format.
    panel_spec : PanelSpec
        Panel specification for rendering help panels.
        If not provided, a default PanelSpec will be created.
    """

    table_spec: Optional["TableSpec"] = None
    panel_spec: Optional["PanelSpec"] = None

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

        from cyclopts.help.specs import PanelSpec, TableSpec

        panel_description = help_panel.description
        if isinstance(panel_description, Text):
            panel_description.end = ""

            if panel_description.plain:
                panel_description = RichGroup(panel_description, NewLine(2))

        if self.table_spec is None:
            table_spec = TableSpec.for_commands() if help_panel.format == "command" else TableSpec.for_parameters()
        else:
            table_spec = self.table_spec
        panel_spec = self.panel_spec or PanelSpec()

        # Realize spec, build table, and add entries
        table_spec = table_spec.realize_columns(console, console.options, help_panel.entries)
        table = table_spec.build()
        table_spec.add_entries(table, help_panel.entries)

        # Build the panel
        if panel_spec.title is None:
            panel = panel_spec.build(RichGroup(panel_description, table), title=help_panel.title)
        else:
            panel = panel_spec.build(RichGroup(panel_description, table))

        return panel
