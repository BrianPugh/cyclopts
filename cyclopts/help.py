import inspect
from enum import Enum
from functools import lru_cache
from inspect import isclass
from typing import TYPE_CHECKING, List, Literal, Tuple, Type, Union, get_args, get_origin

import docstring_parser
from attrs import define, field, frozen
from rich import box, console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cyclopts.group import Group
from cyclopts.parameter import Parameter, get_hint_parameter

if TYPE_CHECKING:
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
    short: str = ""
    description: str = ""
    required: bool = False


@define
class HelpPanel:
    format: Literal["command", "parameter"]
    title: str
    description: str = ""
    entries: List[HelpEntry] = field(factory=list)

    def remove_duplicates(self):
        seen, out = set(), []
        for item in self.entries:
            if item not in seen:
                seen.add(item)
                out.append(item)
        self.entries = out

    def sort(self):
        self.entries.sort(key=lambda x: (x.name.startswith("-"), x.name))

    def __rich__(self):
        if not self.entries:
            return _silent
        table = Table.grid(padding=(0, 1))
        text = Text(end="")
        if self.description:
            text.append(self.description + "\n\n")
        panel = Panel(
            console.Group(text, table),
            box=box.ROUNDED,
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
        for parameter in inspect.signature(app.default_command).parameters.values():
            if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.VAR_POSITIONAL, parameter.POSITIONAL_OR_KEYWORD):
                to_show.add("[ARGS]")
            if parameter.kind in (parameter.KEYWORD_ONLY, parameter.VAR_KEYWORD, parameter.POSITIONAL_OR_KEYWORD):
                to_show.add("[OPTIONS]")
        usage.extend(sorted(to_show))

    return Text(" ".join(usage) + "\n", style="bold")


def format_doc(root_app, app: "App", format: str = "restructuredtext"):
    from cyclopts.core import App  # noqa: F811

    raw_doc_string = app.help

    if not raw_doc_string:
        return _silent

    parsed = docstring_parse(raw_doc_string)

    components: List[Tuple[str, str]] = []
    if parsed.short_description:
        components.append((parsed.short_description + "\n", "default"))

    if parsed.long_description:
        if parsed.short_description:
            components.append(("\n", "default"))
        components.append((parsed.long_description + "\n", "info"))

    format = format.lower()
    if format == "plaintext":
        return Text.assemble(*components)
    elif format in ("markdown", "md"):
        from rich.markdown import Markdown

        return console.Group(Markdown("".join(x[0] for x in components)), Text(""))
    elif format in ("restructuredtext", "rst"):
        from rich_rst import RestructuredText

        return RestructuredText("".join(x[0] for x in components))
    else:
        raise ValueError(f'Unknown help_format "{format}"')


def _get_choices(type_: Type) -> str:
    if get_origin(type_) is Union:
        inner_choices = [_get_choices(inner) for inner in get_args(type_)]
        choices = ",".join(x for x in inner_choices if x)
    elif get_origin(type_) is Literal:
        choices = ",".join(str(x) for x in get_args(type_))
    elif isclass(type_) and issubclass(type_, Enum):
        choices = ",".join(x.name.lower().replace("_", "-") for x in type_)
    else:
        choices = ""

    return choices


def create_parameter_help_panel(group: "Group", iparams, cparams: List[Parameter]) -> HelpPanel:
    help_panel = HelpPanel(format="parameter", title=group.name, description=group.help)
    icparams = [(ip, cp) for ip, cp in zip(iparams, cparams) if cp.show]

    if not icparams:
        return help_panel

    iparams, cparams = (list(x) for x in zip(*icparams))

    for iparam, cparam in icparams:
        assert cparam.name is not None
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
            help_components.append(cparam.help)

        if cparam.show_choices:
            choices = _get_choices(type_)
            if choices:
                help_components.append(rf"[dim]\[choices: {choices}][/dim]")

        if cparam.show_env_var and cparam.env_var:
            env_vars = " ".join(cparam.env_var)
            help_components.append(rf"[dim]\[env var: {env_vars}][/dim]")

        if not cparam.required and (
            cparam.show_default or (cparam.show_default is None and iparam.default is not None)
        ):
            default = ""
            if isclass(type_) and issubclass(type_, Enum):
                default = iparam.default.name.lower().replace("_", "-")
            else:
                default = iparam.default

            help_components.append(rf"[dim]\[default: {default}][/dim]")

        if cparam.required:
            help_components.append(r"[red][dim]\[required][/dim][/red]")

        # populate row
        help_panel.entries.append(
            HelpEntry(
                name=",".join(long_options),
                description=" ".join(help_components),
                short=",".join(short_options),
                required=bool(cparam.required),
            )
        )

    return help_panel


def format_command_entries(elements) -> List:
    entries = []
    for element in elements:
        short_names, long_names = [], []
        for name in element.name:
            short_names.append(name) if _is_short(name) else long_names.append(name)
        entry = HelpEntry(
            name=",".join(long_names),
            short=",".join(short_names),
            description=docstring_parse(element.help).short_description or "",
        )
        if entry not in entries:
            entries.append(entry)
    return entries
