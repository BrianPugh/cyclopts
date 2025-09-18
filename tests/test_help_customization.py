"""Test help customization via Group help_formatter."""

from textwrap import dedent
from typing import Annotated, Any

from rich.box import DOUBLE, SIMPLE, SQUARE
from rich.console import Console

from cyclopts import App, Group, Parameter
from cyclopts.annotations import get_hint_name
from cyclopts.help import ColumnSpec, DefaultFormatter, PanelSpec, TableSpec
from cyclopts.help.specs import ParameterDescriptionColumn


def _type_renderer(entry: Any) -> str:
    """Render the type field as a human-readable string."""
    type_annotation = entry.type
    if type_annotation is None:
        return ""
    return get_hint_name(type_annotation)


def test_group_custom_table_spec(console: Console):
    """Test that custom table_spec on Group is used."""
    custom_group = Group(
        "Custom Options",
        help="These are custom options.",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                show_header=True,
                border_style="blue",
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        verbose: Annotated[bool, Parameter(group=custom_group)] = False,
        config: Annotated[str, Parameter(group=custom_group)] = "default.cfg",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
            Usage: test_help_customization [ARGS] [OPTIONS]

            ╭─ Commands ─────────────────────────────────────────────────────────╮
            │ --help -h  Display this message and exit.                          │
            │ --version  Display application version.                            │
            ╰────────────────────────────────────────────────────────────────────╯
            ╭─ Custom Options ───────────────────────────────────────────────────╮
            │ These are custom options.                                          │
            │                                                                    │
            │ Option             Description                                     │
            │ VERBOSE --verbose  [default: False]                                │
            │   --no-verbose                                                     │
            │ CONFIG --config    [default: default.cfg]                          │
            ╰────────────────────────────────────────────────────────────────────╯
            """
    )
    assert actual == expected


def test_group_custom_panel_spec(console: Console):
    """Test that custom panel_spec on Group is used."""
    custom_group = Group(
        "Styled Options",
        help_formatter=DefaultFormatter(
            panel_spec=PanelSpec(
                box=DOUBLE,
                border_style="cyan",
                padding=(1, 2),
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        flag: Annotated[bool, Parameter(group=custom_group)] = False,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╔═ Styled Options ═══════════════════════════════════════════════════╗
        ║                                                                    ║
        ║  FLAG --flag --no-flag  [default: False]                           ║
        ║                                                                    ║
        ╚════════════════════════════════════════════════════════════════════╝
        """
    )
    assert actual == expected


