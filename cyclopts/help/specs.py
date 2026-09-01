import math
import textwrap
from collections.abc import Iterable, Mapping
from operator import attrgetter
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal, Optional, Self, Union

from attrs import evolve

from cyclopts.utils import frozen

if TYPE_CHECKING:
    from rich.box import Box
    from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
    from rich.padding import PaddingDimensions
    from rich.panel import Panel
    from rich.style import StyleType
    from rich.table import Table
    from rich.theme import Theme

    from cyclopts.help import HelpEntry
    from cyclopts.help.protocols import Renderer


# Every color Cyclopts renders in help output is referred to by one of these
# named styles. Define any of these keys in your Console's ``rich.theme.Theme``
# to restyle that element, e.g. ``Theme({"cyclopts.required": "bold yellow"})``;
# keys you don't define fall back to the paired default below.
DEFAULT_STYLES: Mapping[str, str] = MappingProxyType(
    {
        "cyclopts.name": "cyan",  # parameter / command name column
        "cyclopts.required_marker": "red bold",  # required "*" marker
        "cyclopts.choices": "gray58",  # [choices: ...]
        "cyclopts.env_var": "gray58",  # [env var: ...]
        "cyclopts.default": "gray58",  # [default: ...]
        "cyclopts.required": "red",  # [required]
        "cyclopts.border": "none",  # help panel border
        "cyclopts.usage": "bold",  # "Usage:" line
    }
)


def default_styles_theme(console: "Console") -> "Theme":
    """Build a theme supplying the ``cyclopts.*`` defaults ``console`` lacks.

    Only names the console doesn't already resolve are included, so a user's own
    theme keys take precedence (Rich's :meth:`~rich.console.Console.use_theme`
    layers on top, so a full default theme would otherwise clobber overrides).
    """
    from rich.errors import MissingStyle
    from rich.theme import Theme

    styles: dict[str, str] = {}
    for name, fallback in DEFAULT_STYLES.items():
        try:
            console.get_style(name)
        except MissingStyle:
            styles[name] = fallback
    return Theme(styles)


class DefaultStyled:
    """Wrap a renderable so it renders under the ``cyclopts.*`` style defaults.

    Help output refers to colors by bare ``cyclopts.*`` style names; those names
    only resolve while :func:`default_styles_theme` is active. Wrapping the
    renderable applies that theme at render time, so the styles resolve on any
    console and via any print path (a user's own theme keys still win) without
    callers having to set up the theme themselves.

    A per-group ``theme`` (from :attr:`Group.theme`) is layered on top so its
    ``cyclopts.*`` keys override the defaults for just that group's panel.
    """

    def __init__(self, renderable: "RenderableType", theme: "dict[str, str] | Theme | None" = None):
        self.renderable = renderable
        self.theme = theme

    def __rich_console__(self, console: "Console", options: "ConsoleOptions") -> "RenderResult":
        from contextlib import nullcontext

        from rich.theme import Theme

        theme = self.theme
        if theme is not None and not isinstance(theme, Theme):
            # A mapping is wrapped with inherit=False so it carries only its own
            # keys, overriding just those when layered over the defaults below.
            theme = Theme(theme, inherit=False)

        with console.use_theme(default_styles_theme(console)):
            # The group theme is pushed on top so its keys win for this panel.
            with console.use_theme(theme) if theme is not None else nullcontext():
                yield from console.render(self.renderable, options)


