import argparse
from functools import partial
from itertools import chain
from typing import Callable, Iterable, List, Optional, Tuple

from attrs import define, field
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cyclopts.docstring import DocString
from cyclopts.exceptions import CycloptsError, UnreachableError


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


def _format_arguments(self, function):
    breakpoint()
    raise NotImplementedError


def _format_global_arguments(self, function):
    panel, table = _create_panel_table()
    for action in self.argparse._actions:
        # Most _StoreAction attributes default are None.
        breakpoint()


def _format_global_options(self, function):
    actions = [x for x in self.argparse._actions if x.option_strings]
    if not actions:
        return _silent

    has_required = any(x.required for x in actions)
    options, options_short = [], []
    for action in actions:
        _options, _options_short = [], []
        for s in action.option_strings:
            if s.startswith("--"):
                _options.append(s)
            else:
                _options_short.append(s)
        options.append(",".join(_options))
        options_short.append(",".join(_options_short))

    has_short = any(options_short)

    panel, table = _create_panel_table(title="Global Options")
    if has_required:
        table.add_column(justify="left", width=1, style="red bold")
    table.add_column(justify="left", width=max(len(x) for x in options), style="cyan")
    if has_short:
        table.add_column(justify="left", width=max(len(x) for x in options_short) + 1, style="green")
    table.add_column(justify="left")

    # Populate the table
    for action, option, option_short in zip(actions, options, options_short):
        row_args = []
        if has_required:
            row_args.append("*" if action.required else "")
        row_args.append(option)
        if has_short:
            row_args.append(option_short)
        row_args.append(action.help)  # TODO: probably want to add default & choices here.

        table.add_row(*row_args)

    return panel


def _format_options(self, function):
    # --option -o limitations helpstring
    if function is None:
        for command_name, command_fn in self._commands.items():
            pass
        breakpoint()

        raise NotImplementedError
    else:
        # Check the global argparse
        breakpoint()
        panel, table = _create_two_col_panel("Options")
        raise NotImplementedError

    raise NotImplementedError


def _format_commands(self):
    for command_name, command_fn in self._commands.items():
        pass
    breakpoint()
    raise NotImplementedError


@define(kw_only=True)
class HelpMixin:
    help: str = ""

    help_flags: Iterable[str] = field(factory=lambda: ["--help", "-h"])

    help_panel_prefix: str = ""

    help_print_usage: bool = True
    help_print_options: bool = True
    help_print_commands: bool = True

    ######################
    # Private Attributes #
    ######################
    # A list of higher up ``cyclopts.App``.
    # Used for printing "Usage" help-string.
    _help_usage_prefixes: List[str] = field(init=False, factory=list)

    def help_print(self, *, function: Optional[Callable] = None, console: Optional[Console] = None):
        if console is None:
            console = Console()

        if self.help_print_usage:
            console.print(_format_usage(self, function))
        console.print(_format_doc(self, function))
        # console.print(_format_global_arguments(self, function))
        # console.print(_format_global_options(self, function))
        breakpoint()
        console.print(_format_options(self, function))
        breakpoint()
        # console.print(_format_options(self))
        return

        if True:  # TODO
            console.print(_format_arguments(self, function))
        else:
            console.print(_format_commands(self, function))
