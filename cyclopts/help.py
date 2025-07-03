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
)

from attrs import define, field

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


@frozen
class HelpEntry:
    name: str
    short: str
    description: "RenderableType"
    required: bool = False
    sort_key: Any = None


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


@define
class HelpPanel:
    format: Literal["command", "parameter"]
    title: str
    description: "RenderableType" = field(factory=_text_factory)
    entries: list[HelpEntry] = field(factory=list)

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
                [SortHelper(entry.sort_key, (entry.name.startswith("-"), entry.name), entry) for entry in self.entries]
            )
            self.entries = [x.value for x in sorted_sort_helper]
        else:
            raise NotImplementedError

    def __rich_console__(self, console: "Console", options: "ConsoleOptions") -> "RenderResult":
        if not self.entries:
            return _silent

        import textwrap

        from rich.box import ROUNDED
        from rich.console import Group as RichGroup
        from rich.console import NewLine
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        wrap = partial(
            textwrap.wrap,
            subsequent_indent="  ",
            break_on_hyphens=False,
            tabsize=4,
        )
        # (top, right, bottom, left)
        table = Table.grid(padding=(0, 2, 0, 0), pad_edge=False)
        panel_description = self.description

        if isinstance(panel_description, Text):
            panel_description.end = ""

            if panel_description.plain:
                panel_description = RichGroup(panel_description, NewLine(2))

        panel = Panel(
            RichGroup(panel_description, table),
            box=ROUNDED,
            expand=True,
            title_align="left",
            title=self.title,
        )

        if self.format == "command":
            commands_width = ceil(console.width * 0.35)
            table.add_column("Commands", justify="left", max_width=commands_width, style="cyan")
            table.add_column("Description", justify="left")

            for entry in self.entries:
                name = entry.name
                if entry.short:
                    name += " " + entry.short
                name = "\n".join(wrap(name, commands_width))
                table.add_row(name, entry.description)
        elif self.format == "parameter":
            options_width = ceil(console.width * 0.35)
            short_width = ceil(console.width * 0.1)

            has_short = any(entry.short for entry in self.entries)
            has_required = any(entry.required for entry in self.entries)

            if has_required:
                table.add_column("Asterisk", justify="left", width=1, style="red bold")
            table.add_column("Options", justify="left", overflow="fold", max_width=options_width, style="cyan")
            if has_short:
                table.add_column("Short", justify="left", overflow="fold", max_width=short_width, style="green")
            table.add_column("Description", justify="left", overflow="fold")

            lookup = {col.header: (i, col.max_width) for i, col in enumerate(table.columns)}
            for entry in self.entries:
                row = [""] * len(table.columns)

                def add(key, value, custom_wrap=False):
                    try:
                        index, max_width = lookup[key]
                    except KeyError:
                        return
                    if custom_wrap and max_width:
                        value = "\n".join(wrap(value, max_width))
                    row[index] = value  # noqa: B023

                add("Asterisk", "*" if entry.required else "")
                add("Options", entry.name, custom_wrap=True)
                add("Short", entry.short)
                add("Description", entry.description)
                table.add_row(*row)
        else:
            raise NotImplementedError

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
        entry = HelpEntry(
            name=" ".join(long_options),
            description=help_description,
            short=" ".join(short_options),
            required=argument.required,
        )

        if argument.field_info.is_positional:
            entries_positional.append(entry)
        else:
            entries_kw.append(entry)

    help_panel.entries.extend(entries_positional)
    help_panel.entries.extend(entries_kw)

    return help_panel


def format_command_entries(apps: Iterable["App"], format: str) -> list[HelpEntry]:
    entries = []
    for app in apps:
        if not app.show:
            continue
        short_names, long_names = [], []
        for name in app.name:
            short_names.append(name) if _is_short(name) else long_names.append(name)
        entry = HelpEntry(
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
