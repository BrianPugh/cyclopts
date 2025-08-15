from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal, Optional, Union

from attrs import define, evolve, field

if TYPE_CHECKING:
    from cyclopts.help import AbstractTableEntry
    from cyclopts.help.protocols import Converter, Formatter


@define(frozen=True)
class ColumnSpec:
    from rich.console import RenderableType
    from rich.style import Style
    from rich.table import Table

    PaddingType = Union[int, tuple[int, int], tuple[int, int, int, int]]

    key: str

    formatter: Optional["Formatter"] = None
    converters: Optional[Union["Converter", list["Converter"]]] = None

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

    def render_cell(self, entry: "AbstractTableEntry") -> RenderableType:
        """Render the cell."""
        raw = entry.get(self.key, None)
        out = raw(entry) if callable(raw) else raw
        entry.try_put(self.key, out)

        if self.converters:  # and out is not None:
            converters = [self.converters] if not isinstance(self.converters, list) else self.converters

            for converter in converters:
                out = converter(out, entry)
                entry.try_put(self.key, out)

        # Apply the formatter - takes the current string
        if self.formatter:
            out = self.formatter(out, entry, self)
            entry.try_put(self.key, out)

        return "" if out is None else out

    def with_(self, **kw):
        return evolve(self, **kw)


@define(frozen=True)
class TableSpec:
    from rich.box import Box
    from rich.style import Style
    from rich.table import Table

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

    columns: list[ColumnSpec] = field(factory=list)

    def build(self, **overrides) -> Table:
        from rich.table import Table

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
        for col in self.columns:
            col.add_to(table)
        return table

    def add_entries(self, table: Table, entries: Iterable["AbstractTableEntry"]) -> None:
        """Insert the entries into the table."""
        for e in entries:
            cells = [col.render_cell(e) for col in self.columns]
            table.add_row(*cells)

    # To help with padding...
    def with_padding(self, padding: PaddingType) -> "TableSpec":
        """Immutable helper to tweak padding."""
        return evolve(self, padding=padding)

    def with_(self, **kw):
        return evolve(self, **kw)


@define(frozen=True)
class PanelSpec:
    from rich.box import ROUNDED, Box
    from rich.console import RenderableType
    from rich.panel import Panel
    from rich.style import Style

    PaddingType = Union[int, tuple[int, int], tuple[int, int, int, int]]
    StyleType = Union[Style, str]

    # Content-independent panel chrome
    title: RenderableType = ""
    subtitle: RenderableType = ""
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
        from rich.panel import Panel

        opts = {
            "title": self.title,
            "subtitle": self.subtitle,
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
        opts.update(overrides)
        return Panel(renderable, **opts)

    # Handy immutable helpers
    def with_box(self, box: Box) -> "PanelSpec":
        return evolve(self, box=box)

    def with_padding(self, padding: PaddingType) -> "PanelSpec":
        return evolve(self, padding=padding)

    def with_border_style(self, style: StyleType) -> "PanelSpec":
        return evolve(self, border_style=style)
