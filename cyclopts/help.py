from typing import Iterable, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


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


def _format_usage(self):
    usage_string = []
    usage_string.append("Usage:")
    usage_string.extend(self._help_command_prefixes)
    usage_string.append(self.name)  # How do we get the prefix commands?
    usage_string.append("COMMAND")
    usage_string.append("[OPTIONS]")
    usage_string.append("[ARGS]")

    return Text(" ".join(usage_string), style="bold")


def _format_arguments(self):
    breakpoint()
    raise NotImplementedError


def _format_options(self):
    breakpoint()
    panel, table = _create_two_col_panel("Options")

    raise NotImplementedError


def _format_commands(self):
    breakpoint()
    raise NotImplementedError


class HelpMixin:
    def display_help(self, console: Optional[Console] = None):
        if console is None:
            console = Console()

        console.print(_format_usage(self))
        console.print(_format_options(self))

        if True:  # TODO
            console.print(_format_arguments(self))
        else:
            console.print(_format_commands(self))
