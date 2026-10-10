from textwrap import dedent
from typing import Annotated

import pytest

from cyclopts import App, CycloptsError, Parameter
from cyclopts.exceptions import MissingArgumentError, UnknownCommandError


@pytest.fixture
def mock_get_function_info(mocker):
    mocker.patch("cyclopts.exceptions._get_function_info", return_value=("FILENAME", 100))


def test_runtime_exception_not_enough_tokens(app, console, mock_get_function_info):
    @app.default
    def foo(a: tuple[int, int, int]):
        pass

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["1", "2"], exit_on_error=False, error_console=console)

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        "│ Parameter --a requires 3 positional arguments. Only got 2.         │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["1", "2"], exit_on_error=False, error_console=console, verbose=True)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ MissingArgumentError                                               │
        │ Function defined in file "FILENAME", line 100:                     │
        │     foo(a: tuple[int, int, int])                                   │
        │ Root Input Tokens: ['1', '2']                                      │
        │ Parameter --a requires 3 positional arguments. Only got 2.         │
        │ Parsed: ['1', '2'].                                                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


def test_runtime_exception_missing_parameter(app, console):
    @app.default
    def foo(a, b, c):
        pass

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["1", "2"], exit_on_error=False, error_console=console)

    actual = capture.get()
    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        "│ Parameter --c requires an argument.                                │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_runtime_exception_bad_command(app, console):
    with console.capture() as capture, pytest.raises(UnknownCommandError):
        app(["bad-command", "123"], exit_on_error=False, error_console=console)

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
        app(["bad-command", "123"], exit_on_error=False, error_console=console)

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

    with console.capture() as capture, pytest.raises(UnknownCommandError):
        app(["bad-command", "123"], exit_on_error=False, error_console=console)

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
        app(["cmd", "123"], exit_on_error=False, error_console=console)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Unknown command "cmd". Did you mean "cmd9"? Available commands:    │
        │ cmd1, cmd2, cmd3, cmd4, cmd5, cmd6, cmd7, cmd8, ...                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


@pytest.fixture
def users_app(app):
    app.command(users := App(name="users"))

    @users.command
    def add():
        pass

    return app


@pytest.mark.parametrize("cmd", ["users ad --help", "users ad -h", "users --help ad", "--help users ad"])
def test_runtime_exception_bad_command_with_help(users_app, console, cmd):
    with console.capture() as capture, pytest.raises(UnknownCommandError):
        users_app(cmd, exit_on_error=False, error_console=console)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Unknown command "ad". Did you mean "add"? Available commands: add. │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


def test_runtime_exception_bad_root_command_with_help(users_app, console):
    with pytest.raises(UnknownCommandError):
        users_app("--help userz", exit_on_error=False, error_console=console)


@pytest.mark.parametrize("cmd", ["--help users", "users --help", "users add --help", "users --verbose --help"])
def test_help_with_valid_command(users_app, console, cmd):
    with console.capture() as capture:
        users_app(cmd, exit_on_error=False, console=console, error_console=console)

    assert "Usage:" in capture.get()


def test_runtime_exception_bad_command_with_help_meta(users_app, console):
    @users_app.meta.default
    def meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
        users_app(tokens)

    with pytest.raises(UnknownCommandError):
        users_app.meta("users ad --help", exit_on_error=False, error_console=console)


def test_runtime_exception_bad_parameter_recommend(app, console):
    @app.command
    def some_command(*, foo: int):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(["some-command", "--boo", "123"], exit_on_error=False, error_console=console)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "some-command" parameter --foo requires an argument. Did   │
        │ you mean --foo instead of --boo?                                   │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


def test_runtime_exception_repeat_arguments(app, console):
    @app.default
    def foo(a):
        pass

    with console.capture() as capture, pytest.raises(CycloptsError):
        app(["--a=1", "--a=2"], exit_on_error=False, error_console=console)

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

    When a tuple requires more tokens than provided, MissingArgumentError should
    be raised with a clear message about how many arguments are required.
    """

    @app.default
    def main(
        *,
        network_delay: tuple[int, int] | None = None,
    ):
        pass

    # tuple[int, int] needs 2 tokens but only 1 was provided
    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app(["--network-delay", "1"], exit_on_error=False, error_console=console)

    actual = capture.get()
    assert actual == dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Parameter --network-delay requires 2 positional arguments. Only    │
        │ got 1.                                                             │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
