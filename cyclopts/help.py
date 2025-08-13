"""
Splitting of gathering
and drawing!
"""

import inspect
import sys
from collections.abc import Iterable
from enum import Enum
from functools import lru_cache, partial
from inspect import isclass
from math import ceil
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Literal,
    Optional,
    Sequence,
    get_args,
    get_origin,
    Protocol,
    runtime_checkable
)

from attrs import define, field, Factory, evolve

from cyclopts._convert import ITERABLE_TYPES
from cyclopts.annotations import is_union, resolve_annotated
from cyclopts.field_info import signature_parameters
from cyclopts.group import Group
from cyclopts.utils import SortHelper, frozen, resolve_callables




if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
    from rich.panel import Panel
    from rich.text import Text

    from cyclopts.argument import ArgumentCollection
    from cyclopts.core import App

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import TypeAliasType
else:  # pragma: no cover
    TypeAliasType = None



@lru_cache(maxsize=16)
def docstring_parse(doc: str, format: str):
    """Addon to :func:`docstring_parser.parse` that supports multi-line `short_description`."""
    import docstring_parser

    cleaned_doc = inspect.cleandoc(doc)
    short_description_and_maybe_remainder = cleaned_doc.split("\n\n", 1)

    # Place multi-line summary into a single line.
    # This kind of goes against PEP-0257, but any reasonable CLI command will
    # have either no description, or it will have both a short and long description.
    short = short_description_and_maybe_remainder[0].replace("\n", " ")
    if len(short_description_and_maybe_remainder) == 1:
        cleaned_doc = short
    else:
        cleaned_doc = short + "\n\n" + short_description_and_maybe_remainder[1]

    res = docstring_parser.parse(cleaned_doc)

    # Ensure a short description exists if there's a long description
    assert not res.long_description or res.short_description

    return res






def _text_factory():
    from rich.text import Text

    return Text()


class InlineText:
    def __init__(self, primary_renderable: "RenderableType", *, force_empty_end=False):
        self.primary_renderable = primary_renderable
        self.texts = []
        self.force_empty_end = force_empty_end

    @classmethod
    def from_format(cls, content: Optional[str], format: str, *, force_empty_end=False):
        if content is None:
            from rich.text import Text

            primary_renderable = Text(end="")
        elif format == "plaintext":
            from rich.text import Text

            primary_renderable = Text(content.rstrip())
        elif format in ("markdown", "md"):
            from rich.markdown import Markdown

            primary_renderable = Markdown(content)
        elif format in ("restructuredtext", "rst"):
            from rich_rst import RestructuredText

            primary_renderable = RestructuredText(content)
        elif format == "rich":
            from rich.text import Text

            primary_renderable = Text.from_markup(content)
        else:
            raise ValueError(f'Unknown help_format "{format}"')

        return cls(primary_renderable, force_empty_end=force_empty_end)

    def append(self, text: "Text"):
        self.texts.append(text)

    def __rich_console__(self, console, options):
        from rich.segment import Segment
        from rich.text import Text

        if not self.primary_renderable and not self.texts:
            return

        # Group segments by line
        lines_of_segments, current_line = [], []
        for segment in console.render(self.primary_renderable, options):
            if segment.text == "\n":
                lines_of_segments.append(current_line + [segment])
                current_line = []
            else:
                current_line.append(segment)

        if current_line:
            lines_of_segments.append(current_line)

        # If no content, just yield the additional texts
        if not lines_of_segments:
            if self.texts:
                combined_text = Text.assemble(*self.texts)
                yield from console.render(combined_text, options)
            return

        # Yield all but the last line unchanged
        for line in lines_of_segments[:-1]:
            for segment in line:
                yield segment

        # For the last line, concatenate all of our additional texts;
        # We have to re-render to properly handle textwrapping.
        if lines_of_segments:
            last_line = lines_of_segments[-1]

            # Check for newline at end
            has_newline = last_line and last_line[-1].text == "\n"
            newline_segment = last_line.pop() if has_newline else None

            # rstrip the last segment
            if last_line:
                last_segment = last_line[-1]
                last_segment = Segment(
                    last_segment.text.rstrip(),
                    style=last_segment.style,
                    control=last_segment.control,
                )
                last_line[-1] = last_segment

            # Convert last line segments to text and combine with additional text
            last_line_text = Text("", end="")
            for segment in last_line:
                if segment.text:
                    last_line_text.append(segment.text, segment.style)

            separator = Text(" ")
            for text in self.texts:
                if last_line_text:
                    last_line_text += separator
                last_line_text += text

            # Re-render with proper wrapping
            wrapped_segments = list(console.render(last_line_text, options))

            if self.force_empty_end:
                last_segment = wrapped_segments[-1]
                if last_segment and not last_segment.text.endswith("\n"):
                    wrapped_segments.append(Segment("\n"))

            # Add back newline if it was present
            if newline_segment:
                wrapped_segments.append(newline_segment)

            yield from wrapped_segments





