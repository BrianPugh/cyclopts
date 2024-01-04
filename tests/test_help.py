import inspect
import sys
from enum import Enum
from textwrap import dedent
from typing import List, Literal, Optional, Union

import pytest

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import App, Group, Parameter
from cyclopts.help import (
    create_panel_table_commands,
    format_command_rows,
    format_doc,
    format_group_parameters,
    format_usage,
)


@pytest.fixture
def app():
    return App(
        name="app",
        help="App Help String Line 1.",
        version_flags=[],
        help_flags=[],
    )


def test_help_default_action(app, console):
    """No command should default to help."""
    with console.capture() as capture:
        app([], console=console)

    actual = capture.get()
    assert actual == ("Usage: app\n\nApp Help String Line 1.\n\n")


def test_help_default_help_flags(console):
    """Standard help flags."""
    app = App(name="app", help="App Help String Line 1.")
    with console.capture() as capture:
        app(["--help"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ --help,-h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_help_format_usage_empty(app, console):
    with console.capture() as capture:
        console.print(format_usage(app, []))
    actual = capture.get()
    assert actual == "Usage: app\n\n"


def test_help_format_usage_command(app, console):
    @app.command
    def foo():
        pass

    with console.capture() as capture:
        console.print(format_usage(app, []))
    actual = capture.get()
    assert actual == "Usage: app COMMAND\n\n"


def test_format_doc_function(app, console):
    def foo():
        """Foo Doc String Line 1.

        Foo Doc String Line 3.
        """

    with console.capture() as capture:
        console.print(format_doc(app, foo))

    actual = capture.get()
    assert actual == "Foo Doc String Line 1.\n\nFoo Doc String Line 3.\n\n"


def test_format_commands_docstring(app, console):
    @app.command
    def foo():
        """Docstring for foo.

        This should not be shown.
        """
        pass

    panel, table = create_panel_table_commands(title="Commands")
    with console.capture() as capture:
        for row in format_command_rows((app["foo"],)):
            table.add_row(*row)
        console.print(panel)

    actual = capture.get()
    assert actual == (
        "╭─ Commands ─────────────────────────────────────────────────────────╮\n"
        "│ foo  Docstring for foo.                                            │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_format_commands_explicit_help(app, console):
    @app.command(help="Docstring for foo.")
    def foo():
        """Should not be shown."""
        pass

    panel, table = create_panel_table_commands(title="Commands")
    with console.capture() as capture:
        for row in format_command_rows((app["foo"],)):
            table.add_row(*row)
        console.print(panel)

    actual = capture.get()
    assert actual == (
        "╭─ Commands ─────────────────────────────────────────────────────────╮\n"
        "│ foo  Docstring for foo.                                            │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_format_commands_explicit_name(app, console):
    @app.command(name="bar")
    def foo():
        """Docstring for bar.

        This should not be shown.
        """
        pass

    panel, table = create_panel_table_commands(title="Commands")
    with console.capture() as capture:
        for row in format_command_rows((app["bar"],)):
            table.add_row(*row)
        console.print(panel)

    actual = capture.get()
    assert actual == (
        "╭─ Commands ─────────────────────────────────────────────────────────╮\n"
        "│ bar  Docstring for bar.                                            │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_help_empty(console):
    app = App(name="foo", version_flags=[], help_flags=[])

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()

    assert actual == "Usage: foo\n\n"


def test_help_format_group_parameters(app, console):
    @app.command
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        bar: Annotated[str, Parameter(help="Docstring for bar.")],
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app,
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO,--foo  Docstring for foo. [required]                        │
        │ *  BAR,--bar  Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_short_name(app, console):
    @app.command
    def cmd(
        foo: Annotated[str, Parameter(name=["--foo", "-f"], help="Docstring for foo.")],
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO,--foo  -f  Docstring for foo. [required]                    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_from_docstring(app, console):
    @app.command
    def cmd(foo: str, bar: str):
        """

        Parameters
        ----------
        foo: str
            Docstring for foo.
        bar: str
            Docstring for bar.
        """
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO,--foo  Docstring for foo. [required]                        │
        │ *  BAR,--bar  Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_bool_flag(app, console):
    @app.command
    def cmd(
        foo: Annotated[bool, Parameter(help="Docstring for foo.")] = True,
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo,--no-foo  Docstring for foo. [default: True]             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_bool_flag_custom_negative(app, console):
    @app.command
    def cmd(
        foo: Annotated[bool, Parameter(negative="--yesnt-foo", help="Docstring for foo.")] = True,
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo,--yesnt-foo  Docstring for foo. [default: True]          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_list_flag(app, console):
    @app.command
    def cmd(
        foo: Annotated[Optional[List[int]], Parameter(help="Docstring for foo.")] = None,
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo,--empty-foo  Docstring for foo.                          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_defaults(app, console):
    @app.command
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")] = "fizz",
        bar: Annotated[str, Parameter(help="Docstring for bar.")] = "buzz",
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo  Docstring for foo. [default: fizz]                      │
        │ BAR,--bar  Docstring for bar. [default: buzz]                      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_defaults_no_show(app, console):
    @app.command
    def cmd(
        foo: Annotated[str, Parameter(show_default=False, help="Docstring for foo.")] = "fizz",
        bar: Annotated[str, Parameter(help="Docstring for bar.")] = "buzz",
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo  Docstring for foo.                                      │
        │ BAR,--bar  Docstring for bar. [default: buzz]                      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_no_show(app, console):
    @app.command
    def cmd(
        foo: Annotated[Literal["fizz", "buzz"], Parameter(show_choices=False, help="Docstring for foo.")] = "fizz",
        bar: Annotated[Literal["fizz", "buzz"], Parameter(help="Docstring for bar.")] = "buzz",
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo  Docstring for foo. [default: fizz]                      │
        │ BAR,--bar  Docstring for bar. [choices: fizz,buzz] [default: buzz] │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_literal_union(app, console):
    @app.command
    def cmd(
        foo: Annotated[
            Union[int, Literal["fizz", "buzz"], Literal["bar"]], Parameter(help="Docstring for foo.")
        ] = "fizz",
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo  Docstring for foo. [choices: fizz,buzz,bar] [default:   │
        │            fizz]                                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_choices_enum(app, console):
    class CompSciProblem(Enum):
        fizz = "bleep bloop blop"
        buzz = "blop bleep bloop"

    @app.command
    def cmd(
        foo: Annotated[CompSciProblem, Parameter(help="Docstring for foo.")] = CompSciProblem.fizz,
        bar: Annotated[CompSciProblem, Parameter(help="Docstring for bar.")] = CompSciProblem.buzz,
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo  Docstring for foo. [choices: fizz,buzz] [default: fizz] │
        │ BAR,--bar  Docstring for bar. [choices: fizz,buzz] [default: buzz] │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_group_parameters_env_var(app, console):
    @app.command
    def cmd(
        foo: Annotated[int, Parameter(env_var=["FOO", "BAR"], help="Docstring for foo.")] = 123,
    ):
        pass

    with console.capture() as capture:
        console.print(
            format_group_parameters(
                app["cmd"],
                Group("Parameters"),
                list(inspect.signature(cmd).parameters.values()),
            )
        )

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo  Docstring for foo. [env var: FOO BAR] [default: 123]    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_function(app, console):
    with console.capture() as capture:
        app.help_print(console=console)

    @app.command(help="Cmd help string.")
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        *,
        bar: Annotated[str, Parameter(help="Docstring for bar.")],
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app cmd [ARGS] [OPTIONS]

        Cmd help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO,--foo  Docstring for foo. [required]                        │
        │ *  --bar      Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_function_no_parse(app, console):
    with console.capture() as capture:
        app.help_print(console=console)

    @app.command(help="Cmd help string.")
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        *,
        bar: Annotated[str, Parameter(parse=False)],
    ):
        pass

    with console.capture() as capture:
        app.help_print(["cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app cmd [ARGS] [OPTIONS]

        Cmd help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO,--foo  Docstring for foo. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands(app, console):
    with console.capture() as capture:
        app.help_print(console=console)

    @app.command(help="Cmd1 help string.")
    def cmd1():
        pass

    @app.command(help="Cmd2 help string.")
    def cmd2():
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1  Cmd1 help string.                                            │
        │ cmd2  Cmd2 help string.                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_and_function(app, console):
    with console.capture() as capture:
        app.help_print(console=console)

    @app.command(help="Cmd1 help string.")
    def cmd1():
        pass

    @app.command(help="Cmd2 help string.")
    def cmd2():
        pass

    @app.default()
    def default(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        *,
        bar: Annotated[str, Parameter(help="Docstring for bar.")],
    ):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND [ARGS] [OPTIONS]

        App Help String Line 1.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO,--foo  Docstring for foo. [required]                        │
        │ *  --bar      Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1  Cmd1 help string.                                            │
        │ cmd2  Cmd2 help string.                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_plus_meta(app, console):
    app.version_flags = ["--version"]
    app.help_flags = ["--help", "-h"]

    @app.command(help="Cmd1 help string.")
    def cmd1():
        pass

    @app.meta.command(help="Meta cmd help string.")
    def meta_cmd():
        pass

    @app.command(help="Cmd2 help string.")
    def cmd2():
        pass

    @app.meta.default
    def main(
        *tokens: Annotated[str, Parameter(show=False)],
        hostname: Annotated[str, Parameter(help="Hostname to connect to.")],
    ):
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1.

        ╭─ Session Parameters ───────────────────────────────────────────────╮
        │ *  --hostname  Hostname to connect to. [required]                  │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1       Cmd1 help string.                                       │
        │ cmd2       Cmd2 help string.                                       │
        │ meta-cmd   Meta cmd help string.                                   │
        │ --help,-h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_plus_meta_short(app, console):
    app.help = None
    app.version_flags = ["--version"]
    app.help_flags = ["--help", "-h"]

    @app.command(help="Cmd1 help string.")
    def cmd1():
        pass

    @app.meta.command(help="Meta cmd help string.")
    def meta_cmd(a: int):
        """

        Parameters
        ----------
        a
            Some value.
        """
        pass

    @app.command(help="Cmd2 help string.")
    def cmd2():
        pass

    @app.meta.default
    def main(
        *tokens: str,
        hostname: Annotated[str, Parameter(name=["--hostname", "-n"], help="Hostname to connect to.")],
    ):
        """App Help String Line 1 from meta."""
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND

        App Help String Line 1 from meta.

        ╭─ Session Parameters ───────────────────────────────────────────────╮
        │ *  TOKENS          [required]                                      │
        │ *  --hostname  -n  Hostname to connect to. [required]              │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1       Cmd1 help string.                                       │
        │ cmd2       Cmd2 help string.                                       │
        │ meta-cmd   Meta cmd help string.                                   │
        │ --help,-h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected

    # Add in a default root app.
    @app.default
    def root_default_cmd(rdp):
        """Root Default Command Short Description.

        Parameters
        ----------
        rdp:
            RDP description.
        """
        pass

    with console.capture() as capture:
        app.help_print([], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app COMMAND [ARGS] [OPTIONS]

        Root Default Command Short Description.

        ╭─ Session Parameters ───────────────────────────────────────────────╮
        │ *  TOKENS          [required]                                      │
        │ *  --hostname  -n  Hostname to connect to. [required]              │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  RDP,--rdp  RDP description. [required]                          │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1       Cmd1 help string.                                       │
        │ cmd2       Cmd2 help string.                                       │
        │ meta-cmd   Meta cmd help string.                                   │
        │ --help,-h  Display this message and exit.                          │
        │ --version  Display application version.                            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected

    # Test that the meta command help parsing is correct.
    with console.capture() as capture:
        app.help_print(["meta-cmd"], console=console)

    actual = capture.get()
    expected = dedent(
        """\
        Usage: app meta-cmd [ARGS] [OPTIONS]

        Meta cmd help string.

        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  A,--a  Some value. [required]                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected
