import math
import textwrap
from collections.abc import Iterable
from functools import partial
from typing import TYPE_CHECKING, Literal, Optional, Union

from rich.box import ROUNDED, Box
from rich.console import RenderableType
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

from cyclopts.utils import frozen

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions

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
    RenderableType
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
    RenderableType
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
    RenderableType
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
    RenderableType
        The description or empty string.
    """
    return entry.description if entry.description is not None else ""


@frozen
class ColumnSpec:
    PaddingType = Union[int, tuple[int, int], tuple[int, int, int, int]]

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
    footer: str = ""
    header_style: Optional[Union[Style, str]] = None
    footer_style: Optional[Union[Style, str]] = None
    style: Optional[Union[Style, str]] = None
    justify: Literal["default", "left", "center", "right", "full"] = "left"
    vertical: Literal["top", "middle", "bottom"] = "top"
    overflow: Literal["fold", "crop", "ellipsis", "ignore"] = "ellipsis"
    width: Optional[int] = None
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    ratio: Optional[int] = None
    no_wrap: bool = False

    def render_cell(self, entry: "HelpEntry") -> RenderableType:
        """Render the cell content based on the renderer type.

        If renderer is a string, retrieves that attribute from the entry.
        If renderer is callable, calls it with the entry.
        """
        if isinstance(self.renderer, str):
            value = str(getattr(entry, self.renderer) or "")
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
    console : Console
        Rich console for width calculations.
    options : ConsoleOptions
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
    console : Console
        Rich console for width calculations.
    options : ConsoleOptions
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
    StyleType = Union[Style, str]
    PaddingType = Union[int, tuple[int, int], tuple[int, int, int, int]]

    # Intrinsic table styling/config
    title: Optional[str] = None
    caption: Optional[str] = None
    style: Optional[StyleType] = None
    border_style: Optional[StyleType] = None
    header_style: Optional[StyleType] = None
    footer_style: Optional[StyleType] = None
    box: Optional[Box] = None
    show_header: bool = False
    show_footer: bool = False
    show_lines: bool = False
    expand: bool = False
    pad_edge: bool = False
    padding: PaddingType = (0, 2, 0, 0)
    collapse_padding: bool = False

    def build(
        self,
        columns: tuple[ColumnSpec, ...],
        entries: Iterable["HelpEntry"],
        **overrides,
    ) -> Table:
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
    PaddingType = Union[int, tuple[int, int], tuple[int, int, int, int]]
    StyleType = Union[Style, str]

    # Content-independent panel chrome
    title: Optional[RenderableType] = None
    subtitle: Optional[RenderableType] = None
    title_align: Literal["left", "center", "right"] = "left"
    subtitle_align: Literal["left", "center", "right"] = "center"
    style: Optional[StyleType] = "none"
    border_style: Optional[StyleType] = "none"
    box: Box = ROUNDED
    padding: PaddingType = (0, 1)
    expand: bool = True
    width: Optional[int] = None
    height: Optional[int] = None
    safe_box: Optional[bool] = None

    def build(self, renderable: RenderableType, **overrides) -> Panel:
        """Create a Panel around `renderable`. Use kwargs to override spec per render."""
        opts = {
            "title_align": self.title_align,
            "subtitle_align": self.subtitle_align,
            "style": self.style,
            "border_style": self.border_style,
            "box": self.box,
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
        return Panel(renderable, **opts)
