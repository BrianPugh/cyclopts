import inspect
import sys
from collections.abc import Iterable
from enum import Enum
from functools import lru_cache, partial
from inspect import isclass
from math import ceil
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    Union,
    get_args,
    get_origin,
)

from attrs import define, field

import cyclopts.utils
from cyclopts.annotations import is_union
from cyclopts.group import Group
from cyclopts.utils import SortHelper, frozen, resolve_callables

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderableType, RenderResult

    from cyclopts.argument import ArgumentCollection
    from cyclopts.core import App

if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import TypeAliasType
else:  # pragma: no cover
    TypeAliasType = None


@lru_cache(maxsize=16)
def docstring_parse(doc: str):
    """Addon to :func:`docstring_parser.parse` that double checks the `short_description`."""
    import docstring_parser

    res = docstring_parser.parse(doc)
    cleaned_doc = inspect.cleandoc(doc)
    short = cleaned_doc.split("\n\n")[0]
    if res.short_description != short:
        if res.long_description is None:
            res.long_description = res.short_description
        elif res.short_description is not None:
            res.long_description = res.short_description + "\n" + res.long_description
        res.short_description = None
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
        """Sort entries in-place.

        Callable sort_keys are provided with no argument?
        """
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
        else:
            # Should be either a RST or Markdown object
            if panel_description.markup:  # pyright: ignore[reportAttributeAccessIssue]
                panel_description = RichGroup(panel_description, NewLine(1))

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

    if any(x.show for x in app.subapps):
        usage.append("COMMAND")

    if app.default_command:
        to_show = set()
        for parameter in cyclopts.utils.signature(app.default_command).parameters.values():
            if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.VAR_POSITIONAL, parameter.POSITIONAL_OR_KEYWORD):
                to_show.add("[ARGS]")
            if parameter.kind in (parameter.KEYWORD_ONLY, parameter.VAR_KEYWORD, parameter.POSITIONAL_OR_KEYWORD):
                to_show.add("[OPTIONS]")
        usage.extend(sorted(to_show))

    return Text(" ".join(usage) + "\n", style="bold")


def format_doc(app: "App", format: str = "restructuredtext"):
    from rich.console import Group as RichGroup
    from rich.console import NewLine

    raw_doc_string = app.help

    if not raw_doc_string:
        return _silent

    parsed = docstring_parse(raw_doc_string)

    components: list[Union[str, tuple[str, str]]] = []
    if parsed.short_description:
        components.append(parsed.short_description + "\n")

    if parsed.long_description:
        if parsed.short_description:
            components.append("\n")
        components.append(parsed.long_description + "\n")

    return RichGroup(format_str(*components, format=format), NewLine())


def format_str(*components: Union[str, tuple[str, str]], format: str) -> "RenderableType":
    """Format the sequence of components according to format.

    Parameters
    ----------
    components: str | tuple[str, str]
        Either a plain string, or a tuple of string and formatting style.
        If formatting style is provided, the string-to-be-displayed WILL be escaped.
    """
    format = format.lower()

    if format == "plaintext":
        from rich.text import Text

        aggregate = []
        for component in components:
            if isinstance(component, str):
                aggregate.append(component)
            else:
                aggregate.append(component[0])
        return Text.assemble("".join(aggregate).rstrip())
    elif format in ("markdown", "md"):
        from rich.markdown import Markdown

        aggregate = []
        for component in components:
            if isinstance(component, str):
                aggregate.append(component)
            else:
                # Ignore style for now :(
                aggregate.append(component[0])

        return Markdown("".join(aggregate))
    elif format in ("restructuredtext", "rst"):
        from rich_rst import RestructuredText

        aggregate = []
        for component in components:
            if isinstance(component, str):
                aggregate.append(component)
            else:
                # Ignore style for now :(
                aggregate.append(component[0])
        return RestructuredText("".join(aggregate))
    elif format == "rich":
        from rich.text import Text

        def walk_components():
            for component in components:
                if isinstance(component, str):
                    yield Text.from_markup(component.rstrip())
                else:
                    yield Text(component[0].rstrip(), style=component[1])

        text = Text()
        for component in walk_components():
            text.append(component)
        return text
    else:
        raise ValueError(f'Unknown help_format "{format}"')


def _get_choices(type_: type, name_transform: Callable[[str], str]) -> str:
    get_choices = partial(_get_choices, name_transform=name_transform)
    choices: str = ""
    _origin = get_origin(type_)
    if isclass(type_) and issubclass(type_, Enum):
        choices = ", ".join(name_transform(x.name) for x in type_)
    elif is_union(_origin):
        inner_choices = [get_choices(inner) for inner in get_args(type_)]
        choices = ", ".join(x for x in inner_choices if x)
    elif _origin is Literal:
        choices = ", ".join(str(x) for x in get_args(type_))
    elif _origin in (list, set, tuple):
        args = get_args(type_)
        if len(args) == 1 or (_origin is tuple and len(args) == 2 and args[1] is Ellipsis):
            choices = get_choices(args[0])
    elif TypeAliasType is not None and isinstance(type_, TypeAliasType):
        choices = get_choices(type_.__value__)
    return choices


def create_parameter_help_panel(
    group: "Group",
    argument_collection: "ArgumentCollection",
    format: str,
) -> HelpPanel:
    help_panel = HelpPanel(format="parameter", title=group.name, description=format_str(group.help, format=format))

    def help_append(text, style=""):
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

        if argument.parameter.help:
            help_append(argument.parameter.help)

        if argument.parameter.show_choices:
            choices = _get_choices(argument.hint, argument.parameter.name_transform)
            if choices:
                help_append(rf"[choices: {choices}]", "dim")

        if argument.parameter.show_env_var and argument.parameter.env_var:
            env_vars = ", ".join(argument.parameter.env_var)
            help_append(rf"[env var: {env_vars}]", "dim")

        if argument.show_default:
            default = ""
            if isclass(argument.hint) and issubclass(argument.hint, Enum):
                default = argument.parameter.name_transform(argument.field_info.default.name)
            else:
                default = argument.field_info.default

            help_append(rf"[default: {default}]", "dim")

        if argument.required:
            help_append(r"[required]", "dim red")

        # populate row
        entry = HelpEntry(
            name=" ".join(long_options),
            description=format_str(*help_components, format=format),
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


def format_command_entries(apps: Iterable["App"], format: str) -> list:
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
            description=format_str(docstring_parse(app.help).short_description or "", format=format),
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
