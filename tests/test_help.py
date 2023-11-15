import pytest
from rich.console import Console

from cyclopts import App, Parameter
from cyclopts.help import format_commands, format_doc, format_parameters, format_usage


@pytest.fixture
def console():
    return Console(width=70)


@pytest.fixture
def app():
    return App(help="App Help String Line 1.")


def test_help_format_usage_empty(console):
    with console.capture() as capture:
        console.print(
            format_usage(
                "foo",
                [],
                command=False,
                options=False,
                args=False,
            )
        )
    str_output = capture.get()
    assert str_output == "\x1b[1mUsage: foo \x1b[0m\n\n"


def test_help_format_usage_command(console):
    with console.capture() as capture:
        console.print(
            format_usage(
                "foo",
                [],
                command=True,
                options=False,
                args=False,
            )
        )
    str_output = capture.get()
    assert str_output == "\x1b[1mUsage: foo COMMAND \x1b[0m\n\n"


def test_format_doc_function(app, console):
    def foo():
        """Foo Doc String Line 1.

        Foo Doc String Line 3.
        """

    with console.capture() as capture:
        console.print(format_doc(app, foo))

    str_output = capture.get()
    assert str_output == "\x1b[39mFoo Doc String Line 1.\x1b[0m\n\nFoo Doc String Line 3.\n\n"


def test_format_commands_docstring(app, console):
    @app.command
    def foo():
        """Docstring for Foo.

        This should not be shown.
        """
        pass

    with console.capture() as capture:
        console.print(format_commands(app))

    str_output = capture.get()
    assert str_output == (
        "╭─ Commands ─────────────────────────────────────────────────────────╮\n"
        "│ \x1b[36mfoo \x1b[0m\x1b[36m \x1b[0mDocstring for Foo.                                            │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_help_empty(console):
    app = App(name="foo")

    with console.capture() as capture:
        app.help_print(console=console)
    str_output = capture.get()

    print(str_output, end="")
    assert str_output == "\x1b[1mUsage: foo [OPTIONS] \x1b[0m\n\n"
