import inspect
from enum import Enum
from functools import lru_cache
from inspect import isclass
from typing import Callable, List, Literal, Optional, Tuple, Type, Union, get_args, get_origin

from docstring_parser import parse as docstring_parse
from rich import box, console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cyclopts.group import Group
from cyclopts.parameter import Parameter, get_hint_parameter

docstring_parse = lru_cache(maxsize=16)(docstring_parse)


class SilentRich:
    """Dummy object that causes nothing to be printed."""

    def __rich_console__(self, console, options):
        # This generator yields nothing, so ``rich`` will print nothing for this object.
        if False:
            yield


_silent = SilentRich()


def create_panel_table(**kwargs):
    text = Text(end="")
    table = Table.grid(padding=(0, 1))
    panel = Panel(
        console.Group(text, table),
        box=box.ROUNDED,
        expand=True,
        title_align="left",
        **kwargs,
    )
    return panel, table, text


def create_panel_table_commands(**kwargs):
    panel, table, text = create_panel_table(**kwargs)

    table.add_column(justify="left", style="cyan")
    table.add_column(justify="left")

    return panel, table, text


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


def format_doc(app, function: Optional[Callable]):
    from cyclopts.core import App  # noqa: F811

    if function is None:
        raw_doc_string = app.help_
    elif isinstance(function, App):
        raw_doc_string = function.help_
    else:
        raw_doc_string = function.__doc__ or ""

    if not raw_doc_string:
        return _silent

    parsed = docstring_parse(raw_doc_string)

    components: List[Tuple[str, str]] = []
    if parsed.short_description:
        components.append((parsed.short_description + "\n", "default"))

    if parsed.long_description:
        components.append(("\n" + parsed.long_description + "\n", "info"))

    return Text.assemble(*components)


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


def format_group_parameters(group: "Group", iparams, cparams: List[Parameter]):
    panel, table, text = create_panel_table(title=group.name)
    has_required, has_short = False, False

    icparams = [(ip, cp) for ip, cp in zip(iparams, cparams) if cp.show]
    iparams, cparams = (list(x) for x in zip(*icparams))

    def is_short(s):
        return not s.startswith("--") and s.startswith("-")

    has_required = any(p.required for p in cparams)

    if group.help:
        text.append(group.help + "\n\n")

    for cparam in cparams:
        assert cparam.name is not None
        has_short = any(is_short(x) for x in cparam.name)
        if has_short:
            break

    if has_required:
        table.add_column(justify="left", width=1, style="red bold")  # For asterisk
    table.add_column(justify="left", no_wrap=True, style="cyan")  # For option names
    if has_short:
        table.add_column(justify="left", no_wrap=True, style="green")  # For short options
    table.add_column(justify="left")  # For main help text.

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
            if is_short(option):
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
        row_args = []
        if has_required:
            row_args.append("*" if cparam.required else "")
        row_args.append(",".join(long_options) + " ")
        if has_short:
            row_args.append(",".join(short_options) + " ")
        row_args.append(" ".join(help_components))
        table.add_row(*row_args)

    if table.row_count == 0:
        return _silent

    return panel


def format_command_rows(elements) -> List:
    rows = []
    for element in elements:
        row = (",".join(element.name) + " ", docstring_parse(element.help_).short_description)
        if row not in rows:
            rows.append(row)
    return rows
