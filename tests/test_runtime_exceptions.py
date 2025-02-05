from textwrap import dedent
from typing import Tuple

import pytest

from cyclopts import CycloptsError
from cyclopts.exceptions import MissingArgumentError


@pytest.fixture
def mock_get_function_info(mocker):
    mocker.patch("cyclopts.exceptions._get_function_info", return_value=("FILENAME", 100))


def test_runtime_exception_not_enough_tokens(app, console, mock_get_function_info):
    @app.default
    def foo(a: Tuple[int, int, int]):
        pass

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["1", "2"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        '│ Parameter "--a" requires 3 positional arguments. Only got 2.       │\n'
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["1", "2"], exit_on_error=False, console=console, verbose=True)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ MissingArgumentError                                               │
        │ Function defined in file "FILENAME", line 100:                     │
        │     foo(a: Tuple[int, int, int])                                   │
        │ Root Input Tokens: ['1', '2']                                      │
        │ Parameter "--a" requires 3 positional arguments. Only got 2.       │
        │ Parsed: ['1', '2'].                                                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


def test_runtime_exception_missing_parameter(app, console):
    @app.default
    def foo(a, b, c):
        pass

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["1", "2"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        '│ Parameter "--c" requires an argument.                              │\n'
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_runtime_exception_bad_command(app, console):
    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["bad-command", "123"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        '│ Unknown command "bad-command".                                     │\n'
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_runtime_exception_bad_command_recommend(app, console):
    @app.command
    def mad_command():
        pass

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["bad-command", "123"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        '│ Unknown command "bad-command". Did you mean "mad-command"?         │\n'
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_runtime_exception_bad_parameter_recommend(app, console):
    @app.command
    def some_command(*, foo: int):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(["some-command", "--boo", "123"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "some-command" parameter "--foo" requires an argument. Did │
        │ you mean "--foo" instead of "--boo"?                               │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


def test_runtime_exception_repeat_arguments(app, console):
    @app.default
    def foo(a):
        pass

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["--a=1", "--a=2"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        "│ Parameter --a specified multiple times.                            │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )
