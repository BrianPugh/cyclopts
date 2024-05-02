import inspect
from enum import Enum
from functools import lru_cache, partial
from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Callable,
    Iterable,
    List,
    Literal,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

import docstring_parser
from attrs import define, field, frozen

import cyclopts.utils
from cyclopts.group import Group
from cyclopts.parameter import Parameter, get_hint_parameter

if TYPE_CHECKING:
    from rich.console import RenderableType

    from cyclopts.core import App


@lru_cache(maxsize=16)
def docstring_parse(doc: str):
    """Addon to :func:`docstring_parser.parse` that double checks the `short_description`."""
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


def _text_factory():
    from rich.text import Text

    return Text()


@define
class HelpPanel:
    format: Literal["command", "parameter"]
    title: str
    description: "RenderableType" = field(factory=_text_factory)
    entries: List[HelpEntry] = field(factory=list)

    def remove_duplicates(self):
        seen, out = set(), []
        for item in self.entries:
            hashable = (item.name, item.short)
            if hashable not in seen:
                seen.add(hashable)
                out.append(item)
        self.entries = out

    def sort(self):
        self.entries.sort(key=lambda x: (x.name.startswith("-"), x.name))

    def __rich__(self):
        if not self.entries:
            return _silent
        from rich.box import ROUNDED
        from rich.console import Group as RichGroup
        from rich.console import NewLine
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        table = Table.grid(padding=(0, 1))
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
            table.add_column(justify="left", style="cyan")
            table.add_column(justify="left")

            for entry in self.entries:
                name = entry.name
                if entry.short:
                    name += "," + entry.short
                table.add_row(name + " ", entry.description)
        elif self.format == "parameter":
            has_short = any(entry.short for entry in self.entries)
            has_required = any(entry.required for entry in self.entries)

            if has_required:
                table.add_column(justify="left", width=1, style="red bold")  # For asterisk
            table.add_column(justify="left", no_wrap=True, style="cyan")  # For option names
            if has_short:
                table.add_column(justify="left", no_wrap=True, style="green")  # For short options
            table.add_column(justify="left")  # For main help text.

            for entry in self.entries:
                row = []
                if has_required:
                    if entry.required:
                        row.append("*")
                    else:
                        row.append("")
                row.append(entry.name + " ")
                if has_short:
                    row.append(entry.short + " ")
                row.append(entry.description)
                table.add_row(*row)
        else:
            raise NotImplementedError

        return panel


class SilentRich:
    """Dummy object that causes nothing to be printed."""

    def __rich_console__(self, console, options):
        # This generator yields nothing, so ``rich`` will print nothing for this object.
        if False:
            yield


_silent = SilentRich()


def _is_short(s):
    return not s.startswith("--") and s.startswith("-")


def format_usage(
    app,
    command_chain: List[str],
):
    from rich.text import Text

    usage = []
    usage.append("Usage:")
    usage.append(app.name[0])
    usage.extend(command_chain)

    for command in command_chain:
        app = app[command]

    if app._commands:
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


def format_doc(root_app, app: "App", format: str = "restructuredtext"):
    from rich.console import Group as RichGroup
    from rich.console import NewLine
    from rich.text import Text

    raw_doc_string = app.help

    if not raw_doc_string:
        return _silent

    parsed = docstring_parse(raw_doc_string)

    components: List[Union[str, Tuple[str, str]]] = []
    if parsed.short_description:
        components.append(parsed.short_description + "\n")

    if parsed.long_description:
        if parsed.short_description:
            components.append("\n")
        components.append((parsed.long_description + "\n", "info"))

    return RichGroup(_format(*components, format=format), NewLine())


def _format(*components: Union[str, Tuple[str, str]], format: str = "restructuredtext") -> "RenderableType":
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
                    yield Text.from_markup(component[0].rstrip(), style=component[1])

        return Text().join(walk_components())
    else:
        raise ValueError(f'Unknown help_format "{format}"')


