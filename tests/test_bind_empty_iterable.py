import textwrap
from io import StringIO
from typing import Annotated

import pytest
from rich.console import Console

from cyclopts import CycloptsPanel, Parameter
from cyclopts.exceptions import ConsumeMultipleError, MissingArgumentError


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("", None),
        ("--empty-my-list", []),
        ("--empty-my-list=True", []),
        ("--empty-my-list=False", None),
    ],
)
def test_optional_list_empty_flag_default(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_list: list[int] | None = None):
        pass

    if expected is None:
        assert_parse_args(foo, cmd_str)
    else:
        assert_parse_args(foo, cmd_str, expected)


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("", None),
        ("--empty-my-set", set()),
        ("--empty-my-set=True", set()),
        ("--empty-my-set=False", None),
    ],
)
def test_optional_set_empty_flag_default(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_set: set[int] | None = None):
        pass

    if expected is None:
        assert_parse_args(foo, cmd_str)
    else:
        assert_parse_args(foo, cmd_str, expected)


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("", None),
        ("--empty-my-list", []),
        ("--my-list", []),
        ("--my-list http://example.com", ["http://example.com"]),
        ("--my-list http://example.com http://example2.com", ["http://example.com", "http://example2.com"]),
    ],
)
def test_optional_list_consume_multiple(app, cmd_str, expected, assert_parse_args):
    """Test that --my-list with no values behaves like --empty-my-list when consume_multiple=True."""

    @app.default
    def foo(my_list: Annotated[list[str] | None, Parameter(consume_multiple=True)] = None):
        pass

    if expected is None:
        assert_parse_args(foo, cmd_str)
    else:
        assert_parse_args(foo, cmd_str, expected)


# --- consume_multiple=int (minimum count) ---


def test_consume_multiple_int_rejects_empty(app):
    """consume_multiple=1 should reject --option with no values."""

    @app.default
    def foo(*, my_list: Annotated[list[str] | None, Parameter(consume_multiple=1)] = None):
        pass

    with pytest.raises(ConsumeMultipleError, match="requires at least 1 elements. Got 0"):
        app.parse_args("--my-list", print_error=False, exit_on_error=False)


def test_consume_multiple_int_accepts_enough(app, assert_parse_args):
    """consume_multiple=1 should accept --option with 1+ values."""

    @app.default
    def foo(*, my_list: Annotated[list[str] | None, Parameter(consume_multiple=1)] = None):
        pass

    assert_parse_args(foo, "--my-list a", my_list=["a"])
    assert_parse_args(foo, "--my-list a b c", my_list=["a", "b", "c"])


def test_consume_multiple_int_min_2(app):
    """consume_multiple=2 should reject --option with fewer than 2 values."""

    @app.default
    def foo(*, my_list: Annotated[list[str] | None, Parameter(consume_multiple=2)] = None):
        pass

    with pytest.raises(ConsumeMultipleError, match="requires at least 2 elements. Got 1"):
        app.parse_args("--my-list a", print_error=False, exit_on_error=False)


def test_consume_multiple_int_min_2_accepts(app, assert_parse_args):
    """consume_multiple=2 should accept --option with 2+ values."""

    @app.default
    def foo(*, my_list: Annotated[list[str] | None, Parameter(consume_multiple=2)] = None):
        pass

    assert_parse_args(foo, "--my-list a b", my_list=["a", "b"])
    assert_parse_args(foo, "--my-list a b c", my_list=["a", "b", "c"])


def test_consume_multiple_0_allows_empty(app, assert_parse_args):
    """consume_multiple=0 should behave like True (allow empty)."""

    @app.default
    def foo(*, my_list: Annotated[list[str] | None, Parameter(consume_multiple=0)] = None):
        pass

    assert_parse_args(foo, "--my-list", my_list=[])
    assert_parse_args(foo, "--my-list a b", my_list=["a", "b"])


# --- consume_multiple=tuple (min, max) ---


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--my-list", []),
        ("--my-list a", ["a"]),
        ("--my-list a b c", ["a", "b", "c"]),
    ],
)
def test_consume_multiple_tuple_0_3(app, cmd_str, expected, assert_parse_args):
    """consume_multiple=(0, 3) allows empty but stops after 3."""

    @app.default
    def foo(*, my_list: Annotated[list[str] | None, Parameter(consume_multiple=(0, 3))] = None):
        pass

    assert_parse_args(foo, cmd_str, my_list=expected)


def test_consume_multiple_tuple_0_3_max_enforced(app):
    """consume_multiple=(0, 3) should reject more than 3 values."""

    @app.default
    def foo(other: str, *, my_list: Annotated[list[str] | None, Parameter(consume_multiple=(0, 3))] = None):
        pass

    # With 4 values after --my-list, should raise an error since max is 3.
    with pytest.raises(ConsumeMultipleError, match="accepts at most 3 elements. Got 4"):
        app.parse_args("--my-list a b c d", print_error=False, exit_on_error=False)


def test_consume_multiple_tuple_min_max(app, assert_parse_args):
    """consume_multiple=(2, 5) requires 2-5 values."""

    @app.default
    def foo(*, my_list: Annotated[list[str] | None, Parameter(consume_multiple=(2, 5))] = None):
        pass

    assert_parse_args(foo, "--my-list a b", my_list=["a", "b"])
    assert_parse_args(foo, "--my-list a b c d e", my_list=["a", "b", "c", "d", "e"])


def test_consume_multiple_tuple_min_not_met(app):
    """consume_multiple=(2, 5) should reject fewer than 2 values."""

    @app.default
    def foo(*, my_list: Annotated[list[str] | None, Parameter(consume_multiple=(2, 5))] = None):
        pass

    with pytest.raises(ConsumeMultipleError, match="requires at least 2 elements. Got 1"):
        app.parse_args("--my-list a", print_error=False, exit_on_error=False)

    with pytest.raises(ConsumeMultipleError, match="requires at least 2 elements. Got 0"):
        app.parse_args("--my-list", print_error=False, exit_on_error=False)


def test_consume_multiple_error_is_missing_argument_error():
    """ConsumeMultipleError should be a subclass of MissingArgumentError for backward compat."""
    assert issubclass(ConsumeMultipleError, MissingArgumentError)


def test_consume_multiple_error_message_max(app):
    """Exceeding max should produce an 'accepts at most' message."""

    @app.default
    def foo(*, urls: Annotated[list[str] | None, Parameter(consume_multiple=(2, 5))] = None):
        pass

    with pytest.raises(ConsumeMultipleError, match="accepts at most 5 elements. Got 6"):
        app.parse_args("--urls a b c d e f", print_error=False, exit_on_error=False)


def test_consume_multiple_error_panel_min(app):
    """Full rich panel output for min constraint violation."""

    @app.default
    def foo(*, urls: Annotated[list[str] | None, Parameter(consume_multiple=(2, 5))] = None):
        pass

    with pytest.raises(ConsumeMultipleError) as exc_info:
        app.parse_args("--urls a", print_error=False, exit_on_error=False)

    buf = StringIO()
    console = Console(file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False)
    console.print(CycloptsPanel(exc_info.value))
    actual = buf.getvalue()

    expected = textwrap.dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Parameter "--urls" requires at least 2 elements. Got 1.            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


def test_consume_multiple_error_panel_empty(app):
    """Full rich panel output when zero values provided."""

    @app.default
    def foo(*, urls: Annotated[list[str] | None, Parameter(consume_multiple=3)] = None):
        pass

    with pytest.raises(ConsumeMultipleError) as exc_info:
        app.parse_args("--urls", print_error=False, exit_on_error=False)

    buf = StringIO()
    console = Console(file=buf, width=70, force_terminal=True, highlight=False, color_system=None, legacy_windows=False)
    console.print(CycloptsPanel(exc_info.value))
    actual = buf.getvalue()

    expected = textwrap.dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Parameter "--urls" requires at least 3 elements. Got 0.            │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected


# --- Validation at Parameter creation ---


def test_consume_multiple_negative_int_raises():
    """Negative int should raise ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        Parameter(consume_multiple=-1)


def test_consume_multiple_tuple_min_gt_max_raises():
    """Tuple with min > max should raise ValueError."""
    with pytest.raises(ValueError, match="min must be <= max"):
        Parameter(consume_multiple=(5, 3))


def test_consume_multiple_tuple_negative_raises():
    """Tuple with negative values should raise ValueError."""
    with pytest.raises(ValueError, match="non-negative"):
        Parameter(consume_multiple=(-1, 3))