class NameRenderer:
    """Renderer for parameter/command names with optional text wrapping.

    Parameters
    ----------
    max_width : int | None
        Maximum width for wrapping. If None, no wrapping is applied.
    """

    def __init__(self, max_width: int | None = None, show_metavar: bool = True):
        """Initialize the renderer with formatting options.

        Parameters
        ----------
        max_width : int | None
            Maximum width for wrapping. If None, no wrapping is applied.
        show_metavar : bool
            If True (default), append the type-derived value placeholder to
            keyword-only parameters (e.g. ``--config PATH``). Set to False to
            render option names alone.
        """
        self.max_width = max_width
        self.show_metavar = show_metavar

    def __call__(self, entry: "HelpEntry") -> "RenderableType":
        """Render the names column with optional text wrapping.

        Parameters
        ----------
        entry : HelpEntry
            The table entry to render.

        Returns
        -------
        ~rich.console.RenderableType
            Combined names and shorts, optionally wrapped.
            Order: positional_label (positional only), positive_names, positive_shorts,
            negative_names, negative_shorts
        """
        labels = entry.display_labels
        if self.show_metavar and not entry.positional and entry.metavar and not entry.choices:
            # Keyword-only value-taking parameters have no positional label to stand in
            # for their value, so surface the type-derived shape (``--config PATH``).
            # Positional-capable rows already show their name-derived identifier, and
            # rows with ``[choices]`` convey the shape better than a raw ``LITERAL[...]``.
            # The metavar goes right after the value-taking names; negatives such as
            # ``--empty-custom`` take no value and must not appear to.
            labels = (
                *entry.positive_names,
                *entry.positive_shorts,
                entry.metavar,
                *entry.negative_names,
                *entry.negative_shorts,
            )
        text = " ".join(labels)

        if self.max_width is None:
            return text

        wrapped = textwrap.wrap(
            text,
            self.max_width,
            subsequent_indent="  ",
            break_on_hyphens=False,
            tabsize=4,
        )

        return "\n".join(wrapped)


class CommandNameRenderer:
    """Renderer for command names with aliases in parentheses.

    Displays commands in argparse-style format: ``primary (alias1, alias2)``.

    Parameters
    ----------
    max_width : int | None
        Maximum width for wrapping. If None, no wrapping is applied.
    """

    def __init__(self, max_width: int | None = None):
        """Initialize the renderer with formatting options.

        Parameters
        ----------
        max_width : int | None
            Maximum width for wrapping. If None, no wrapping is applied.
        """
        self.max_width = max_width

    def __call__(self, entry: "HelpEntry") -> "RenderableType":
        """Render command name with aliases in parentheses.

        Parameters
        ----------
        entry : HelpEntry
            The table entry to render.

        Returns
        -------
        ~rich.console.RenderableType
            Primary command name with aliases in parentheses.
        """
        primary = entry.all_options[0] if entry.all_options else ""
        aliases = list(entry.all_options[1:])

        if aliases:
            text = f"{primary} ({', '.join(aliases)})"
        else:
            text = primary

        if self.max_width is None:
            return text

        wrapped = textwrap.wrap(
            text,
            self.max_width,
            subsequent_indent="  ",
            break_on_hyphens=False,
            tabsize=4,
        )

        return "\n".join(wrapped)


class DescriptionRenderer:
    """Renderer for descriptions with configurable metadata formatting.

    Parameters
    ----------
    newline_metadata : bool
        If True, display metadata (choices, env vars, defaults) on separate lines.
        If False (default), display metadata inline with the description.
    """

    def __init__(self, newline_metadata: bool = False):
        """Initialize the renderer with formatting options.

        Parameters
        ----------
        newline_metadata : bool
            If True, display metadata on separate lines instead of inline.
        """
        self.newline_metadata = newline_metadata

    def __call__(self, entry: "HelpEntry") -> "RenderableType":
        """Render parameter description with metadata annotations.

        Enriches the base description with choices, environment variables,
        default values, and required status.

        Parameters
        ----------
        entry : HelpEntry
            The table entry to render.

        Returns
        -------
        ~rich.console.RenderableType
            Description with appended metadata.
        """
        from rich.text import Text

        from cyclopts.help.inline_text import InlineText

        description = entry.description
        if description is None:
            description = InlineText(Text())
        elif not isinstance(description, InlineText):
            # Convert to InlineText if it isn't already
            if hasattr(entry.description, "__rich_console__"):
                # It's already a Rich renderable, wrap it
                description = InlineText(description)
            else:
                # Convert to Text first, then wrap in InlineText
                from rich.text import Text

                description = InlineText(Text(str(description)))

        # Collect metadata items
        metadata_items = []

        if entry.choices:
            choices_str = ", ".join(entry.choices)
            metadata_items.append(Text(rf"[choices: {choices_str}]", "cyclopts.choices"))

        if entry.env_var:
            env_vars_str = ", ".join(entry.env_var)
            metadata_items.append(Text(rf"[env var: {env_vars_str}]", "cyclopts.env_var"))

        if entry.default is not None:
            metadata_items.append(Text(rf"[default: {entry.default}]", "cyclopts.default"))

        if entry.required:
            metadata_items.append(Text(r"[required]", "cyclopts.required"))

        # Apply metadata based on formatting mode
        if self.newline_metadata and metadata_items:
            # Add metadata on separate lines with indentation
            from rich.console import Group as RichGroup
            from rich.text import Text

            # Create a list of renderables to group
            renderables = []

            # Add the original description first
            if description.primary_renderable:
                renderables.append(description.primary_renderable)

            # Add each metadata item without indentation
            for item in metadata_items:
                renderables.append(item)

            # Return a Rich Group that stacks these vertically
            return RichGroup(*renderables) if renderables else Text()
        else:
            # Original inline behavior
            for item in metadata_items:
                description.append(item)

            return description


class AsteriskRenderer:
    """Renderer for required parameter asterisk indicator.

    A simple renderer that displays an asterisk (*) for required parameters.
    """

    def __call__(self, entry: "HelpEntry") -> "RenderableType":
        """Render an asterisk for required parameters.

        Parameters
        ----------
        entry : HelpEntry
            The table entry to render.

        Returns
        -------
        ~rich.console.RenderableType
            An asterisk if the entry is required, empty string otherwise.
        """
        return "*" if entry.required else ""


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
      'description', 'required', 'type'). The string is displayed as-is.
    - A callable: A function matching the :class:`~cyclopts.help.protocols.Renderer` protocol.
      The function receives a :class:`~cyclopts.help.HelpEntry` and should return a
      :class:`~rich.console.RenderableType` (str, :class:`~rich.text.Text`, or other Rich renderable).

    Examples::

        # String renderer - get attribute directly
        ColumnSpec(renderer="description")

        # Callable renderer - custom formatting.
        # ``display_labels`` includes the ``positional_label`` for positional parameters;
        # use ``all_options`` for option names only (see HelpEntry).
        def format_names(entry: HelpEntry) -> str:
            return ", ".join(entry.display_labels)
        ColumnSpec(renderer=format_names)
    """

    header: str = ""
    """Column header text displayed at the top of the column.

    Example::

        header="Options" renders:
        ┌─────────┬─────────────┐
        │ Options │ Description │
        ├─────────┼─────────────┤
        │ --help  │ Show help   │
        └─────────┴─────────────┘
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
    """Style applied to the column header text.

    Corresponds to the ``header_style`` parameter of :meth:`rich.table.Table.add_column`.
    """

    footer_style: Optional["StyleType"] = None
    """Style applied to the column footer text.

    Corresponds to the ``footer_style`` parameter of :meth:`rich.table.Table.add_column`.
    """

    style: Optional["StyleType"] = None
    """Default style applied to all cells in this column.

    Corresponds to the ``style`` parameter of :meth:`rich.table.Table.add_column`.
    """

    justify: Literal["default", "left", "center", "right", "full"] = "left"
    """Text justification within the column.

    Corresponds to the ``justify`` parameter of :meth:`rich.table.Table.add_column`.
    """

    vertical: Literal["top", "middle", "bottom"] = "top"
    """Vertical alignment of text within cells.

    Corresponds to the ``vertical`` parameter of :meth:`rich.table.Table.add_column`.
    """

    overflow: Literal["fold", "crop", "ellipsis", "ignore"] = "ellipsis"
    """How to handle text that exceeds column width.

    Corresponds to the ``overflow`` parameter of :meth:`rich.table.Table.add_column`.
    """

    width: int | None = None
    """Fixed width for the column in characters.

    Corresponds to the ``width`` parameter of :meth:`rich.table.Table.add_column`.
    """

    min_width: int | None = None
    """Minimum width for the column in characters.

    Corresponds to the ``min_width`` parameter of :meth:`rich.table.Table.add_column`.
    """

    max_width: int | None = None
    """Maximum width for the column in characters.

    Corresponds to the ``max_width`` parameter of :meth:`rich.table.Table.add_column`.
    """

    ratio: int | None = None
    """Relative width ratio compared to other columns.

    Corresponds to the ``ratio`` parameter of :meth:`rich.table.Table.add_column`.
    """

    no_wrap: bool = False
    """Prevent text wrapping in the column.

    Corresponds to the ``no_wrap`` parameter of :meth:`rich.table.Table.add_column`.
    """

    highlight: bool | None = None
    """Enable automatic highlighting of text in the column.

    Corresponds to the ``highlight`` parameter of :meth:`rich.table.Table.add_column`.
    """

    def _render_cell(self, entry: "HelpEntry") -> "RenderableType":
        """Render the cell content based on the renderer type.

        If renderer is a string, retrieves that attribute from the entry.
        If renderer is callable, calls it with the entry.
        """
        if isinstance(self.renderer, str):
            value = attrgetter(self.renderer)(entry)
        elif callable(self.renderer):
            value = self.renderer(entry)
        else:
            value = None
        return "" if value is None else value

    def copy(self, **kwargs: Any) -> Self:
        return evolve(self, **kwargs)


