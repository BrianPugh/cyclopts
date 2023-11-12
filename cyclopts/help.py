import inspect
import typing
from typing import Callable, List, Optional, Tuple

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cyclopts.bind import UnknownTokens
from cyclopts.docstring import DocString
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


def format_usage(app_name, command_chain: List[str]):
    usage_string = []
    usage_string.append("Usage:")
    usage_string.append(app_name)
    usage_string.extend(command_chain)
    usage_string.append("COMMAND")  # TODO: only do this if there are subcommands
    usage_string.append("[OPTIONS]")  # TODO: only do this if there are options
    usage_string.append("[ARGS]")  # TODO: only do this if there are positional arguments
    usage_string.append("\n")

    return Text(" ".join(usage_string), style="bold")


def format_doc(self, function: Optional[Callable]):
    if function is None:
        doc_strings = self.help.split("\n")
    elif isinstance(function, type(self)):
        doc_strings = function.help.split("\n")
    else:
        doc_strings = (function.__doc__ or "").split("\n")

    if not doc_strings:
        return Text()

    components: List[Tuple[str, str]] = [(doc_strings[0], "default")]
    for s in doc_strings[1:]:
        components.append((s, "info"))

    return Text.assemble(*components)


def format_commands(app):
    if not app._commands:
        return _silent

    panel, table = _create_panel_table(title="Commands")

    table.add_column(justify="left", style="cyan")
    table.add_column(justify="left")

    for command_name, command_fn in app._commands.items():
        row_args = []
        row_args.append(command_name)
        docstring = DocString(command_fn)
        row_args.append(docstring.short_description)
        table.add_row(*row_args)
    return panel


def format_parameters(function, title):
    if function is None:
        return _silent

    panel, table = _create_panel_table(title=title)

    parameters = []
    for parameter in inspect.signature(function).parameters.values():
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

        help_components = []
        if param.help:
            help_components.append(param.help)
        if param.show_default and not is_required(parameter):
            help_components.append(rf"[dim]\[default: {parameter.default}][/dim]")

        # populate row
        row_args = []
        if has_required:
            row_args.append("*" if is_required(parameter) else "")
        row_args.append(",".join(options))
        # if has_short:
        #     row_args.append(option_short)
        row_args.append(" ".join(help_components))
        table.add_row(*row_args)

    return panel
