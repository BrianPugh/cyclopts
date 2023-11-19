from textwrap import dedent
from typing import List, Optional

import pytest
from typing_extensions import Annotated

from cyclopts import App, Parameter
from cyclopts.help import format_commands, format_doc, format_parameters, format_usage


@pytest.fixture
def app():
    return App(
        name="app",
        help="App Help String Line 1.",
        version_flags=[],
        help_flags=[],
    )


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

    with console.capture() as capture:
        console.print(format_commands(app, "Commands"))

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

    with console.capture() as capture:
        console.print(format_commands(app, "Commands"))

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

    with console.capture() as capture:
        console.print(format_commands(app, "Commands"))

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


def test_help_format_parameters(app, console):
    @app.command
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")],
        bar: Annotated[str, Parameter(help="Docstring for bar.")],
    ):
        pass

    with console.capture() as capture:
        console.print(format_parameters(app["cmd"], app.help_title_parameters))

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


def test_help_format_parameters_short_name(app, console):
    @app.command
    def cmd(
        foo: Annotated[str, Parameter(name=["--foo", "-f"], help="Docstring for foo.")],
    ):
        pass

    with console.capture() as capture:
        console.print(format_parameters(app["cmd"], app.help_title_parameters))

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO,--foo  -f  Docstring for foo. [required]                    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_parameters_bool_flag(app, console):
    @app.command
    def cmd(
        foo: Annotated[bool, Parameter(help="Docstring for foo.")] = True,
    ):
        pass

    with console.capture() as capture:
        console.print(format_parameters(app["cmd"], app.help_title_parameters))

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo,--no-foo  Docstring for foo. [default: True]             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_parameters_bool_flag_custom_negative(app, console):
    @app.command
    def cmd(
        foo: Annotated[bool, Parameter(negative="--yesnt-foo", help="Docstring for foo.")] = True,
    ):
        pass

    with console.capture() as capture:
        console.print(format_parameters(app["cmd"], app.help_title_parameters))

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo,--yesnt-foo  Docstring for foo. [default: True]          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_parameters_list_flag(app, console):
    @app.command
    def cmd(
        foo: Annotated[Optional[List[int]], Parameter(help="Docstring for foo.")] = None,
    ):
        pass

    with console.capture() as capture:
        console.print(format_parameters(app["cmd"], app.help_title_parameters))

    actual = capture.get()
    expected = dedent(
        """\
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ FOO,--foo,--empty-foo  Docstring for foo. [default: None]          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_format_parameters_defaults(app, console):
    @app.command
    def cmd(
        foo: Annotated[str, Parameter(help="Docstring for foo.")] = "fizz",
        bar: Annotated[str, Parameter(help="Docstring for bar.")] = "buzz",
    ):
        pass

    with console.capture() as capture:
        console.print(format_parameters(app["cmd"], app.help_title_parameters))

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


def test_help_format_parameters_defaults_no_show(app, console):
    @app.command
    def cmd(
        foo: Annotated[str, Parameter(show_default=False, help="Docstring for foo.")] = "fizz",
        bar: Annotated[str, Parameter(help="Docstring for bar.")] = "buzz",
    ):
        pass

    with console.capture() as capture:
        console.print(format_parameters(app["cmd"], app.help_title_parameters))

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

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ cmd1  Cmd1 help string.                                            │
        │ cmd2  Cmd2 help string.                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ *  FOO,--foo  Docstring for foo. [required]                        │
        │ *  --bar      Docstring for bar. [required]                        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_help_print_commands_plus_meta(app, console):
    app.version_flags = ["--version"]
    app.help_flags = ["--help", "-h"]

    with console.capture() as capture:
        app.help_print(console=console)

    @app.command(help="Cmd1 help string.")
    def cmd1():
        pass

    @app.command(help="Cmd2 help string.")
    def cmd2():
        pass

    @app.meta.default
    def main(*tokens, hostname: Annotated[str, Parameter(help="Hostname to connect to.")]):
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
        │ cmd1  Cmd1 help string.                                            │
        │ cmd2  Cmd2 help string.                                            │
        ╰────────────────────────────────────────────────────────────────────╯
        ╭─ Parameters ───────────────────────────────────────────────────────╮
        │ --version  Show this message and exit.                             │
        │ --help,-h  Print app version and exit.                             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected
