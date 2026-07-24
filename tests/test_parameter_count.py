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


@pytest.mark.parametrize(
    "tokens,expected",
    [
        ("--verbose=3", 3),
        ("-v=3", 3),
        ("--verbose=0", 0),
    ],
)
def test_count_equals_value(app, assert_parse_args, tokens, expected):
    """An attached ``=value`` explicitly sets the count."""

    def cmd(verbose: Annotated[int, Parameter(name=("--verbose", "-v"), count=True)] = 0):
        pass

    app.default(cmd)
    assert_parse_args(cmd, tokens, expected)


@pytest.mark.parametrize(
    "tokens",
    [
        "-v --verbose=2",
        "--verbose=2 -v",
        "-vv --verbose=2",
        "--verbose=2 --verbose=3",
    ],
)
def test_count_equals_value_mixed_with_repeats(app, tokens):
    """An explicit ``=value`` must be the flag's only occurrence.

    ``=`` reads as assignment; silently summing it with repeats (or another
    assignment) would surprise, so mixing raises instead.
    """
    from cyclopts.exceptions import RepeatArgumentError

    def cmd(verbose: Annotated[int, Parameter(name=("--verbose", "-v"), count=True)] = 0):
        pass

    app.default(cmd)
    with pytest.raises(RepeatArgumentError):
        app.parse_args(tokens, exit_on_error=False)


def test_count_equals_value_mixed_error_message(app):
    """The mixed-occurrence error renders ONLY the count-specific message.

    Pins the ``RepeatArgumentError._segments`` msg-override fix: without it the
    custom message and the stock "specified multiple times" text rendered
    concatenated.
    """
    from cyclopts.exceptions import RepeatArgumentError

    def cmd(verbose: Annotated[int, Parameter(name=("--verbose", "-v"), count=True)] = 0):
        pass

    app.default(cmd)
    with pytest.raises(RepeatArgumentError) as exc_info:
        app.parse_args("-v --verbose=2", exit_on_error=False)
    message = str(exc_info.value)
    assert '"--verbose=2" sets the count explicitly' in message
    assert "specified multiple times" not in message


def test_count_allow_repeating_true_still_rejects_equals_mix(app):
    """``allow_repeating=True`` does not exempt an explicit ``=value`` from exclusivity."""
    from cyclopts.exceptions import RepeatArgumentError

    def cmd(
        verbose: Annotated[int, Parameter(name=("--verbose", "-v"), count=True, allow_repeating=True)] = 0,
    ):
        pass

    app.default(cmd)
    with pytest.raises(RepeatArgumentError):
        app.parse_args("-v --verbose=2", exit_on_error=False)


def test_count_allow_repeating_false_rejects_bare_repeats(app, assert_parse_args):
    """``allow_repeating=False`` still forbids plain repeats of a count flag."""
    from cyclopts.exceptions import RepeatArgumentError

    def cmd(
        verbose: Annotated[int, Parameter(name=("--verbose", "-v"), count=True, allow_repeating=False)] = 0,
    ):
        pass

    app.default(cmd)
    assert_parse_args(cmd, "-v", 1)
    with pytest.raises(RepeatArgumentError):
        app.parse_args("-v -v", exit_on_error=False)


@pytest.mark.parametrize("value", ["garbage", "true", "", "1.5", "2.0", "0x2", "-1"])
def test_count_equals_value_invalid(app, value):
    """A non-decimal-int or negative ``=value`` raises instead of being silently discarded.

    Fractional and negative values are rejected rather than rounded/honored: a
    count is a number of occurrences, so ``--verbose=1.5`` and ``--verbose=-1``
    are treated as user errors.
    """
    from cyclopts.exceptions import CoercionError

    def cmd(verbose: Annotated[int, Parameter(name=("--verbose", "-v"), count=True)] = 0):
        pass

    app.default(cmd)
    with pytest.raises(CoercionError):
        app.parse_args(f"--verbose={value}", exit_on_error=False)


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
