from dataclasses import dataclass
from textwrap import dedent
from typing import Annotated

import pytest

from cyclopts import (
    Argument,
    ArgumentOrderError,
    CoercionError,
    MissingArgumentError,
    MixedArgumentError,
    Parameter,
    Token,
    UnknownCommandError,
    ValidationError,
)


def positive_validator(type_, value):
    if value <= 0:
        # Seeing if we can translate a ValueError into a ValidationError as helpfully as possible.
        raise ValueError("Value must be positive.")


def multi_positive_validator(type_, values):
    for value in values:
        if value <= 0:
            raise ValueError("Value must be positive.")


def test_exceptions_missing_argument_single(app, console):
    @app.command
    def foo(bar: int):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app("foo", error_console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "--bar" requires an argument.              │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_missing_argument_flag(app, console):
    @app.command
    def foo(bar: bool):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app("foo", error_console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "--bar" flag required.                     │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_missing_argument_with_short_flag(app, console):
    """Error message should reference the flag actually used, not the canonical name."""

    @app.command
    def foo(option: Annotated[int, Parameter(alias="-o")]):
        pass

    with console.capture() as capture, pytest.raises(MissingArgumentError):
        app("foo -o1", error_console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Command "foo" parameter "-o" requires an argument.                 │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_validation_error_cli_single_positional(app, console):
    argument = Argument(
        hint=int,
        parameter=Parameter(name=("--bar",), validator=positive_validator),
        tokens=[
            Token(keyword=None, value="-2", source="cli"),
        ],
    )
    with pytest.raises(ValidationError) as e:
        argument.convert_and_validate()

    expected = dedent(
        """
        ValidationError
        Invalid value "-2" for "BAR". Value must be positive.
        """
    ).strip()
    assert str(e.value) == expected


def test_exceptions_validation_error_cli_single_keyword(app, console):
    argument = Argument(
        hint=int,
        parameter=Parameter(name=("--bar",), validator=positive_validator),
        tokens=[
            Token(keyword="--bar", value="-2", source="cli"),
        ],
    )
    with pytest.raises(ValidationError) as e:
        argument.convert_and_validate()

    expected = dedent(
        """
        ValidationError
        Invalid value "-2" for "--bar". Value must be positive.
        """
    ).strip()
    assert str(e.value) == expected


def test_exceptions_validation_error_class(app, console):
    """Double checks that error message is appropriately handled for class validators.

    https://github.com/BrianPugh/cyclopts/issues/432
    """

    def v(type_, value):
        raise ValueError("My custom message.")

    @Parameter(validator=v)
    @dataclass
    class Movie:
        title: str
        year: int

    @app.command
    def add(movie: Movie):
        pass

    with pytest.raises(ValidationError) as e:
        app("add foo 2020", exit_on_error=False)

    expected = """My custom message."""
    assert str(e.value) == expected


def test_exceptions_validation_error_non_cli_single_keyword(app, console):
    argument = Argument(
        hint=int,
        parameter=Parameter(name=("--bar",), validator=positive_validator),
        tokens=[
            Token(value="-2", source="test"),
        ],
    )
    with pytest.raises(ValidationError) as e:
        argument.convert_and_validate()

    expected = dedent(
        """
        ValidationError
        Invalid value "-2" for "BAR" provided by "test". Value must be positive.
        """
    ).strip()
    assert str(e.value) == expected


def test_exceptions_validation_error_cli_multi_positional(app, console):
    argument = Argument(
        hint=tuple[int, int],
        parameter=Parameter(name=("--bar",), validator=multi_positive_validator),
        tokens=[
            Token(keyword=None, value="100", source="cli"),
            Token(keyword=None, value="-2", source="cli"),
        ],
    )
    with pytest.raises(ValidationError) as e:
        argument.convert_and_validate()

    expected = dedent(
        """
        ValidationError
        Invalid value "(100, -2)" for "BAR". Value must be positive.
        """
    ).strip()
    assert str(e.value) == expected


def test_exceptions_validation_error_cli_multi_keyword(app, console):
    argument = Argument(
        hint=tuple[int, int],
        parameter=Parameter(name=("--bar",), validator=multi_positive_validator),
        tokens=[
            Token(keyword="--bar", value="100", source="cli"),
            Token(keyword="--bar", value="-2", source="cli"),
        ],
    )
    with pytest.raises(ValidationError) as e:
        argument.convert_and_validate()

    expected = dedent(
        """
        ValidationError
        Invalid value "(100, -2)" for "--bar". Value must be positive.
        """
    ).strip()
    assert str(e.value) == expected


def test_exceptions_coercion_error_from_positional_cli(app, console):
    @app.command
    def foo(bar: int):
        pass

    with console.capture() as capture, pytest.raises(CoercionError):
        app("foo fizz", error_console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value for "BAR": unable to convert "fizz" into int.        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_coercion_error_from_keyword_cli(app, console):
    @app.command
    def foo(bar: Annotated[int, Parameter(name=("--bar", "-b"))]):
        pass

    with console.capture() as capture, pytest.raises(CoercionError):
        app("foo -b fizz", error_console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value for "-b": unable to convert "fizz" into int.         │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_coercion_error_verbose(app, console):
    @app.command
    def foo(bar: int):
        pass

    with console.capture() as capture, pytest.raises(CoercionError):
        app("foo fizz", error_console=console, exit_on_error=False, verbose=True)

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
        │ Invalid value for "BAR": unable to convert "fizz" into int.        │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )
    assert actual.endswith(expected)


def test_exceptions_mixed_argument_error(app, console):
    @app.default
    def foo(bar: int | dict):
        pass

    with console.capture() as capture, pytest.raises(MixedArgumentError):
        app("--bar 5 --bar.baz fizz", error_console=console, exit_on_error=False)

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

    with console.capture() as capture, pytest.raises(UnknownCommandError):
        app("bar fizz", error_console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Unknown command "bar". Available commands: foo.                    │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_exceptions_argument_order_error_singular(app, console):
    @app.command
    def foo(a, b, c):
        pass

    with console.capture() as capture, pytest.raises(ArgumentOrderError):
        app("foo --b=5 1 2", error_console=console, exit_on_error=False)

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
        app("foo --a=1 --b=5 3", error_console=console, exit_on_error=False)

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
