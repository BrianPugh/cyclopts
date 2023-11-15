import pytest
from rich.console import Console

from cyclopts import App, Parameter
from cyclopts.help import format_commands, format_doc, format_parameters, format_usage


@pytest.fixture
def console():
    return Console(width=70)


def test_help_format_usage_empty(console):
    print("meow")
    with console.capture() as capture:
        console.print(
            format_usage(
                "foo",
                [],
                command=False,
                options=False,
                args=False,  # TODO
            )
        )
    str_output = capture.get()
    assert str_output == "\x1b[1mUsage: foo \x1b[0m\n\n"


def test_help_empty(console):
    app = App(name="foo")

    with console.capture() as capture:
        app.help_print(console=console)
    str_output = capture.get()

    print(str_output, end="")
    assert str_output == "\x1b[1mUsage: foo [OPTIONS] \x1b[0m\n\n"