from typing import TypeAlias

ValueOrCallable: TypeAlias = "RenderableType" | Callable[["AbstractTableEntry"], "RenderableType"]
#ValueOrCallable: TypeAlias = str | Callable[["AbstractTableEntry"], str]

@define(slots=True)
class TableData:
    """Intentionally empty dataclass.

    Users can inherit from this and declore concrete fields and then pass
    the object to AbstractTableEntry
    """

    pass

#def _resolve(v: Optional[ValueOrCallable]) -> Optional[RenderableType]:
def _resolve(v: Optional[ValueOrCallable]) -> str | None:
    if v is None:
        return None
    return v() if callable(v) else v

@define(slots=True)
class AbstractTableEntry:
    """Adjust the Format on an entry level basis.

    Include a dictionary of data, that all evalaute to
    RenderableType. Mapping column names -> Data

    Then pull any of the request data at rendertime
    """

    from rich.console import RenderableType

    name: RenderableType | None = None
    short: RenderableType | None = None
    description: RenderableType | None = None
    required: bool = False
    sort_key: Any = None

    extras: TableData = field(factory=TableData, repr=False)


    def try_put(self, key: str, value: ValueOrCallable):
        """Put a attr to the dataclass.

        This is looser than put, and will not raise an Attribute Error if
        the member does not exist. This is useful when the list of entries
        do not have all the same members.
        """
        if hasattr(self, key):
            setattr(self, key, value)
        elif hasattr(self.extras, key):
            setattr(self.extras, key, value)
        return self

    def put(self, key: str, value: ValueOrCallable):
        """Put a attr to the dataclass.
        """
        if hasattr(self, key):
            setattr(self, key, value)
        elif hasattr(self.extras, key):
            setattr(self.extras, key, value)
        else:
            raise AttributeError(f"'{type(self.extras).__name__}' has no field {key}")
        return self

    def get(self, key: str, default: Any = None, resolve: bool = False) -> Any:
        if hasattr(self, key):
            val = getattr(self, key)
            return _resolve(val) if resolve else val
        if hasattr(self.extras, key):
            val = getattr(self.extras, key)
            return _resolve(val) if resolve else val
        return default

    def __getattr__(self, name: str)->ValueOrCallable:
        """Access extra values as if they were members.

        This makes members in the `extra` dataclass feel like
        members of the `AbstractTableEntry` instance. Thus, psuedo
        adding members is easy, and table generation is simplified.
        """
        extras = object.__getattribute__(self, "extras")
        try:
            return getattr(extras, name)
        except AttributeError:
            raise AttributeError
    def with_(self, **kw):
        return evolve(self, **kw)



@define(frozen=True)
class ColumnSpec:
    from rich.console import RenderableType
    from rich.table import Table
    from rich.style import Style

    PaddingType = int | tuple[int, int] | tuple[int, int, int, int]

    key: str

    formatter:  Callable[[RenderableType, AbstractTableEntry, "ColumnSpec"], RenderableType] | None = None
    converters: Callable[[AbstractTableEntry], RenderableType] | None | list[Callable[[AbstractTableEntry], RenderableType] | None] = None

    header: str = ""
    footer: str = ""
    header_style: Style | str | None = None
    footer_style: Style | str | None = None
    style: Style | str | None = None
    justify: str = "left"
    vertical: str = "top"
    overflow: str = "ellipsis"
    width: int | None = None
    min_width: int | None = None
    max_width: int | None = None
    ratio: int | None = None
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

    def render_cell(self, entry: AbstractTableEntry) -> RenderableType:
        """Render the cell.
        """
        raw = entry.get(self.key, None)

        print(f"RENDER COL KEY: {self.key}" )

        # If it's a callable, eval the callable 
        if callable(raw):
            out = raw(entry)
            entry.try_put(self.key, out)
        else:
            # If its a renderable type just keep that or None
            out = raw

        # Apply the converter  - takes the whole entry
        # The converter requires that the current out 
        # not be None. If it is, just return "" 
        if self.converters: #and out is not None:
            converters = [self.converters] if  not isinstance(self.converters,list) else self.converters

            for converter in converters:
                out = converter(out, entry)
                entry.try_put(self.key, out)
                #entry = entry.with_(self.key=out)
                #entry.put(self.key, out)

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

    from rich.table import Table
    from rich.style import Style

    StyleType = Style | str
    PaddingType = int | tuple[int, int] | tuple[int, int, int, int]

    # Intrinsic table styling/config
    title: str | None = None
    caption: str | None = None
    style: StyleType | None = None
    border_style: StyleType | None = None
    header_style: StyleType | None = None
    footer_style: StyleType | None = None
    box: Box | None = None
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

    def add_entries(self, table: Table, entries:Iterable[AbstractTableEntry]) -> None:
        """Insert the entries into the table."""
        print(f"Render cols: {[x.key for x in self.columns]}")
        for e in entries:
            cells = [col.render_cell(e) for col in self.columns]
            print(f"For entry: {e.name} adding row: {cells}")
            table.add_row(*cells)

    # To help with padding...
    def with_padding(self, padding: PaddingType) -> "TableSpec":
        """Immutable helper to tweak padding."""
        return evolve(self, padding=padding)


    def with_(self, **kw):
        return evolve(self, **kw)



@define(frozen=True)
class PanelSpec:
    from rich.box import Box, ROUNDED
    from rich.panel import Panel
    from rich.console import RenderableType

    from rich.style import Style

    PaddingType = int | tuple[int, int] | tuple[int, int, int, int]
    StyleType = Style | str


    # Content-independent panel chrome
    title: RenderableType  = ""
    subtitle: RenderableType  = ""
    title_align: Literal["left", "center", "right"] = "left"
    subtitle_align: Literal["left", "center", "right"] = "center"
    style: StyleType | None = "none"
    border_style: StyleType | None = "none"
    box: Box = ROUNDED
    padding: PaddingType = (0, 1)
    expand: bool = True
    width: int | None = None
    height: int | None = None
    safe_box: bool | None = None

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



# Define some default column specs
def wrap_formatter(inp: "RenderableType", entry: AbstractTableEntry, col_spec:ColumnSpec )->"RenderableType":

    import textwrap
    wrap = partial(
            textwrap.wrap,
            subsequent_indent="  ",
            break_on_hyphens=False,
            tabsize=4,
        )

    if col_spec.max_width:
        new =  "\n".join(wrap(inp, col_spec.max_width))
    else:
        new =  "\n".join(wrap(inp))
    return new

def asterisk_converter(out: "RenderableType", inp: AbstractTableEntry)->"RenderableType":
    if inp.required:
        return "*"
    return ""

def stretch_name_converter(out: "RenderableType", inp:AbstractTableEntry)->"RenderableType":
    """Split name into two parts based on --.

    Example
    -------
        '--foo--no-foo'  to '--foo --no-foo'.
    """
    out = " --".join(inp.name.split("--"))
    return out[1:] if out[0] == " " else out


def combine_long_short_converter(out: "RenderableType", inp:AbstractTableEntry)->"RenderableType":
    """Concatenate a name and its short version.

    Examples
    --------
        name = "--help"
        short = "-h"
        return: "--help -h"
    """
    return inp.name + " " + inp.short



# For Parameters:
AsteriskColumn = ColumnSpec(key="asterisk", header="", justify="left", width=1, style="red bold", converters=asterisk_converter)
NameColumn = ColumnSpec(key="name", header="", justify="left",  style="cyan", formatter=wrap_formatter, converters=[stretch_name_converter, combine_long_short_converter])
DescriptionColumn = ColumnSpec(key="description", header="", justify="left", overflow="fold")
# For Commands:
CommandColumn = ColumnSpec(key="name", header="", justify="left", style="cyan", formatter=wrap_formatter, converters=[stretch_name_converter, combine_long_short_converter] )


@define
class AbstractRichHelpPanel:
    """Adjust the Format for the help panel!."""

    import textwrap
    from rich.box import Box, ROUNDED
    from rich.console import Group as RichGroup
    from rich.console import NewLine, RenderableType
    from rich.panel import Panel
    from rich.table import Table, Column
    from rich.text import Text

    format: Literal["command", "parameter"]
    title: RenderableType
    description: RenderableType = field(factory=_text_factory)
    entries: list[AbstractTableEntry] = field(factory=list)

    column_specs: list[ColumnSpec] = field(
        default=Factory(
            lambda self: [CommandColumn, DescriptionColumn]
            if self.format == "command"
            else [NameColumn, DescriptionColumn]
        ,takes_self=True)
    )

    table_spec: TableSpec = field(
        default=Factory(lambda self: TableSpec(columns=self.column_specs), takes_self=True))

    panel_spec: PanelSpec = field(
        default=Factory(lambda self: PanelSpec(title=self.title), takes_self=True))

    def remove_duplicates(self):
        seen, out = set(), []
        for item in self.entries:
            hashable = (item.name,
                        item.short)
            if hashable not in seen:
                seen.add(hashable)
                out.append(item)
        self.entries = out

    def sort(self):
        """Sort entries in-place."""
        if not self.entries:
            return

        if self.format == "command":
            sorted_sort_helper = SortHelper.sort(
                [SortHelper(entry.sort_key, (entry.name.startswith("-"), entry.name), entry) for entry in self.entries]
            )
            self.entries = [x.value for x in sorted_sort_helper]
        else:
            raise NotImplementedError

    def __rich_console__(self, console: "Console", options: "ConsoleOptions") -> "RenderResult":
        if not self.entries:
            return _silent


        from rich.console import Group as RichGroup
        from rich.console import NewLine
        from rich.text import Text
        commands_width = ceil(console.width * 0.35)

        panel_description = self.description
        if isinstance(panel_description, Text):
            panel_description.end = ""

            if panel_description.plain:
                panel_description = RichGroup(panel_description, NewLine(2))

        #TODO: Do this at instaiation time so that if a user changes the 
        # columns (or doesnt want asterisk column not matter what) their 
        # changes are not overridding by this. 

        # 1. Adjust the format (need to keep default behavior...)
        if self.format == "command":
            commands_width = ceil(console.width * 0.35)
            for i in range(len(self.column_specs)):
                spec = self.column_specs[i]
                if spec.key == "name":
                    spec = spec.with_(max_width=commands_width)
                self.column_specs[i] = spec

        elif self.format == "parameter":

            # Add AsteriskColumn if any params are required
            if any(x.required for x in self.entries):
                col_specs = [AsteriskColumn]
                col_specs.extend(self.column_specs)
                self.column_specs = col_specs

            name_width = ceil(console.width * 0.35)
            short_width = ceil(console.width * 0.1)

            for i in range(len(self.column_specs)):
                spec = self.column_specs[i]
                if spec.key == "name":
                    spec = spec.with_(max_width=name_width)
                elif spec.key == "short":
                    spec = spec.with_(max_width=short_width)

                self.column_specs[i] = spec


        # 2.Build table and Add Etnries
        self.table_spec = self.table_spec.with_(columns = self.column_specs)

        table = self.table_spec.build()
        self.table_spec.add_entries(table, self.entries)

        # 3. Final make the panel
        panel = self.panel_spec.build(RichGroup(panel_description, table))

        yield panel


class SilentRich:
    """Dummy object that causes nothing to be printed."""

    def __rich_console__(self, console: "Console", options: "ConsoleOptions") -> "RenderResult":
        # This generator yields nothing, so ``rich`` will print nothing for this object.
        if False:
            yield


_silent = SilentRich()


def _is_short(s):
    return not s.startswith("--") and s.startswith("-")


def format_usage(
    app,
    command_chain: Iterable[str],
):
    from rich.text import Text

    usage = []
    usage.append("Usage:")
    usage.append(app.name[0])
    usage.extend(command_chain)

    for command in command_chain:
        app = app[command]

    if any(app[x].show for x in app._registered_commands):
        usage.append("COMMAND")

    if app.default_command:
        to_show = set()
        for field_info in signature_parameters(app.default_command).values():
            if field_info.kind in (
                field_info.POSITIONAL_ONLY,
                field_info.VAR_POSITIONAL,
                field_info.POSITIONAL_OR_KEYWORD,
            ):
                to_show.add("[ARGS]")
            if field_info.kind in (field_info.KEYWORD_ONLY, field_info.VAR_KEYWORD, field_info.POSITIONAL_OR_KEYWORD):
                to_show.add("[OPTIONS]")
        usage.extend(sorted(to_show))

    return Text(" ".join(usage) + "\n", style="bold")


def _smart_join(strings: Sequence[str]) -> str:
    """Joins strings with a space, unless the previous string ended in a newline."""
    if not strings:
        return ""

    result = [strings[0]]
    for s in strings[1:]:
        if result[-1].endswith("\n"):
            result.append(s)
        else:
            result.append(" " + s)

    return "".join(result)


def format_doc(app: "App", format: str = "restructuredtext"):
    raw_doc_string = app.help

    if not raw_doc_string:
        return _silent

    parsed = docstring_parse(raw_doc_string, format)

    components: list[str] = []
    if parsed.short_description:
        components.append(parsed.short_description + "\n")

    if parsed.long_description:
        if parsed.short_description:
            components.append("\n")
        components.append(parsed.long_description + "\n")
    return InlineText.from_format(_smart_join(components), format=format, force_empty_end=True)


def _get_choices(type_: type, name_transform: Callable[[str], str]) -> list[str]:
    get_choices = partial(_get_choices, name_transform=name_transform)
    choices = []
    _origin = get_origin(type_)
    if isclass(type_) and issubclass(type_, Enum):
        choices.extend(name_transform(x) for x in type_.__members__)
    elif is_union(_origin):
        inner_choices = [get_choices(inner) for inner in get_args(type_)]
        for x in inner_choices:
            if x:
                choices.extend(x)
    elif _origin is Literal:
        choices.extend(str(x) for x in get_args(type_))
    elif _origin in ITERABLE_TYPES:
        args = get_args(type_)
        if len(args) == 1 or (_origin is tuple and len(args) == 2 and args[1] is Ellipsis):
            choices.extend(get_choices(args[0]))
    elif _origin is Annotated:
        choices.extend(get_choices(resolve_annotated(type_)))
    elif TypeAliasType is not None and isinstance(type_, TypeAliasType):
        choices.extend(get_choices(type_.__value__))
    return choices


def create_parameter_help_panel(
    group: "Group",
    argument_collection: "ArgumentCollection",
    format: str,
) -> AbstractRichHelpPanel:
    from rich.text import Text

    help_panel = AbstractRichHelpPanel(
        format="parameter",
        title=group.name,
        description=InlineText.from_format(group.help, format=format, force_empty_end=True) if group.help else Text(),
    )

    def help_append(text, style):
        if help_components:
            text = " " + text
        if style:
            help_components.append((text, style))
        else:
            help_components.append(text)

    entries_positional, entries_kw = [], []
    for argument in argument_collection.filter_by(show=True):
        assert argument.parameter.name_transform

        help_components = []
        options = list(argument.names)

        # Add an all-uppercase name if it's an argument
        if argument.index is not None:
            arg_name = options[0].lstrip("-").upper()
            if arg_name != options[0]:
                options = [arg_name, *options]

        short_options, long_options = [], []
        for option in options:
            if _is_short(option):
                short_options.append(option)
            else:
                long_options.append(option)

        help_description = InlineText.from_format(argument.parameter.help, format=format)

        if argument.parameter.show_choices:
            choices = _get_choices(argument.hint, argument.parameter.name_transform)
            choices = ", ".join(choices)
            if choices:
                help_description.append(Text(rf"[choices: {choices}]", "dim"))

        if argument.parameter.show_env_var and argument.parameter.env_var:
            env_vars = ", ".join(argument.parameter.env_var)
            help_description.append(Text(rf"[env var: {env_vars}]", "dim"))

        if argument.show_default:
            if isclass(argument.hint) and issubclass(argument.hint, Enum):
                default = argument.parameter.name_transform(argument.field_info.default.name)
            else:
                default = argument.field_info.default
            if callable(argument.show_default):
                default = argument.show_default(default)

            help_description.append(Text(rf"[default: {default}]", "dim"))

        if argument.required:
            help_description.append(Text(r"[required]", "dim red"))

        # populate row
        entry = AbstractTableEntry(
                name="".join(long_options),
                description= help_description,
                short= "".join(short_options),
                required= argument.required,
        )

        if argument.field_info.is_positional:
            entries_positional.append(entry)
        else:
            entries_kw.append(entry)

    help_panel.entries.extend(entries_positional)
    help_panel.entries.extend(entries_kw)

    return help_panel


def format_command_entries(apps: Iterable["App"], format: str) -> list[AbstractTableEntry]:
    entries = []
    for app in apps:
        if not app.show:
            continue
        short_names, long_names = [], []
        for name in app.name:
            short_names.append(name) if _is_short(name) else long_names.append(name)

        print(f"The SHORTS ARE: {short_names} the LONGS ARE: {long_names}")
        entry = AbstractTableEntry(
            name= "\n".join(long_names),
            short=" ".join(short_names),
            description=InlineText.from_format(docstring_parse(app.help, format).short_description, format=format),
            sort_key=resolve_callables(app.sort_key, app),
        )
        if entry not in entries:
            entries.append(entry)
    return entries


def resolve_help_format(app_chain: Iterable["App"]) -> str:
    # Resolve help_format; None fallsback to parent; non-None overwrites parent.
    format_ = "restructuredtext"
    for app in app_chain:
        if app.help_format is not None:
            format_ = app.help_format
    return format_


def resolve_version_format(app_chain: Iterable["App"]) -> str:
    format_ = resolve_help_format(app_chain)
    for app in app_chain:
        if app.version_format is not None:
            format_ = app.version_format
    return format_


# named like a class because it's just a very thin wrapper around a class.
def CycloptsPanel(message: Any, title: str = "Error", style: str = "red") -> "Panel":  # noqa: N802
    """Create a :class:`~rich.panel.Panel` with a consistent style.

    The resulting panel can be displayed using a :class:`~rich.console.Console`.

    .. code-block:: text

        ╭─ Title ──────────────────────────────────╮
        │ Message content here.                    │
        ╰──────────────────────────────────────────╯

    Parameters
    ----------
    message: Any
        The body of the panel will be filled with the stringified version of the message.
    title: str
        Title of the panel that appears in the top-left corner.
    style: str
        Rich `style <https://rich.readthedocs.io/en/stable/style.html>`_ for the panel border.

    Returns
    -------
    rich.panel.Panel
        Formatted panel object.
    """
    from rich import box
    from rich.panel import Panel
    from rich.text import Text

    panel = Panel(
        Text(str(message), "default"),
        title=title,
        style=style,
        box=box.ROUNDED,
        expand=True,
        title_align="left",
    )
    return panel
