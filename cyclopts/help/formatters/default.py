"""Default Rich-based help formatter."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console, RenderableType

    from cyclopts.help import HelpPanel

from cyclopts.help.silent import SILENT


def format_default(
    help_panels: list["HelpPanel"],
    usage: Any,
    description: Any,
    console: "Console",
) -> None:
    """Format help using Rich library for beautiful terminal output.

    Parameters
    ----------
    help_panels : list[HelpPanel]
        List of help panels to render.
    usage : Any
        The usage line (Text or str).
    description : Any
        The description (can be various Rich renderables).
    console : Console
        Console to render to.
    """
    if usage:
        console.print(usage)

    if description:
        console.print(description)

    for panel in help_panels:
        rendered = _render_panel_rich(panel, console)
        console.print(rendered)


def _render_panel_rich(help_panel: "HelpPanel", console: "Console") -> "RenderableType":
    """Render a single help panel.

    This extracts the logic from HelpPanel.__rich_console__.
    """
    if not help_panel.entries:
        return SILENT

    from rich.console import Group as RichGroup
    from rich.console import NewLine
    from rich.text import Text

    panel_description = help_panel.description
    if isinstance(panel_description, Text):
        panel_description.end = ""

        if panel_description.plain:
            panel_description = RichGroup(panel_description, NewLine(2))

    # Realize spec, build table, and add entries
    table_spec = help_panel.table_spec.realize_columns(console, console.options, help_panel.entries)
    table = table_spec.build()
    table_spec.add_entries(table, help_panel.entries)

    # Build the panel
    if help_panel.panel_spec.title is None:
        panel = help_panel.panel_spec.build(RichGroup(panel_description, table), title=help_panel.title)
    else:
        panel = help_panel.panel_spec.build(RichGroup(panel_description, table))

    return panel
