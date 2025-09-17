import math
import textwrap
from collections.abc import Iterable
from functools import partial
from typing import TYPE_CHECKING, Literal, Optional, Union

from cyclopts.utils import frozen

if TYPE_CHECKING:
    from rich.box import Box
    from rich.console import Console, ConsoleOptions, RenderableType
    from rich.padding import PaddingDimensions
    from rich.panel import Panel
    from rich.style import StyleType
    from rich.table import Table

    from cyclopts.help import HelpEntry
    from cyclopts.help.protocols import Renderer


def asterisk_renderer(entry: "HelpEntry") -> "RenderableType":
    """Render an asterisk for required parameters.

    Parameters
    ----------
    entry : HelpEntry
        The table entry to render.

    Returns
    -------
    ~rich.console.RenderableType
        "*" if required, empty string otherwise.
    """
    return "*" if entry.required else ""


def name_renderer(entry: "HelpEntry") -> "RenderableType":
    """Render the names column by combining names and shorts.

    Parameters
    ----------
    entry : HelpEntry
        The table entry to render.

    Returns
    -------
    ~rich.console.RenderableType
        Combined names and shorts as a string.
    """
    names_str = " ".join(entry.names) if entry.names else ""
    shorts_str = " ".join(entry.shorts) if entry.shorts else ""

    if names_str and shorts_str:
        return names_str + " " + shorts_str
    return names_str or shorts_str


def wrapped_name_renderer(entry: "HelpEntry", max_width: Optional[int] = None) -> "RenderableType":
    """Render names with text wrapping.

    Parameters
    ----------
    entry : HelpEntry
        The table entry to render.
    max_width : Optional[int]
        Maximum width for wrapping.

    Returns
    -------
    ~rich.console.RenderableType
        Wrapped names text.
    """
    text = str(name_renderer(entry))

    wrap = partial(
        textwrap.wrap,
        subsequent_indent="  ",
        break_on_hyphens=False,
        tabsize=4,
    )

    if max_width:
        return "\n".join(wrap(text, max_width))
    else:
        return "\n".join(wrap(text))


def description_renderer(entry: "HelpEntry") -> "RenderableType":
    """Render the description column.

    Parameters
    ----------
    entry : HelpEntry
        The table entry to render.

    Returns
    -------
    ~rich.console.RenderableType
        The description or empty string.
    """
    return entry.description if entry.description is not None else ""


@frozen
class ColumnSpec:
    """Specification for a single column in a help table.

    Used by :class:`~cyclopts.help.formatters.default.DefaultFormatter` to define
    how individual columns are rendered in help tables. Each column can have its
    own renderer, styling, and layout properties.

    See Also
    --------
    ~cyclopts.help.formatters.default.DefaultFormatter : The formatter that uses these specs.
    ~cyclopts.help.specs.TableSpec : Specification for the entire table.
    ~cyclopts.help.specs.PanelSpec : Specification for the outer panel.
    """

    renderer: Union[str, "Renderer"]
    """Specifies how to extract and render cell content from a :class:`~cyclopts.help.HelpEntry`.

    Can be either:

    - A string: The attribute name to retrieve from :class:`~cyclopts.help.HelpEntry` (e.g., 'names',
      'description', 'required', 'type'). The value is retrieved using
      :meth:`~cyclopts.help.HelpEntry.get` and displayed as-is.
    - A callable: A function matching the :class:`~cyclopts.help.protocols.Renderer` protocol.
      The function receives a :class:`~cyclopts.help.HelpEntry` and should return a
      :class:`~rich.console.RenderableType` (str, :class:`~rich.text.Text`, or other Rich renderable).

    Examples::

        # String renderer - get attribute directly
        ColumnSpec(renderer="description")

        # Callable renderer - custom formatting
        def format_names(entry: HelpEntry) -> str:
            return ", ".join(entry.names) if entry.names else ""
        ColumnSpec(renderer=format_names)
    """

    header: str = ""
    """Column header text displayed at the top of the column.

    Example::

        header="Options" renders:
        ┌─────────┬────────────┐
        │ Options │ Description│
        ├─────────┼────────────┤
        │ --help  │ Show help  │
        └─────────┴────────────┘
    """

    footer: str = ""
    """Column footer text displayed at the bottom of the column.

    Example::

        footer="Required" renders:
        ┌──────────┬────────────┐
        │ --help   │ Show help  │
        ├──────────┼────────────┤
        │ Required │            │
        └──────────┴────────────┘
    """

    header_style: Optional["StyleType"] = None
    """Rich style applied to the column header text.

    Example::

        header_style="bold cyan" renders the header in bold cyan color:
        [bold cyan]Options[/bold cyan]
    """

    footer_style: Optional["StyleType"] = None
    """Rich style applied to the column footer text.

    Example::

        footer_style="dim italic" renders the footer in dim italic:
        [dim italic]Required[/dim italic]
    """

    style: Optional["StyleType"] = None
    """Default Rich style applied to all cells in this column.

    Example::

        style="cyan" renders all cell content in cyan:
        [cyan]--verbose[/cyan]
        [cyan]--debug[/cyan]
    """

    justify: Literal["default", "left", "center", "right", "full"] = "left"
    """Text justification within the column.

    Example::

        justify="center" centers text in column:
        │   --help   │
        justify="right" aligns text to the right:
        │      --help│
    """

    vertical: Literal["top", "middle", "bottom"] = "top"
    """Vertical alignment of text within cells when cells have multiple lines.

    Example::

        vertical="middle" with multi-line cells:
        │        │ Line 1    │
        │ --help │ Line 2    │  <- --help is vertically centered
        │        │ Line 3    │
    """

    overflow: Literal["fold", "crop", "ellipsis", "ignore"] = "ellipsis"
    """How to handle text that exceeds column width.

    Example::

        overflow="ellipsis" with long text:
        │ --very-long-option-na... │
        overflow="fold" wraps to next line:
        │ --very-long-option-     │
        │ name                    │
    """

    width: Optional[int] = None
    """Fixed width for the column in characters.

    Example::

        width=10 creates a column exactly 10 characters wide:
        │ --help    │  <- exactly 10 chars
    """

    min_width: Optional[int] = None
    """Minimum width for the column in characters.

    Example::

        min_width=15 ensures column is at least 15 chars:
        │ --h           │  <- padded to 15 chars minimum
    """

    max_width: Optional[int] = None
    """Maximum width for the column in characters.

    Example::

        max_width=20 limits column width:
        │ --very-long-option...│  <- truncated at 20 chars
    """

    ratio: Optional[int] = None
    """Relative width ratio compared to other columns.

    Example::

        Column A with ratio=2, Column B with ratio=1:
        │     Column A (2/3 width)     │ Col B (1/3) │
    """

    no_wrap: bool = False
    """Prevent text wrapping in the column.

    Example::

        no_wrap=True forces single line (may overflow):
        │ --very-long-option-name-that-wont-wrap │
        no_wrap=False allows wrapping:
        │ --very-long-option- │
        │ name-that-wraps    │
    """

    def render_cell(self, entry: "HelpEntry") -> "RenderableType":
        """Render the cell content based on the renderer type.

        If renderer is a string, retrieves that attribute from the entry.
        If renderer is callable, calls it with the entry.
        """
        if isinstance(self.renderer, str):
            value = str(getattr(entry, self.renderer))
        elif callable(self.renderer):
            value = self.renderer(entry)
        else:
            value = None
        return "" if value is None else value


# For Parameters:
AsteriskColumn = ColumnSpec(renderer=asterisk_renderer, header="", justify="left", width=1, style="red bold")

NameColumn = ColumnSpec(
    renderer=name_renderer,
    header="",
    justify="left",
    style="cyan",
)

DescriptionColumn = ColumnSpec(renderer=description_renderer, header="", justify="left", overflow="fold")


def get_default_command_columns(
    console: "Console", options: "ConsoleOptions", entries: list["HelpEntry"]
) -> tuple[ColumnSpec, ...]:
    """Get default column specifications for command display.

    Parameters
    ----------
    console : ~rich.console.Console
        Rich console for width calculations.
    options : ~rich.console.ConsoleOptions
        Console rendering options.
    entries : list[HelpEntry]
        Command entries to display.

    Returns
    -------
    tuple[ColumnSpec, ...]
        Column specifications for command table.
    """
    max_width = math.ceil(console.width * 0.35)
    command_column = ColumnSpec(
        renderer=partial(wrapped_name_renderer, max_width=max_width),
        header="",
        justify="left",
        style="cyan",
        max_width=max_width,
    )

    return (
        command_column,
        DescriptionColumn,
    )


def get_default_parameter_columns(
    console: "Console", options: "ConsoleOptions", entries: list["HelpEntry"]
) -> tuple[ColumnSpec, ...]:
    """Get default column specifications for parameter display.

    Parameters
    ----------
    console : ~rich.console.Console
        Rich console for width calculations.
    options : ~rich.console.ConsoleOptions
        Console rendering options.
    entries : list[HelpEntry]
        Parameter entries to display.

    Returns
    -------
    tuple[ColumnSpec, ...]
        Column specifications for parameter table.
    """
    max_width = math.ceil(console.width * 0.35)
    name_column = ColumnSpec(
        renderer=partial(wrapped_name_renderer, max_width=max_width),
        header="",
        justify="left",
        style="cyan",
        max_width=max_width,
    )

    if any(x.required for x in entries):
        return (
            AsteriskColumn,
            name_column,
            DescriptionColumn,
        )
    else:
        return (
            name_column,
            DescriptionColumn,
        )


@frozen
class TableSpec:
    """Specification for table layout and styling.

    Used by :class:`~cyclopts.help.formatters.default.DefaultFormatter` to control
    the appearance of tables that display commands and parameters. This spec defines
    table-wide properties like borders, headers, and padding.

    See Also
    --------
    ~cyclopts.help.formatters.default.DefaultFormatter : The formatter that uses these specs.
    ~cyclopts.help.specs.ColumnSpec : Specification for individual columns.
    ~cyclopts.help.specs.PanelSpec : Specification for the outer panel.
    """

    # Intrinsic table styling/config
    title: Optional[str] = None
    """Title text displayed above the table.

    Example::

        title="Available Options" renders:
        Available Options
        ┌────────┬────────────┐
        │ --help │ Show help  │
        └────────┴────────────┘
    """

    caption: Optional[str] = None
    """Caption text displayed below the table.

    Example::

        caption="Use --help for more info" renders:
        ┌────────┬────────────┐
        │ --help │ Show help  │
        └────────┴────────────┘
        Use --help for more info
    """

    style: Optional["StyleType"] = None
    """Default style applied to the entire table.

    Example::

        style="dim" renders the entire table in dim style:
        [dim]┌────────┬────────────┐
        │ --help │ Show help  │
        └────────┴────────────┘[/dim]
    """

    border_style: Optional["StyleType"] = None
    """Style applied to table borders.

    Example::

        border_style="cyan" renders borders in cyan:
        [cyan]┌────────┬────────────┐[/cyan]
        [cyan]│[/cyan] --help [cyan]│[/cyan] Show help  [cyan]│[/cyan]
        [cyan]└────────┴────────────┘[/cyan]
    """

    header_style: Optional["StyleType"] = None
    """Default style for all table headers (can be overridden per column).

    Example::

        header_style="bold underline" with show_header=True:
        [bold underline]Options  Description[/bold underline]
        --help   Show help
    """

    footer_style: Optional["StyleType"] = None
    """Default style for all table footers (can be overridden per column).

    Example::

        footer_style="italic" with show_footer=True:
        --help   Show help
        [italic]Required Optional[/italic]
    """

    box: Optional["Box"] = None
    """Box drawing style for the table borders.

    Example::

        box=SIMPLE renders:
          --help   Show help
        box=DOUBLE renders:
        ╔════════╦════════════╗
        ║ --help ║ Show help  ║
        ╚════════╩════════════╝
    """

    show_header: bool = False
    """Whether to display column headers.

    Example::

        show_header=True with header="Option" renders:
        Option   Description
        --help   Show help
        show_header=False renders:
        --help   Show help
    """

    show_footer: bool = False
    """Whether to display column footers.

    Example::

        show_footer=True with footer="Required" renders:
        --help   Show help
        Required
    """

    show_lines: bool = False
    """Whether to show horizontal lines between rows.

    Example::

        show_lines=True renders:
        ┌────────┬────────────┐
        │ --help │ Show help  │
        ├────────┼────────────┤
        │ --verbose │ Verbose  │
        └────────┴────────────┘
    """

    expand: bool = False
    """Whether the table should expand to fill available width.

    Example::

        expand=True with 80 char terminal:
        ┌──────────────────────────────────┬───────────────────────────────────────────┐
        │ --help                           │ Show help                                 │
        └──────────────────────────────────┴───────────────────────────────────────────┘
    """

    pad_edge: bool = False
    """Whether to add padding to the table edges.

    Example::

        pad_edge=True adds space around table edges:
        ┌──────────┬──────────────┐
        │  --help  │  Show help  │  <- extra padding
        └──────────┴──────────────┘
    """

    padding: "PaddingDimensions" = (0, 2, 0, 0)
    """Padding around cell content (top, right, bottom, left).

    Example::

        padding=(1, 2, 1, 2) adds vertical and horizontal padding:
        ┌────────────┬────────────────┐
        │            │                │  <- top padding
        │  --help    │  Show help     │  <- left/right padding
        │            │                │  <- bottom padding
        └────────────┴────────────────┘
    """

    collapse_padding: bool = False
    """Whether to collapse padding when adjacent cells are empty.

    Example::

        collapse_padding=True removes padding between empty cells:
        Normal:    │  --help  │          │  <- padding maintained
        Collapsed: │  --help  ││  <- padding collapsed for empty cell
    """

    def build(
        self,
        columns: tuple[ColumnSpec, ...],
        entries: Iterable["HelpEntry"],
        **overrides,
    ) -> "Table":
        """Construct and populate a rich.Table.

        Parameters
        ----------
        columns : tuple[ColumnSpec, ...]
            Column specifications defining the table structure.
        entries : Iterable[HelpEntry]
            Table entries to populate the table with.
        **overrides
            Per-render overrides for table settings.

        Returns
        -------
        Table
            A populated Rich Table.
        """
        # If show_header is True but all columns have empty headers, don't show the header
        # This prevents an empty line from appearing at the top of the table
        show_header = self.show_header
        if show_header and all(not col.header for col in columns):
            show_header = False

        opts = {
            "title": self.title,
            "caption": self.caption,
            "style": self.style,
            "border_style": self.border_style,
            "header_style": self.header_style,
            "footer_style": self.footer_style,
            "box": self.box,
            "show_header": show_header,
            "show_footer": self.show_footer,
            "show_lines": self.show_lines,
            "expand": self.expand,
            "pad_edge": self.pad_edge,
            "padding": self.padding,
            "collapse_padding": self.collapse_padding,
        }
        opts.update(overrides)

        from rich.table import Table

        table = Table(**opts)

        # Add columns
        for column in columns:
            table.add_column(
                column.header,
                footer=column.footer,
                header_style=column.header_style,
                footer_style=column.footer_style,
                style=column.style,
                justify=column.justify,
                vertical=column.vertical,
                overflow=column.overflow,
                width=column.width,
                min_width=column.min_width,
                max_width=column.max_width,
                ratio=column.ratio,
                no_wrap=column.no_wrap,
            )

        # Add entries
        for e in entries:
            cells = [col.render_cell(e) for col in columns]
            table.add_row(*cells)

        return table


