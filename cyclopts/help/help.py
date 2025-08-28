import inspect
import sys
from collections.abc import Iterable
from enum import Enum
from functools import lru_cache, partial
from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Literal,
    Optional,
    Sequence,
    Union,
    get_args,
    get_origin,
)

from attrs import Factory, define, evolve, field

from cyclopts._convert import ITERABLE_TYPES
from cyclopts.annotations import is_union, resolve_annotated
from cyclopts.field_info import signature_parameters
from cyclopts.group import Group
from cyclopts.help.specs import PanelSpec, TableSpec
from cyclopts.utils import SortHelper, resolve_callables

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
    from rich.text import Text

    from cyclopts.argument import ArgumentCollection
    from cyclopts.core import App
    from cyclopts.help.protocols import LazyData

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


def _resolve(v: Union["RenderableType", "LazyData"], entry: "TableEntry") -> "RenderableType":
    return v(entry) if callable(v) else v


# TODO: Is there a low cost runtime validator that all members in this
#       are renderable?
@define(slots=True)
class TableData:
    """Intentionally empty dataclass.

    Users can inherit from this and declare concrete fields and then pass
    the object to TableEntry
    """

    pass


@define(slots=True)
class TableEntry:
    """Abstract version of TableEntry.

    Member extras can be a user-defined dataclass. All members in `extras`
    will be treated as if they are members of `TableEntry` allowing
    for arbitrary data to be included in the Entry.
    """

    from rich.console import RenderableType

    name: Optional[str] = None
    short: Optional[str] = None
    description: Optional[RenderableType] = None
    required: bool = False
    sort_key: Any = None

    extras: TableData = field(factory=TableData, repr=False)

    def try_put(self, key: str, value: Optional[Union["RenderableType", "LazyData"]]):
        """Put a attr to the dataclass.

        This is looser than put, and will not raise an AttributeError if
        the member does not exist. This is useful when the list of entries
        do not have all the same members. This was required for
        `ColumnSpec.render_cell`
        """
        try:
            return self.put(key, value)
        except AttributeError:
            return self

    def put(self, key: str, value: Optional[Union["RenderableType", "LazyData"]]):
        """Put a attr to the dataclass."""
        if hasattr(self, key):
            setattr(self, key, value)
        elif hasattr(self.extras, key):
            setattr(self.extras, key, value)
        else:
            raise AttributeError(f"'{type(self.extras).__name__}' has no field {key}")
        return self

    def get(self, key: str, default: Any = None, resolve: bool = False) -> Union["LazyData", "RenderableType"]:
        if hasattr(self, key):
            val = getattr(self, key)
            return _resolve(val, self) if resolve else val
        if hasattr(self.extras, key):
            val = getattr(self.extras, key)
            return _resolve(val, self) if resolve else val
        return default

    def __getattr__(self, name: str) -> Union[str, "LazyData"]:
        """Access extra values as if they were members.

        This makes members in the `extra` dataclass feel like
        members of the `TableEntry` instance. Thus, pseudo
        adding members is easy, and table generation is simplified.
        """
        extras = object.__getattribute__(self, "extras")
        try:
            return getattr(extras, name)
        except AttributeError as err:
            raise AttributeError(f"'{type(self)} nor {type(self.extras).__name__}' have field {name}") from err

    def with_(self, **kw):
        return evolve(self, **kw)


@define
class HelpPanel:
    """Adjust the Format for the help panel!."""

    from rich.box import ROUNDED, Box
    from rich.console import Group as RichGroup
    from rich.console import NewLine, RenderableType
    from rich.panel import Panel
    from rich.table import Column, Table
    from rich.text import Text

    # TODO: This is _only_ here for convenience to be passed to table_spec
    #       otherwise, we could instantiate this panel and then
    #       instantiate the table_spec with the correct format.
    #
    # I.E) Without this, to make a HelpPanel we'll have to make and
    #       pass a list of column specs.
    format: str  # Literal["command", "parameter"]

    title: RenderableType
    description: RenderableType = field(factory=_text_factory)
    entries: list[TableEntry] = field(factory=list)

    table_spec: TableSpec = field(default=Factory(lambda self: TableSpec(preset=self.format), takes_self=True))
    panel_spec: PanelSpec = field(default=Factory(lambda self: PanelSpec(title=self.title), takes_self=True))

    def remove_duplicates(self):
        seen, out = set(), []
        for item in self.entries:
            hashable = (item.name, item.short)
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
                [
                    SortHelper(
                        entry.sort_key,
                        (entry.name.startswith("-") if entry.name is not None else False, entry.name),
                        entry,
                    )
                    for entry in self.entries
                ]
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

        panel_description = self.description
        if isinstance(panel_description, Text):
            panel_description.end = ""

            if panel_description.plain:
                panel_description = RichGroup(panel_description, NewLine(2))

        # 2. Realize spec, build table, and add entries
        table_spec = self.table_spec.realize_columns(console, options, self.entries)
        table = table_spec.build()
        table_spec.add_entries(table, self.entries)

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
) -> HelpPanel:
    from rich.text import Text

    help_panel = HelpPanel(
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
        entry = TableEntry(
            name="".join(long_options),
            description=help_description,
            short="".join(short_options),
            required=argument.required,
        )

        if argument.field_info.is_positional:
            entries_positional.append(entry)
        else:
            entries_kw.append(entry)

    help_panel.entries.extend(entries_positional)
    help_panel.entries.extend(entries_kw)

    return help_panel


def format_command_entries(apps: Iterable["App"], format: str) -> list[TableEntry]:
    entries = []
    for app in apps:
        if not app.show:
            continue
        short_names, long_names = [], []
        for name in app.name:
            short_names.append(name) if _is_short(name) else long_names.append(name)

        entry = TableEntry(
            name="\n".join(long_names),
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
