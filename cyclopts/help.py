import argparse
import inspect
import typing
from functools import partial
from itertools import chain
from typing import Callable, Iterable, List, Optional, Tuple

from attrs import Factory, define, field
from rich import box
from rich.console import Console, Group
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cyclopts.bind import UnknownTokens
from cyclopts.docstring import DocString
from cyclopts.exceptions import CycloptsError, UnreachableError
from cyclopts.parameter import get_hint_parameter, get_name


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


def _format_usage(self, function):
    usage_string = []
    usage_string.append("Usage:")
    usage_string.extend(self._help_usage_prefixes)
    usage_string.append(self.name)
    if function is not None:
        for name, f in self._commands.items():
            if f == function:
                usage_string.append(name)
                break
    usage_string.append("COMMAND")  # TODO: only do this if there are subcommands
    usage_string.append("[OPTIONS]")  # TODO: only do this if there are options
    usage_string.append("[ARGS]")  # TODO: only do this if there are positional arguments

    return Text(" ".join(usage_string), style="bold")


def _format_doc(self, function):
    doc_strings = self.help.split("\n")

    if not doc_strings:
        return Text()

    components: List[Tuple[str, str]] = [(doc_strings[0], "default")]
    for s in doc_strings[1:]:
        components.append((s, "info"))

    return Text.assemble(*components)


def _format_commands(self, function):
    if not self._commands:
        return _silent

    panel, table = _create_panel_table(title="Commands")

    table.add_column(justify="left", style="cyan")
    table.add_column(justify="left")

    for command_name, command_fn in self._commands.items():
        row_args = []
        row_args.append(command_name)
        docstring = DocString(command_fn)
        row_args.append(docstring.short_description)
        table.add_row(*row_args)
    return panel


def _format_function(self, function):
    if function is None:
        return _silent

    panel, table = _create_panel_table(title=self.help_panel_title)

    parameters = []
    for parameter in inspect.signature(function).parameters.values():
        hint, param = get_hint_parameter(parameter)

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
        hint, param = get_hint_parameter(parameter)
        option = get_name(parameter)

        help_components = []
        if param.help:
            help_components.append(param.help)
        if param.show_default and not is_required(parameter):
            help_components.append(rf"[dim]\[default: {parameter.default}][/dim]")

        # populate row
        row_args = []
        if has_required:
            row_args.append("*" if is_required(parameter) else "")
        row_args.append(option)
        # if has_short:
        #     row_args.append(option_short)
        row_args.append(" ".join(help_components))
        table.add_row(*row_args)

    return panel


@define(kw_only=True)
class HelpMixin:
    help: str = ""

    help_flags: Iterable[str] = field(factory=lambda: ["--help", "-h"])

    help_print: Callable = field(default=Factory(lambda self: self._help_print, takes_self=True))

    help_print_usage: bool = True
    help_print_options: bool = True
    help_print_commands: bool = True

    help_panel_title: str = "Parameters"

    ######################
    # Private Attributes #
    ######################
    # A list of higher up ``cyclopts.App``.
    # Used for printing "Usage" help-string.
    _help_usage_prefixes: List[str] = field(init=False, factory=list)

    def _help_print(self, *, function: Optional[Callable] = None):
        console = Console()

        if self.help_print_usage:
            console.print(_format_usage(self, function))
        console.print(_format_doc(self, function))
        console.print(_format_function(self, function))
        console.print(_format_commands(self, function))
