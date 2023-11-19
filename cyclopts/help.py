import inspect
from textwrap import dedent
from typing import Callable, List, Optional, Tuple

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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

    return Text(" ".join(usage) + "\n", style="bold")


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


def format_parameters(app, title, hide_var_positional=False):
    panel, table = _create_panel_table(title=title)

    has_required, has_short = False, False

    if app.default_command:
        parameters = list(inspect.signature(app.default_command).parameters.values())

        def is_required(parameter):
            if hide_var_positional and parameter.kind == parameter.VAR_POSITIONAL:
                return False
            return parameter.default is parameter.empty

        def is_short(s):
            return not s.startswith("--") and s.startswith("-")

        has_required = any(is_required(p) for p in parameters)

        for p in parameters:
            has_short = any(is_short(x) for x in get_names(p))
            if has_short:
                break

        if has_required:
            table.add_column(justify="left", width=1, style="red bold")
        table.add_column(justify="left", no_wrap=True, style="cyan")
        if has_short:
            table.add_column(justify="left", no_wrap=True, style="green")
        table.add_column(justify="left")

        for parameter in parameters:
            if hide_var_positional and parameter.kind == parameter.VAR_POSITIONAL:
                continue

            hint, param = get_hint_parameter(parameter.annotation)
            options = get_names(parameter)
            options.extend(param.get_negatives(hint, *options))

            if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD):
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
            if param.help:
                help_components.append(param.help)
            if param.show_default and not is_required(parameter):
                help_components.append(rf"[dim]\[default: {parameter.default}][/dim]")
            if is_required(parameter):
                help_components.append(r"[red][dim]\[required][/dim][/red]")

            # populate row
            row_args = []
            if has_required:
                row_args.append("*" if is_required(parameter) else "")
            row_args.append(",".join(long_options) + " ")  # a little extra padding
            if has_short:
                row_args.append(",".join(short_options) + " ")  # a little extra padding
            row_args.append(" ".join(help_components))
            table.add_row(*row_args)

    # Add in special flags
    if app.version_flags:
        row_args = []
        if has_required:
            row_args.append("")

        row_args.append(",".join(app.version_flags) + " ")
        row_args.append("Show this message and exit.")
        table.add_row(*row_args)

    if app.help_flags:
        row_args = []
        if has_required:
            row_args.append("")
        row_args.append(",".join(app.help_flags) + " ")
        row_args.append(f"Print {app._name_derived} version and exit.")
        table.add_row(*row_args)

    if table.row_count == 0:
        return _silent

    return panel