def test_group_custom_columns(console: Console):
    """Test that custom columns can be specified via DefaultFormatter."""

    def names_renderer(entry):
        """Render names and shorts as a single string."""
        names_str = " ".join(entry.names) if entry.names else ""
        shorts_str = " ".join(entry.shorts) if entry.shorts else ""
        if names_str and shorts_str:
            return names_str + " " + shorts_str
        return names_str or shorts_str

    custom_columns = (
        ColumnSpec(renderer=names_renderer, style="green bold", header="Option"),
        ColumnSpec(renderer=_type_renderer, style="yellow", header="Type"),
        ParameterDescriptionColumn,
    )

    custom_group = Group(
        "Advanced Options",
        help_formatter=DefaultFormatter(
            column_specs=custom_columns,
            table_spec=TableSpec(show_header=True),
        ),
    )

    app = App()

    @app.default
    def main(
        threads: Annotated[int, Parameter(group=custom_group, help="Number of threads")] = 4,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Advanced Options ─────────────────────────────────────────────────╮
        │ Option             Type  Description                               │
        │ THREADS --threads  int   Number of threads [default: 4]            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_default_group_with_custom_spec(app, console):
    """Test that default groups can be created and then customized with specs."""
    # Create a default parameters group and then set its specs
    custom_params_group = Group.create_default_parameters()
    custom_params_group = Group(
        custom_params_group.name,
        sort_key=custom_params_group.sort_key,
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                show_lines=True,
                box=SQUARE,  # Need a box style for lines to appear
            ),
            panel_spec=PanelSpec(
                box=DOUBLE,
            ),
        ),
    )

    app.group_parameters = custom_params_group

    @app.default
    def main(verbose: bool = False):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╔═ Parameters ═══════════════════════════════════════════════════════╗
        ║ ┌───────────────────┬────────────────────────────────────────────┐ ║
        ║ │VERBOSE --verbose  │[default: False]                            │ ║
        ║ │  --no-verbose     │                                            │ ║
        ║ └───────────────────┴────────────────────────────────────────────┘ ║
        ╚════════════════════════════════════════════════════════════════════╝
        """
    )
    assert actual == expected


def test_command_group_with_custom_spec(console: Console):
    """Test that command groups can have custom specs."""
    # Create a default commands group and then customize it
    custom_commands_group = Group(
        "Commands",
        sort_key=Group.create_default_commands().sort_key,
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                padding=(0, 1),
            ),
        ),
    )

    app = App(group_commands=custom_commands_group)

    @app.command
    def foo():
        """Foo command."""
        pass

    @app.command
    def bar():
        """Bar command."""
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization COMMAND

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ bar        Bar command.                                            │
        │ foo        Foo command.                                            │
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_panel_spec_custom_title(console: Console):
    """Test that a custom title in panel_spec overrides the group name."""
    custom_group = Group(
        "Original Name",
        help_formatter=DefaultFormatter(
            panel_spec=PanelSpec(
                title="Custom Title",
                border_style="magenta",
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        option: Annotated[str, Parameter(group=custom_group)] = "default",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Custom Title ─────────────────────────────────────────────────────╮
        │ OPTION --option  [default: default]                                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_mixed_groups_with_different_specs(console: Console):
    """Test multiple groups each with their own custom specs."""
    required_group = Group(
        "Required",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                border_style="red",
            ),
        ),
    )

    optional_group = Group(
        "Optional",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                border_style="green",
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        name: Annotated[str, Parameter(group=required_group)],
        verbose: Annotated[bool, Parameter(group=optional_group)] = False,
        debug: Annotated[bool, Parameter(group=optional_group)] = False,
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Optional ─────────────────────────────────────────────────────────╮
        │ VERBOSE --verbose         [default: False]                         │
        │   --no-verbose                                                     │
        │ DEBUG --debug --no-debug  [default: False]                         │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Required ─────────────────────────────────────────────────────────╮
        │ *  NAME --name  [required]                                         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_table_show_lines_with_box(console: Console):
    """Test that lines appear between rows when both show_lines=True and box is set."""
    custom_group = Group(
        "Options",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                show_lines=True,
                box=SIMPLE,  # Need a box style for lines to appear
                border_style="green",
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        first: Annotated[str, Parameter(group=custom_group)] = "one",
        second: Annotated[str, Parameter(group=custom_group)] = "two",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Options ──────────────────────────────────────────────────────────╮
        │                                                                    │
        │  FIRST --first     [default: one]                                  │
        │                                                                    │
        │  SECOND --second   [default: two]                                  │
        │                                                                    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_table_headers_with_default_columns(console: Console):
    """Test that default columns now have headers that show when show_header=True."""
    custom_group = Group(
        "Config",
        help_formatter=DefaultFormatter(
            table_spec=TableSpec(
                show_header=True,  # Headers should now show with default columns
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        param: Annotated[str, Parameter(group=custom_group)] = "value",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Config ───────────────────────────────────────────────────────────╮
        │ Option         Description                                         │
        │ PARAM --param  [default: value]                                    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_table_headers_suppressed_when_all_empty(console: Console):
    """Test that headers are suppressed when all column headers are empty strings."""
    from cyclopts.help.specs import parameter_description_renderer

    # Create columns with explicitly empty headers
    custom_columns = (
        ColumnSpec(renderer=lambda entry: " ".join(entry.names) if entry.names else "", header="", style="cyan"),
        ColumnSpec(renderer=parameter_description_renderer, header=""),
    )

    custom_group = Group(
        "Settings",
        help_formatter=DefaultFormatter(
            column_specs=custom_columns,
            table_spec=TableSpec(
                show_header=True,  # Even with this True, headers shouldn't show if all are empty
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        setting: Annotated[str, Parameter(group=custom_group, help="A configuration setting")] = "default",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Settings ─────────────────────────────────────────────────────────╮
        │ SETTING --setting  A configuration setting [default: default]      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_table_headers_with_non_empty_headers(console: Console):
    """Test that headers appear when column headers have text."""

    def names_renderer(entry):
        """Render names and shorts as a single string."""
        names_str = " ".join(entry.names) if entry.names else ""
        shorts_str = " ".join(entry.shorts) if entry.shorts else ""
        if names_str and shorts_str:
            return names_str + " " + shorts_str
        return names_str or shorts_str

    custom_columns = (
        ColumnSpec(renderer=names_renderer, header="Option", style="cyan"),
        ParameterDescriptionColumn,
    )

    custom_group = Group(
        "Settings",
        help_formatter=DefaultFormatter(
            column_specs=custom_columns,
            table_spec=TableSpec(
                show_header=True,
            ),
        ),
    )

    app = App()

    @app.default
    def main(
        setting: Annotated[str, Parameter(group=custom_group, help="A configuration setting")] = "default",
    ):
        pass

    with console.capture() as capture:
        app.help_print(console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: test_help_customization [ARGS] [OPTIONS]

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help -h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Settings ─────────────────────────────────────────────────────────╮
        │ Option             Description                                     │
        │ SETTING --setting  A configuration setting [default: default]      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected
