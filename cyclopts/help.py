from typing import Callable, Iterable, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cyclopts.docstring import DocString
from cyclopts.exceptions import CycloptsError, UnreachableError


def _create_two_col_panel(title: str, col_1_strings: Iterable[str]):
    # Calculate maximum width
    width = max(len(s) for s in col_1_strings)

    table = Table.grid(padding=(0, 1))
    table.add_column(justify="left", no_wrap=True, width=width)
    table.add_column(justify="left", no_wrap=False)

    panel = Panel(
        table,
        box=box.ROUNDED,
        expand=True,
        title=title,
        title_align="left",
    )
    return panel, table


def _format_usage(self, function):
    usage_string = []
    usage_string.append("Usage:")
    usage_string.extend(self._help_command_prefixes)
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


def _format_options(self, function):
    for command_name, command_fn in self._commands.items():
        pass
    breakpoint()
    panel, table = _create_two_col_panel("Options")

    raise NotImplementedError


def _format_commands(self):
    for command_name, command_fn in self._commands.items():
        pass
    breakpoint()
    raise NotImplementedError


class HelpMixin:
    def display_help(self, *, function: Optional[Callable] = None, console: Optional[Console] = None):
        if console is None:
            console = Console()

        console.print(_format_usage(self, function))
        console.print(_format_doc(self, function))
        breakpoint()
        # console.print(_format_options(self))
        return

        if True:  # TODO
            console.print(_format_arguments(self, function))
        else:
            console.print(_format_commands(self, function))
