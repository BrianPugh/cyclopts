from textwrap import dedent
from typing import Union

import pytest

from cyclopts.exceptions import CoercionError, InvalidCommandError, MissingArgumentError, MixedArgumentError


def test_exceptions_missing_argument(app, console):
    @app.command
    def foo(bar: int):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app("foo", console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "--bar" requires an argument.              │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_coercion_error(app, console):
    @app.command
    def foo(bar: int):
        pass

    with console.capture() as capture, pytest.raises(CoercionError):
        app("foo fizz", console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value for "--bar": unable to convert "fizz" into int.      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_coercion_error_verbose(app, console):
    @app.command
    def foo(bar: int):
        pass

    with console.capture() as capture, pytest.raises(CoercionError):
        app("foo fizz", console=console, exit_on_error=False, verbose=True)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ CoercionError                                                      │
        """
    )
    assert actual.startswith(expected)

    expected = dedent(
        """\
        │     foo(bar: int)                                                  │
        │ Root Input Tokens: ['foo', 'fizz']                                 │
        │ Error converting value "fizz" to <class 'int'> for "--bar".        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual.endswith(expected)


def test_exceptions_mixed_argument_error(app, console):
    @app.default
    def foo(bar: Union[int, dict]):
        pass

    with console.capture() as capture, pytest.raises(MixedArgumentError):
        app("--bar 5 --bar.baz fizz", console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Cannot supply keyword & non-keyword arguments to "--bar".          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual == expected


def test_exceptions_unknown_command(app, console):
    @app.command
    def foo(bar: int):
        pass

    with console.capture() as capture, pytest.raises(InvalidCommandError):
        app("bar fizz", console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Unable to interpret valid command from "bar".                      │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected
