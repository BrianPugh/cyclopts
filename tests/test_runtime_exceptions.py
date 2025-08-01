from textwrap import dedent
from typing import Optional, Tuple

import pytest

from cyclopts import CycloptsError
from cyclopts.exceptions import MissingArgumentError, UnknownCommandError


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
    with console.capture() as capture, pytest.raises(UnknownCommandError):
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

    with console.capture() as capture, pytest.raises(UnknownCommandError):
        app(["bad-command", "123"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Unknown command "bad-command". Did you mean "mad-command"?         │
        │ Available commands: mad-command.                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


def test_runtime_exception_bad_command_recommend_no_show(app, console):
    """If a command is hidden, do not show recommendations for it."""

    @app.command(show=False)
    def mad_command():  # "mad-command" should not be recommended, and not show up as an available command.
        pass

    @app.command
    def other_command():
        pass

    with console.capture() as capture, pytest.raises(InvalidCommandError):
        app(["bad-command", "123"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Unknown command "bad-command". Did you mean "other-command"?       │
        │ Available commands: other-command.                                 │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


def test_runtime_exception_bad_command_list_ellipsis(app, console):
    def cmd():
        pass

    app.command(name="cmd1")(cmd)
    app.command(name="cmd2")(cmd)
    app.command(name="cmd3")(cmd)
    app.command(name="cmd4")(cmd)
    app.command(name="cmd5")(cmd)
    app.command(name="cmd6")(cmd)
    app.command(name="cmd7")(cmd)
    app.command(name="cmd8")(cmd)
    app.command(name="cmd9")(cmd)

    with console.capture() as capture, pytest.raises(UnknownCommandError):
        app(["cmd", "123"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Unknown command "cmd". Did you mean "cmd9"? Available commands:    │
        │ cmd1, cmd2, cmd3, cmd4, cmd5, cmd6, cmd7, cmd8, ...                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
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


def test_runtime_exception_missing_tuple(app, console):
    """
    A bug was found where the "Did you mean" would be inappropriately displayed
    when insufficient tokens were supplied to a tuple type.

    https://github.com/BrianPugh/cyclopts/issues/443
    """

    @app.default
    def main(
        *,
        network_delay: Optional[Tuple[int, int]] = None,
    ):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(["--network-delay", "1"], exit_on_error=False, console=console)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Parameter "--network-delay" requires 2 positional arguments. Only  │
        │ got 1.                                                             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
