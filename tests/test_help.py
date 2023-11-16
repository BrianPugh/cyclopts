from textwrap import dedent

import pytest
from rich.console import Console
from typing_extensions import Annotated

from cyclopts import App, Parameter
from cyclopts.help import format_commands, format_doc, format_parameters, format_usage


@pytest.fixture
def console():
    return Console(width=70, force_terminal=True, no_color=True, highlight=False)


@pytest.fixture
def app():
    return App(name="app", help="App Help String Line 1.")


def test_help_format_usage_empty(app, console):
    with console.capture() as capture:
        console.print(format_usage(app, []))
    actual = capture.get()
    assert actual == "\x1b[1mUsage: app \x1b[0m\n\n"


def test_help_format_usage_command(app, console):
    @app.command
    def foo():
        pass

    with console.capture() as capture:
        console.print(format_usage(app, []))
    actual = capture.get()
    assert actual == "\x1b[1mUsage: app COMMAND \x1b[0m\n\n"


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
    app = App(name="foo")

    with console.capture() as capture:
        app.help_print(console=console)
    actual = capture.get()

    assert actual == "\x1b[1mUsage: foo \x1b[0m\n\n"


@pytest.mark.skip
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
        │ *  FOO,--foo  Docstring for foo.                                   │
        │ *  --bar      Docstring for bar.                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected
