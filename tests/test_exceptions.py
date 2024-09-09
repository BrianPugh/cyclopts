from textwrap import dedent
from typing import Annotated, Union

import pytest

from cyclopts import (
    ArgumentOrderError,
    CoercionError,
    InvalidCommandError,
    MissingArgumentError,
    MixedArgumentError,
    Parameter,
    ValidationError,
)


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


def test_exceptions_validation_error_cli_single_positional(app, console):
    def validator(type_, value):
        if value <= 0:
            raise ValueError("Value must be positive.")

    @app.command
    def foo(bar: Annotated[int, Parameter(validator=validator)]):
        pass

    with console.capture() as capture, pytest.raises(ValidationError):
        app("foo -2", console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value "-2" for BAR. Value must be positive.                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_validation_error_cli_single_keyword(app, console):
    def validator(type_, value):
        if value <= 0:
            raise ValueError("Value must be positive.")

    @app.command
    def foo(bar: Annotated[int, Parameter(validator=validator)]):
        pass

    with console.capture() as capture, pytest.raises(ValidationError):
        app("foo --bar -2", console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value -2 for --bar. Value must be positive.                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_validation_error_non_cli_single_keyword(app, console):
    # TODO
    pass


def test_exceptions_validation_error_cli_multi_positional(app, console):
    # TODO
    pass


def test_exceptions_validation_error_cli_multi_keyword(app, console):
    # TODO
    pass


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
        │ Invalid value for "--bar": unable to convert "fizz" into int.      │
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


def test_exceptions_argument_order_error_singular(app, console):
    @app.command
    def foo(a, b, c):
        pass

    with console.capture() as capture, pytest.raises(ArgumentOrderError):
        app("foo --b=5 1 2", console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Cannot specify token '2' positionally for parameter 'c' due to     │
        │ previously specified keyword '--b'. '--b' must either be passed    │
        │ positionally, or '2' must be passed as a keyword to '--c'.         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_argument_order_error_plural(app, console):
    @app.command
    def foo(a, b, c):
        pass

    with console.capture() as capture, pytest.raises(ArgumentOrderError):
        app("foo --a=1 --b=5 3", console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Cannot specify token '3' positionally for parameter 'c' due to     │
        │ previously specified keywords ['--a', '--b']. ['--a', '--b'] must  │
        │ either be passed positionally, or '3' must be passed as a keyword  │
        │ to '--c'.                                                          │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected
