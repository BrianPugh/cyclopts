import inspect
import sys
from contextlib import suppress
from enum import Enum
from functools import lru_cache
from inspect import isclass
from typing import TYPE_CHECKING, Callable, Dict, List, Literal, Optional, Tuple, Type, Union, get_args, get_origin

from docstring_parser import DocstringParam
from docstring_parser import parse as docstring_parse
from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

if TYPE_CHECKING:
    from cyclopts.core import App

from cyclopts.exceptions import DocstringError
from cyclopts.group import Group
from cyclopts.parameter import Parameter, get_hint_parameter, get_names

docstring_parse = lru_cache(maxsize=16)(docstring_parse)


def parameter2docstring(f: Callable) -> Dict[inspect.Parameter, DocstringParam]:
    parsed = docstring_parse(f.__doc__)
    inspect_parameters = inspect.signature(f).parameters

    out = {}
    for doc_param in parsed.params:
        try:
            inspect_parameter = inspect_parameters[doc_param.arg_name]
            out[inspect_parameter] = doc_param
        except KeyError:
            # Even though we could pass/continue, we're raising
            # an exception because the developer really aught to know.
            raise DocstringError(
                f"Docstring parameter {doc_param.arg_name} has no equivalent in function signature."
            ) from None

    return out


class SilentRich:
    """Dummy object that causes nothing to be printed."""

    def __rich_console__(self, console, options):
        # This generator yields nothing, so ``rich`` will print nothing for this object.
        if False:
            yield


_silent = SilentRich()


def create_panel_table(**kwargs):
    table = Table.grid(padding=(0, 1))
    panel = Panel(
        table,
        box=box.ROUNDED,
        expand=True,
        title_align="left",
        **kwargs,
    )
    return panel, table


def create_panel_table_commands(**kwargs):
    panel, table = create_panel_table(**kwargs)

    table.add_column(justify="left", style="cyan")
    table.add_column(justify="left")

    return panel, table


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
    from cyclopts.core import App

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


def format_group_parameters(app, group, iparams_):
    from cyclopts.group_extractors import iparam_to_groups

    panel, table = create_panel_table(title=group.name)
    has_required, has_short = False, False
    help_lookup = parameter2docstring(app.default_command) if app.default_command else {}

    iparams = []
    for iparam in iparams_:
        groups = iparam_to_groups(iparam, app.default_parameter, app.group_arguments, app.group_parameters)
        _, param = get_hint_parameter(iparam.annotation, app.default_parameter, *(x.default_parameter for x in groups))
        if not param.parse or not param.show:
            continue
        iparams.append(iparam)

    def is_required(parameter):
        return parameter.default is parameter.empty

    def is_short(s):
        return not s.startswith("--") and s.startswith("-")

    has_required = any(is_required(p) for p in iparams)

    for iparam in iparams:
        groups = iparam_to_groups(iparam, app.default_parameter, app.group_arguments, app.group_parameters)
        type_, param = get_hint_parameter(
            iparam.annotation, app.default_parameter, *(x.default_parameter for x in groups)
        )
        if not param.show:
            continue
        has_short = any(
            is_short(x) for x in get_names(iparam, app.default_parameter, *(x.default_parameter for x in groups))
        )
        if has_short:
            break

    if has_required:
        table.add_column(justify="left", width=1, style="red bold")  # For asterisk
    table.add_column(justify="left", no_wrap=True, style="cyan")  # For option names
    if has_short:
        table.add_column(justify="left", no_wrap=True, style="green")  # For short options
    table.add_column(justify="left")  # For main help text.

    for iparam in iparams:
        groups = iparam_to_groups(iparam, app.default_parameter, app.group_arguments, app.group_parameters)
        type_, param = get_hint_parameter(
            iparam.annotation, app.default_parameter, *(x.default_parameter for x in groups)
        )

        options = get_names(iparam, app.default_parameter, *(x.default_parameter for x in groups))
        options.extend(param.get_negatives(type_, *options))

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
        if param.help is not None:
            help_components.append(param.help)
        else:
            with suppress(KeyError):
                help_components.append(help_lookup[iparam].description)

        if param.show_choices:
            choices = _get_choices(type_)
            if choices:
                help_components.append(rf"[dim]\[choices: {choices}][/dim]")

        if param.show_env_var and param.env_var:
            env_vars = " ".join(param.env_var)
            help_components.append(rf"[dim]\[env var: {env_vars}][/dim]")

        if not is_required(iparam) and (
            param.show_default or (param.show_default is None and iparam.default is not None)
        ):
            default = ""
            if isclass(type_) and issubclass(type_, Enum):
                default = iparam.default.name.lower().replace("_", "-")
            else:
                default = iparam.default

            help_components.append(rf"[dim]\[default: {default}][/dim]")
        if is_required(iparam):
            help_components.append(r"[red][dim]\[required][/dim][/red]")

        # populate row
        row_args = []
        if has_required:
            row_args.append("*" if is_required(iparam) else "")
        row_args.append(",".join(long_options) + " ")  # a little extra padding
        if has_short:
            row_args.append(",".join(short_options) + " ")  # a little extra padding
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