@frozen
class PanelSpec:
    """Specification for panel (outer box) styling.

    Used by :class:`~cyclopts.help.formatters.default.DefaultFormatter` to control
    the appearance of the outer panel that wraps help sections. This spec defines
    the panel's border, title, subtitle, and overall styling.

    See Also
    --------
    ~cyclopts.help.formatters.default.DefaultFormatter : The formatter that uses these specs.
    ~cyclopts.help.specs.TableSpec : Specification for the inner table.
    ~cyclopts.help.specs.ColumnSpec : Specification for individual columns.
    """

    # Content-independent panel chrome
    title: Optional["RenderableType"] = None
    """Title text displayed at the top of the panel.

    Example::

        title="Help Information" renders:
        ╭─ Help Information ────────────────╮
        │ Panel content here              │
        ╰─────────────────────────────────╯
    """

    subtitle: Optional["RenderableType"] = None
    """Subtitle text displayed at the bottom of the panel.

    Example::

        subtitle="Version 1.0" renders:
        ╭─────────────────────────────────╮
        │ Panel content here              │
        ╰───────────── Version 1.0 ──────╯
    """

    title_align: Literal["left", "center", "right"] = "left"
    """Alignment of the title text within the panel.

    Example::

        title_align="center" renders:
        ╭──────── Title Here ─────────╮
        title_align="right" renders:
        ╭──────────────── Title Here ─╮
    """

    subtitle_align: Literal["left", "center", "right"] = "center"
    """Alignment of the subtitle text within the panel.

    Example::

        subtitle_align="left" renders:
        ╰─ Subtitle ───────────────────╯
        subtitle_align="right" renders:
        ╰─────────────────── Subtitle ─╯
    """

    style: Optional["StyleType"] = "none"
    """Style applied to the panel background.

    Example::

        style="on blue" renders the panel with blue background:
        [on blue]╭─────────────────────────────────╮
        │ Panel content here              │
        ╰─────────────────────────────────╯[/on blue]
    """

    border_style: Optional["StyleType"] = "none"
    """Style applied to the panel border.

    Example::

        border_style="cyan bold" renders borders in bold cyan:
        [cyan bold]╭─────────────────────────────────╮[/cyan bold]
        [cyan bold]│[/cyan bold] Panel content here              [cyan bold]│[/cyan bold]
        [cyan bold]╰─────────────────────────────────╯[/cyan bold]
    """

    box: Optional["Box"] = None  # Will use ROUNDED as default when building
    """Box drawing style for the panel border.

    Example::

        box=SQUARE renders:
        ┌─────────────────────────────────┐
        │ Panel content here              │
        └─────────────────────────────────┘
        box=DOUBLE renders:
        ╔═════════════════════════════════╗
        ║ Panel content here              ║
        ╚═════════════════════════════════╝
    """

    padding: "PaddingDimensions" = (0, 1)
    """Padding inside the panel (top/bottom, left/right) or (top, right, bottom, left).

    Example::

        padding=(1, 2) adds vertical and horizontal padding:
        ╭─────────────────────────────────╮
        │                                │  <- top padding
        │  Panel content here            │  <- left/right padding
        │                                │  <- bottom padding
        ╰─────────────────────────────────╯
    """

    expand: bool = True
    """Whether the panel should expand to fill available width.

    Example::

        expand=True with 60 char terminal:
        ╭────────────────────────────────────────────────────────╮
        │ Content                                                  │
        ╰────────────────────────────────────────────────────────╯
        expand=False:
        ╭─────────╮
        │ Content │
        ╰─────────╯
    """

    width: Optional[int] = None
    """Fixed width for the panel in characters.

    Example::

        width=40 creates a panel exactly 40 characters wide:
        ╭────────────────────────────────────╮
        │ Content                            │
        ╰────────────────────────────────────╯
    """

    height: Optional[int] = None
    """Fixed height for the panel in lines.

    Example::

        height=5 creates a panel exactly 5 lines tall:
        ╭─────────────────────────────────╮
        │ Content                        │
        │                                │  <- padded to height
        │                                │
        ╰─────────────────────────────────╯
    """

    safe_box: Optional[bool] = None
    """Whether to use ASCII-safe box characters for compatibility.

    Example::

        safe_box=True uses ASCII characters:
        +----------------------------------+
        | Panel content here               |
        +----------------------------------+
        safe_box=False uses Unicode box drawing:
        ╭─────────────────────────────────╮
        │ Panel content here              │
        ╰─────────────────────────────────╯
    """

    def build(self, renderable: "RenderableType", **overrides) -> "Panel":
        """Create a Panel around `renderable`. Use kwargs to override spec per render."""
        # Import box here for lazy loading
        box = self.box
        if box is None:
            from rich.box import ROUNDED

            box = ROUNDED

        opts = {
            "title_align": self.title_align,
            "subtitle_align": self.subtitle_align,
            "style": self.style,
            "border_style": self.border_style,
            "box": box,
            "padding": self.padding,
            "expand": self.expand,
            "width": self.width,
            "height": self.height,
            "safe_box": self.safe_box,
        }
        if self.title is not None:
            opts["title"] = self.title
        if self.subtitle is not None:
            opts["subtitle"] = self.subtitle

        opts.update(overrides)

        from rich.panel import Panel

        return Panel(renderable, **opts)