# For Parameters:
AsteriskColumn = ColumnSpec(
    renderer=AsteriskRenderer(),
    header="",
    justify="left",
    width=1,
    style="cyclopts.required_marker",
)

NameColumn = ColumnSpec(
    renderer=NameRenderer(),
    header="Option",
    justify="left",
    style="cyclopts.name",
)

DescriptionColumn = ColumnSpec(renderer=DescriptionRenderer(), header="Description", justify="left", overflow="fold")


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
        renderer=CommandNameRenderer(max_width=max_width),
        header="Command",
        justify="left",
        style="cyclopts.name",
        max_width=max_width,
    )

    return (
        command_column,
        DescriptionColumn,
    )


def get_default_parameter_columns(
    console: "Console", options: "ConsoleOptions", entries: list["HelpEntry"], show_metavar: bool = True
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
        renderer=NameRenderer(max_width=max_width, show_metavar=show_metavar),
        header="Option",
        justify="left",
        style="cyclopts.name",
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
    title: str | None = None
    """Title text displayed above the table.

    Corresponds to the ``title`` parameter of :class:`~rich.table.Table`.
    """

    caption: str | None = None
    """Caption text displayed below the table.

    Corresponds to the ``caption`` parameter of :class:`~rich.table.Table`.
    """

    style: Optional["StyleType"] = None
    """Default style applied to the entire table.

    Corresponds to the ``style`` parameter of :class:`~rich.table.Table`.
    """

    border_style: Optional["StyleType"] = None
    """Style applied to table borders.

    Corresponds to the ``border_style`` parameter of :class:`~rich.table.Table`.
    """

    header_style: Optional["StyleType"] = None
    """Default style for all table headers (can be overridden per column).

    Corresponds to the ``header_style`` parameter of :class:`~rich.table.Table`.
    """

    footer_style: Optional["StyleType"] = None
    """Default style for all table footers (can be overridden per column).

    Corresponds to the ``footer_style`` parameter of :class:`~rich.table.Table`.
    """

    box: Optional["Box"] = None
    """Box drawing style for the table borders.

    Corresponds to the ``box`` parameter of :class:`~rich.table.Table`. See :mod:`rich.box` for available styles.
    """

    show_header: bool = False
    """Whether to display column headers.

    Corresponds to the ``show_header`` parameter of :class:`~rich.table.Table`.
    """

    show_footer: bool = False
    """Whether to display column footers.

    Corresponds to the ``show_footer`` parameter of :class:`~rich.table.Table`.
    """

    show_lines: bool = False
    """Whether to show horizontal lines between rows.

    Corresponds to the ``show_lines`` parameter of :class:`~rich.table.Table`.
    """

    show_edge: bool = True
    """Whether to draw a box around the outside of the table.

    Corresponds to the ``show_edge`` parameter of :class:`~rich.table.Table`.
    """

    expand: bool = False
    """Whether the table should expand to fill available width.

    Corresponds to the ``expand`` parameter of :class:`~rich.table.Table`.
    """

    pad_edge: bool = False
    """Whether to add padding to the table edges.

    Corresponds to the ``pad_edge`` parameter of :class:`~rich.table.Table`.
    """

    padding: "PaddingDimensions" = (0, 2, 0, 0)
    """Padding around cell content (top, right, bottom, left).

    Corresponds to the ``padding`` parameter of :class:`~rich.table.Table`.
    """

    collapse_padding: bool = False
    """Whether to collapse padding when adjacent cells are empty.

    Corresponds to the ``collapse_padding`` parameter of :class:`~rich.table.Table`.
    """

    width: int | None = None
    """Fixed width for the table in characters.

    Corresponds to the ``width`` parameter of :class:`~rich.table.Table`.
    """

    min_width: int | None = None
    """Minimum width for the table in characters.

    Corresponds to the ``min_width`` parameter of :class:`~rich.table.Table`.
    """

    safe_box: bool | None = None
    """Whether to use ASCII-safe box characters for compatibility.

    Corresponds to the ``safe_box`` parameter of :class:`~rich.table.Table`.
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
            "show_edge": self.show_edge,
            "expand": self.expand,
            "pad_edge": self.pad_edge,
            "padding": self.padding,
            "collapse_padding": self.collapse_padding,
            "width": self.width,
            "min_width": self.min_width,
            "safe_box": self.safe_box,
        }
        opts.update(overrides)

        from rich.table import Table

        table = Table(**opts)

        # Add columns
        for column in columns:
            col_opts = {
                "header": column.header,
                "footer": column.footer,
                "header_style": column.header_style,
                "footer_style": column.footer_style,
                "style": column.style,
                "justify": column.justify,
                "vertical": column.vertical,
                "overflow": column.overflow,
                "width": column.width,
                "min_width": column.min_width,
                "max_width": column.max_width,
                "ratio": column.ratio,
                "no_wrap": column.no_wrap,
            }
            if column.highlight is not None:
                col_opts["highlight"] = column.highlight
            table.add_column(**col_opts)

        # Add entries
        for e in entries:
            cells = [col._render_cell(e) for col in columns]
            table.add_row(*cells)

        return table

    def copy(self, **kwargs: Any) -> Self:
        return evolve(self, **kwargs)


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

    Corresponds to the ``title`` parameter of :class:`~rich.panel.Panel`.
    """

    subtitle: Optional["RenderableType"] = None
    """Subtitle text displayed at the bottom of the panel.

    Corresponds to the ``subtitle`` parameter of :class:`~rich.panel.Panel`.
    """

    title_align: Literal["left", "center", "right"] = "left"
    """Alignment of the title text within the panel.

    Corresponds to the ``title_align`` parameter of :class:`~rich.panel.Panel`.
    """

    subtitle_align: Literal["left", "center", "right"] = "center"
    """Alignment of the subtitle text within the panel.

    Corresponds to the ``subtitle_align`` parameter of :class:`~rich.panel.Panel`.
    """

    style: Optional["StyleType"] = "none"
    """Style applied to the panel background.

    Corresponds to the ``style`` parameter of :class:`~rich.panel.Panel`.
    """

    border_style: Optional["StyleType"] = "cyclopts.border"
    """Style applied to the panel border.

    Corresponds to the ``border_style`` parameter of :class:`~rich.panel.Panel`.
    Defaults to the ``cyclopts.border`` named style (``none``), which can be
    remapped via a :class:`~rich.theme.Theme` on the :class:`~cyclopts.App`'s console.
    """

    box: Optional["Box"] = None  # Will use ROUNDED as default when building
    """Box drawing style for the panel border.

    Corresponds to the ``box`` parameter of :class:`~rich.panel.Panel`. See :mod:`rich.box` for available styles.
    Defaults to ``rich.box.ROUNDED``.
    """

    padding: "PaddingDimensions" = (0, 1)
    """Padding inside the panel (top/bottom, left/right) or (top, right, bottom, left).

    Corresponds to the ``padding`` parameter of :class:`~rich.panel.Panel`.
    """

    expand: bool = True
    """Whether the panel should expand to fill available width.

    Corresponds to the ``expand`` parameter of :class:`~rich.panel.Panel`.
    """

    width: int | None = None
    """Fixed width for the panel in characters.

    Corresponds to the ``width`` parameter of :class:`~rich.panel.Panel`.
    """

    height: int | None = None
    """Fixed height for the panel in lines.

    Corresponds to the ``height`` parameter of :class:`~rich.panel.Panel`.
    """

    safe_box: bool | None = None
    """Whether to use ASCII-safe box characters for compatibility.

    Corresponds to the ``safe_box`` parameter of :class:`~rich.panel.Panel`.
    """

    highlight: bool = False
    """Enable automatic highlighting of panel contents.

    Corresponds to the ``highlight`` parameter of :class:`~rich.panel.Panel`.
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
            "highlight": self.highlight,
        }
        if self.title is not None:
            opts["title"] = self.title
        if self.subtitle is not None:
            opts["subtitle"] = self.subtitle

        opts.update(overrides)

        from rich.panel import Panel

        return Panel(renderable, **opts)

    def copy(self, **kwargs: Any) -> Self:
        return evolve(self, **kwargs)
