import math
import textwrap
from collections.abc import Iterable
from functools import partial
from typing import TYPE_CHECKING, Literal, Optional, Union

from attrs import evolve
from rich.box import ROUNDED, Box
from rich.console import RenderableType
from rich.panel import Panel
from rich.style import Style
from rich.table import Table

from cyclopts.utils import frozen

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions

    from cyclopts.help import TableEntry
    from cyclopts.help.protocols import ColumnSpecBuilder, Renderer


# Renderer functions for different column types
def asterisk_renderer(entry: "TableEntry") -> "RenderableType":
    """Render an asterisk for required parameters.

    Parameters
    ----------
    entry : TableEntry
        The table entry to render.

    Returns
    -------
    RenderableType
        "*" if required, empty string otherwise.
    """
    return "*" if entry.required else ""


def name_renderer(entry: "TableEntry") -> "RenderableType":
    """Render the names column by combining names and shorts.

    Parameters
    ----------
    entry : TableEntry
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


def wrapped_name_renderer(entry: "TableEntry", max_width: Optional[int] = None) -> "RenderableType":
    """Render names with text wrapping.

    Parameters
    ----------
    entry : TableEntry
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


def description_renderer(entry: "TableEntry") -> "RenderableType":
    """Render the description column.

    Parameters
    ----------
    entry : TableEntry
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

    key: str
    """Key identifying this column's purpose (e.g., 'names', 'description', 'asterisk')."""

    renderer: Optional["Renderer"] = None
    """Function that renders this column's cell from a TableEntry."""

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

    def add_to(self, table: Table) -> None:
        table.add_column(
            self.header,
            footer=self.footer,
            header_style=self.header_style,
            footer_style=self.footer_style,
            style=self.style,
            justify=self.justify,
            vertical=self.vertical,
            overflow=self.overflow,
            width=self.width,
            min_width=self.min_width,
            max_width=self.max_width,
            ratio=self.ratio,
            no_wrap=self.no_wrap,
        )

    def render_cell(self, entry: "TableEntry") -> RenderableType:
        """Render the cell using the renderer function.

        If no renderer is provided, attempts to get the value directly from the entry
        using the key attribute.
        """
        value = self.renderer(entry) if self.renderer else entry.get(self.key, None)

        if callable(value):  # Handle lazy data (callables)
            value = value(entry)

        return "" if value is None else value

    def with_(self, **kw):
        return evolve(self, **kw)


# For Parameters:
AsteriskColumn = ColumnSpec(
    key="asterisk", header="", justify="left", width=1, style="red bold", renderer=asterisk_renderer
)

NameColumn = ColumnSpec(
    key="names",
    header="",
    justify="left",
    style="cyan",
    renderer=name_renderer,
)

DescriptionColumn = ColumnSpec(
    key="description", header="", justify="left", overflow="fold", renderer=description_renderer
)


def _command_column_spec_builder(
    console: "Console", options: "ConsoleOptions", entries: list["TableEntry"]
) -> tuple[ColumnSpec, ...]:
    """Builder for default command column_specs."""
    max_width = math.ceil(console.width * 0.35)
    command_column = ColumnSpec(
        key="names",
        header="",
        justify="left",
        style="cyan",
        renderer=partial(wrapped_name_renderer, max_width=max_width),
        max_width=max_width,
    )

    return (
        command_column,
        DescriptionColumn,
    )


def _parameter_column_spec_builder(
    console: "Console", options: "ConsoleOptions", entries: list["TableEntry"]
) -> tuple[ColumnSpec, ...]:
    """Builder for default parameter column_specs."""
    max_width = math.ceil(console.width * 0.35)
    name_column = ColumnSpec(
        key="names",
        header="",
        justify="left",
        style="cyan",
        renderer=partial(wrapped_name_renderer, max_width=max_width),
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

    columns: Union[tuple[ColumnSpec, ...], "ColumnSpecBuilder"]

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

    def realize_columns(self, console, options, entries) -> "TableSpec":
        """Realize ColumnSpecBuilders."""
        return self.with_(columns=self.columns(console, options, entries) if callable(self.columns) else self.columns)

    def build(self, **overrides) -> Table:
        """Construct a rich.Table, allowing per-render overrides, e.g. build(padding=0)."""
        opts = {
            "title": self.title,
            "caption": self.caption,
            "style": self.style,
            "border_style": self.border_style,
            "header_style": self.header_style,
            "footer_style": self.footer_style,
            "box": self.box,
            "show_header": self.show_header,
            "show_footer": self.show_footer,
            "show_lines": self.show_lines,
            "expand": self.expand,
            "pad_edge": self.pad_edge,
            "padding": self.padding,
            "collapse_padding": self.collapse_padding,
        }
        opts.update(overrides)
        table = Table(**opts)

        if callable(self.columns):
            raise TypeError("Columns must be realized before building table")

        for col in self.columns:
            col.add_to(table)
        return table

    def add_entries(self, table: Table, entries: Iterable["TableEntry"]) -> None:
        """Insert the entries into the table."""
        if callable(self.columns):
            raise TypeError("Columns must be realized before building table")

        for e in entries:
            cells = [col.render_cell(e) for col in self.columns]
            table.add_row(*cells)

    def with_(self, **kw):
        return evolve(self, **kw)

    @classmethod
    def for_commands(cls, **kwargs) -> "TableSpec":
        """Create a TableSpec configured for command display.

        Parameters
        ----------
        **kwargs
            Additional keyword arguments to override defaults.
        """
        defaults: dict = {
            "columns": _command_column_spec_builder,
        }
        defaults.update(kwargs)
        return cls(**defaults)

    @classmethod
    def for_parameters(cls, **kwargs) -> "TableSpec":
        """Create a TableSpec configured for parameter display.

        Parameters
        ----------
        **kwargs
            Additional keyword arguments to override defaults.
        """
        defaults: dict = {
            "columns": _parameter_column_spec_builder,
        }
        defaults.update(kwargs)
        return cls(**defaults)


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

    # Handy immutable helpers
    def with_box(self, box: Box) -> "PanelSpec":
        return evolve(self, box=box)

    def with_padding(self, padding: PaddingType) -> "PanelSpec":
        return evolve(self, padding=padding)

    def with_border_style(self, style: StyleType) -> "PanelSpec":
        return evolve(self, border_style=style)