def _get_choices(type_: Type, name_transform: Callable[[str], str]) -> str:
    get_choices = partial(_get_choices, name_transform=name_transform)
    choices: str = ""
    _origin = get_origin(type_)
    if isclass(type_) and issubclass(type_, Enum):
        choices = ",".join(name_transform(x.name) for x in type_)
    elif _origin is Union:
        inner_choices = [get_choices(inner) for inner in get_args(type_)]
        choices = ",".join(x for x in inner_choices if x)
    elif _origin is Literal:
        choices = ",".join(str(x) for x in get_args(type_))
    elif _origin in (list, set, tuple):
        args = get_args(type_)
        if len(args) == 1 or (_origin is tuple and len(args) == 2 and args[1] is Ellipsis):
            choices = get_choices(args[0])
    return choices


def create_parameter_help_panel(
    group: "Group",
    iparams,
    cparams: List[Parameter],
    format: str,
) -> HelpPanel:
    help_panel = HelpPanel(format="parameter", title=group.name, description=_format(group.help, format=format))
    icparams = [(ip, cp) for ip, cp in zip(iparams, cparams) if cp.show]

    if not icparams:
        return help_panel

    iparams, cparams = (list(x) for x in zip(*icparams))

    def help_append(text, style=""):
        if help_components:
            text = " " + text
        if style:
            help_components.append((text, style))
        else:
            help_components.append(text)

    for iparam, cparam in icparams:
        assert cparam.name is not None
        assert cparam.name_transform is not None
        type_ = get_hint_parameter(iparam)[0]
        options = list(cparam.name)
        options.extend(cparam.get_negatives(type_, *options))

        # Add an all-uppercase name if it's an argument
        if iparam.kind in (iparam.POSITIONAL_ONLY, iparam.POSITIONAL_OR_KEYWORD):
            arg_name = options[0].lstrip("-").upper()
            if arg_name != options[0]:
                options = [arg_name, *options]

        short_options, long_options = [], []
        for option in options:
            if _is_short(option):
                short_options.append(option)
            else:
                long_options.append(option)

        help_components = []

        if cparam.help:
            help_append(cparam.help)

        if cparam.show_choices:
            choices = _get_choices(type_, cparam.name_transform)
            if choices:
                help_append(rf"[choices: {choices}]", "dim")

        if cparam.show_env_var and cparam.env_var:
            env_vars = " ".join(cparam.env_var)
            help_append(rf"[env var: {env_vars}]", "dim")

        if cparam.show_default or (
            cparam.show_default is None and iparam.default not in {None, inspect.Parameter.empty}
        ):
            default = ""
            if isclass(type_) and issubclass(type_, Enum):
                default = cparam.name_transform(iparam.default.name)
            else:
                default = iparam.default

            help_append(rf"[default: {default}]", "dim")

        if cparam.required:
            help_append(r"[required]", "dim red")

        # populate row
        help_panel.entries.append(
            HelpEntry(
                name=",".join(long_options),
                description=_format(*help_components, format=format),
                short=",".join(short_options),
                required=bool(cparam.required),
            )
        )

    return help_panel


def format_command_entries(apps: Iterable["App"], format: str) -> List:
    entries = []
    for app in apps:
        short_names, long_names = [], []
        for name in app.name:
            short_names.append(name) if _is_short(name) else long_names.append(name)
        entry = HelpEntry(
            name=",".join(long_names),
            short=",".join(short_names),
            description=_format(docstring_parse(app.help).short_description or "", format=format),
        )
        if entry not in entries:
            entries.append(entry)
    return entries


def resolve_help_format(app_chain: Iterable["App"]) -> str:
    # Resolve help_format; None fallsback to parent; non-None overwrites parent.
    help_format = "restructuredtext"
    for app in app_chain:
        if app.help_format is not None:
            help_format = app.help_format
    return help_format
