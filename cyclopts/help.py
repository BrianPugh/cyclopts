import inspect
import typing
from textwrap import dedent
from typing import Callable, List, Optional, Tuple

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cyclopts.bind import UnknownTokens
from cyclopts.parameter import get_hint_parameter, get_names


class SilentRich:
    """Dummy object that causes nothing to be printed."""

    def __rich_console__(self, console, options):
        # This generator yields nothing, so 'rich' will print nothing for this object.
        if False:
            yield


_silent = SilentRich()


def _create_panel_table(**kwargs):
    table = Table.grid(padding=(0, 1))
    panel = Panel(
        table,
        box=box.ROUNDED,
        expand=True,
        title_align="left",
        **kwargs,
    )
    return panel, table


def format_usage(
    self,
    command_chain: List[str],
):
    usage = []
    usage.append("Usage:")
    usage.append(self._name_derived)
    usage.extend(command_chain)

    app = self
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

    usage.append("\n")

    return Text(" ".join(usage), style="bold")


def format_doc(self, function: Optional[Callable]):
    if function is None:
        raw_doc_string = self.help
    elif isinstance(function, type(self)):
        raw_doc_string = function.help
    else:
        raw_doc_string = function.__doc__ or ""

    if not raw_doc_string:
        return _silent

    doc_strings = raw_doc_string.split("\n", 1)

    components: List[Tuple[str, str]] = [(doc_strings[0] + "\n", "default")]

    if len(doc_strings) > 1:
        components.append((dedent(doc_strings[1]), "info"))

    return Text.assemble(*components)


def format_commands(app, title):
    if not app._commands:
        return _silent

    panel, table = _create_panel_table(title=title)

    table.add_column(justify="left", style="cyan")
    table.add_column(justify="left")

    for command_name, command_app in app._commands.items():
        row_args = []
        row_args.append(command_name + " ")  # A little extra padding
        row_args.append(command_app._help_short_derived)
        table.add_row(*row_args)

    return panel


def format_parameters(app, title):
    if not app.default_command:
        return _silent

    panel, table = _create_panel_table(title=title)

    parameters = []
    for parameter in inspect.signature(app.default_command).parameters.values():
        hint, param = get_hint_parameter(parameter.annotation)

        if (typing.get_origin(hint) or hint) is UnknownTokens:
            continue

        parameters.append(parameter)

    has_required, has_short = False, False  # noqa: F841

    def is_required(parameter):
        return parameter.default is parameter.empty

    has_required = any(is_required(p) for p in parameters)

    if has_required:
        table.add_column(justify="left", width=1, style="red bold")
    table.add_column(justify="left", no_wrap=True, style="cyan")
    # if has_short:
    #    table.add_column(justify="left", width=max(len(x) for x in options_short) + 1, style="green")
    table.add_column(justify="left")

    for parameter in parameters:
        hint, param = get_hint_parameter(parameter.annotation)
        options = get_names(parameter)

        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD):
            arg_name = options[0].lstrip("-").upper()
            if arg_name != options[0]:
                options = [arg_name, *options]

        help_components = []
        if param.help:
            help_components.append(param.help)
        if param.show_default and not is_required(parameter):
            help_components.append(rf"[dim]\[default: {parameter.default}][/dim]")

        # populate row
        row_args = []
        if has_required:
            row_args.append("*" if is_required(parameter) else "")
        row_args.append(",".join(options) + " ")  # a little extra padding
        # if has_short:
        #     row_args.append(option_short)
        row_args.append(" ".join(help_components))
        table.add_row(*row_args)

    return panel
