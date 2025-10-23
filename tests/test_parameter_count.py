"""Tests for Parameter(count=True) functionality."""

from typing import Annotated, Optional

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import MissingArgumentError, UnknownOptionError


@pytest.mark.parametrize(
    "tokens,expected",
    [
        ("", 0),
        ("-v", 1),
        ("-vv", 2),
        ("-vvv", 3),
        ("-v -v -v", 3),
        ("-v --verbose -v", 3),
        ("--verbose", 1),
        ("--verbose --verbose", 2),
        ("-v --verbose -vv --verbose", 5),
    ],
)
def test_count_various_inputs(app, assert_parse_args, tokens, expected):
    """Test count with various flag combinations."""

    def cmd(verbose: Annotated[int, Parameter(name=("--verbose", "-v"), count=True)] = 0):
        pass

    app.default(cmd)
    assert_parse_args(cmd, tokens, expected)


def test_count_negative_disabled(app):
    """Ensure --no-verbose is NOT generated."""

    def cmd(verbose: Annotated[int, Parameter(name="--verbose", count=True)] = 0):
        pass

    app.default(cmd)
    with pytest.raises(UnknownOptionError):
        app.parse_args("--no-verbose", exit_on_error=False)


@pytest.mark.parametrize(
    "type_hint",
    [str, bool, list, dict],
)
def test_count_wrong_type_error(app, type_hint):
    """count=True with non-int type should error."""

    def cmd(verbose: Annotated[type_hint, Parameter(count=True)]):  # pyright: ignore[reportInvalidTypeForm]
        pass

    app.default(cmd)
    with pytest.raises(ValueError, match="requires an int type hint"):
        app.parse_args("", exit_on_error=False)


def test_count_optional_int(app, assert_parse_args):
    """count=True with Optional[int] should work."""

    def cmd(verbose: Annotated[Optional[int], Parameter(name="-v", count=True)] = 0):
        pass

    app.default(cmd)
    assert_parse_args(cmd, "-vv", 2)


def test_count_multiple_parameters(app, assert_parse_args):
    """Multiple count parameters in same command."""

    def cmd(
        verbose: Annotated[int, Parameter(name="-v", count=True)] = 0,
        quiet: Annotated[int, Parameter(name="-q", count=True)] = 0,
    ):
        pass

    app.default(cmd)
    assert_parse_args(cmd, "", 0, 0)
    assert_parse_args(cmd, "-vvv", 3, 0)
    assert_parse_args(cmd, "-qq", 0, 2)
    assert_parse_args(cmd, "-vv -qqq", 2, 3)


def test_count_with_other_parameters(app, assert_parse_args):
    """Count flag mixed with regular parameters."""

    def cmd(
        verbose: Annotated[int, Parameter(name="-v", count=True)] = 0,
        output: str = "default",
    ):
        pass

    app.default(cmd)
    assert_parse_args(cmd, "-vv --output test.txt", 2, "test.txt")
    assert_parse_args(cmd, "--output foo -vvv", 3, "foo")


def test_count_no_default(app):
    """Count without explicit default should be required."""

    def cmd(verbose: Annotated[int, Parameter(name="-v", count=True)]):
        pass

    app.default(cmd)
    with pytest.raises(MissingArgumentError):
        app.parse_args("", exit_on_error=False)


def test_count_help_text(app, console):
    """Verify help text includes user-provided description."""

    def cmd(verbose: Annotated[int, Parameter(name=("-v", "--verbose"), count=True, help="Increase verbosity")] = 0):
        """Command with count flag."""
        pass

    app.default(cmd)

    with console.capture() as capture:
        app.help_print([], console=console)
    help_text = capture.get()

    assert "increase verbosity" in help_text.lower()
    assert "verbose" in help_text.lower()
