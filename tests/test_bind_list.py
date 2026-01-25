import collections.abc
from collections.abc import MutableSequence as AbcMutableSequence
from collections.abc import MutableSet as AbcMutableSet
from collections.abc import Sequence
from collections.abc import Set as AbcSet
from pathlib import Path

import pytest

from cyclopts.exceptions import MissingArgumentError


def test_pos_list(app, assert_parse_args):
    @app.command
    def foo(a: list[int]):
        pass

    assert_parse_args(foo, "foo 1 2 3", [1, 2, 3])


def test_keyword_list(app, assert_parse_args):
    @app.command
    def foo(a: list[int]):
        pass

    assert_parse_args(foo, "foo --a=1 --a=2 --a 3", [1, 2, 3])


def test_keyword_list_mutable_default(app, assert_parse_args):
    @app.command
    def foo(a: list[int] = []):  # noqa: B006
        pass

    assert_parse_args(foo, "foo --a=1 --a=2 --a 3", [1, 2, 3])
    assert_parse_args(foo, "foo")


def test_keyword_list_pos(app, assert_parse_args):
    @app.command
    def foo(a: list[int]):
        pass

    assert_parse_args(foo, "foo 1 2 3", [1, 2, 3])


def test_keyword_optional_list_none_default(app, assert_parse_args):
    @app.command
    def foo(a: list[int] | None = None):
        pass

    assert_parse_args(foo, "foo")


@pytest.mark.parametrize(
    "cmd_expected",
    [
        ("", None),
        ("--verbose", [True]),
        ("--verbose --verbose", [True, True]),
        ("--verbose --verbose --no-verbose", [True, True, False]),
        ("--verbose --verbose=False", [True, False]),
        ("--verbose --no-verbose=False", [True, True]),
        ("--verbose --verbose=True", [True, True]),
    ],
)
def test_keyword_list_of_bool(app, assert_parse_args, cmd_expected):
    cmd, expected = cmd_expected

    @app.default
    def foo(*, verbose: list[bool] | None = None):
        pass

    if expected is None:
        assert_parse_args(foo, cmd)
    else:
        assert_parse_args(foo, cmd, verbose=expected)


@pytest.mark.parametrize(
    "cmd_expected",
    [
        ("", None),
        ("--verbose", (True,)),
        ("--verbose --verbose", (True, True)),
        ("--verbose --verbose --no-verbose", (True, True, False)),
        ("--verbose --verbose=False", (True, False)),
        ("--verbose --no-verbose=False", (True, True)),
        ("--verbose --verbose=True", (True, True)),
    ],
)
def test_keyword_tuple_of_bool(app, assert_parse_args, cmd_expected):
    cmd, expected = cmd_expected

    @app.default
    def foo(*, verbose: tuple[bool, ...] | None = None):
        pass

    if expected is None:
        assert_parse_args(foo, cmd)
    else:
        assert_parse_args(foo, cmd, verbose=expected)


@pytest.mark.parametrize(
    "cmd_expected",
    [
        ("", None),
        ("--verbose", [True]),
        ("--verbose --verbose", [True, True]),
        ("--verbose --verbose --no-verbose", [True, True, False]),
        ("--verbose --verbose=False", [True, False]),
        ("--verbose --no-verbose=False", [True, True]),
        ("--verbose --verbose=True", [True, True]),
    ],
)
@pytest.mark.parametrize("hint", [Sequence[bool], collections.abc.Sequence[bool]])
def test_keyword_sequence_of_bool(app, assert_parse_args, cmd_expected, hint):
    cmd, expected = cmd_expected

    @app.default
    def foo(*, verbose: hint | None = None):  # pyright: ignore[reportInvalidTypeForm]
        pass

    if expected is None:
        assert_parse_args(foo, cmd)
    else:
        assert_parse_args(foo, cmd, verbose=expected)


@pytest.mark.parametrize(
    "cmd",
    [
        "foo --item",
    ],
)
def test_list_tuple_missing_arguments_no_arguments(app, cmd):
    """Missing values."""

    @app.command
    def foo(item: list[tuple[int, str]]):
        pass

    with pytest.raises(MissingArgumentError):
        app(cmd, exit_on_error=False)


@pytest.mark.parametrize(
    "cmd",
    [
        "foo --item 1",
        "foo --item a --stuff g",
    ],
)
def test_list_tuple_missing_arguments_non_divisible(app, cmd):
    """Missing values."""

    @app.command
    def foo(item: list[tuple[int, str]], stuff: str = ""):
        pass

    with pytest.raises(MissingArgumentError):
        app(cmd, exit_on_error=False)


def test_pos_sequence(app, assert_parse_args):
    @app.command
    def foo(a: Sequence[int]):
        pass

    assert_parse_args(foo, "foo 1 2 3", [1, 2, 3])


@pytest.mark.parametrize(
    "cmd_str",
    [
        "fizz buzz bar",
        "-- fizz buzz bar",
        "fizz -- buzz bar",
        "fizz buzz -- bar",
        "fizz buzz bar --",
    ],
)
def test_list_positional_all_but_last(app, cmd_str, assert_parse_args):
    @app.default
    def foo(inputs: list[Path], output: Path, /):
        pass

    assert_parse_args(foo, cmd_str, [Path("fizz"), Path("buzz")], Path("bar"))


@pytest.mark.parametrize(
    "hint,expected",
    [
        (AbcSet[str], {"1", "2", "3"}),
        (AbcMutableSet[str], {"1", "2", "3"}),
        (AbcMutableSequence[str], ["1", "2", "3"]),
        (collections.abc.Set, {"1", "2", "3"}),
        (collections.abc.MutableSet, {"1", "2", "3"}),
        (collections.abc.MutableSequence, ["1", "2", "3"]),
    ],
)
def test_abstract_collection_types(app, assert_parse_args, hint, expected):
    """Test that collections.abc abstract types work (issue #702).

    Tests both parameterized types (e.g., Set[str]) and bare types (e.g., Set).
    Bare abstract types should default to [str] like bare concrete types.
    """

    @app.default
    def main(test: hint):  # pyright: ignore[reportInvalidTypeForm]
        return test

    assert_parse_args(main, "1 2 3", expected)


#############################
# Multi-Token Union Elements
#############################


@pytest.mark.parametrize(
    "cmd,expected",
    [
        # Two ints -> one tuple
        ("1 2", [(1, 2)]),
        # Four ints -> two tuples
        ("1 2 3 4", [(1, 2), (3, 4)]),
        # Single string
        ("hello", ["hello"]),
        # Multiple strings
        ("hello world", ["hello", "world"]),
        # Mix of tuples and strings
        ("1 2 hello 3 4", [(1, 2), "hello", (3, 4)]),
        # Odd number of numeric tokens - last becomes string
        ("1 2 3", [(1, 2), "3"]),
        # String between tuples
        ("1 2 foo 3 4 bar", [(1, 2), "foo", (3, 4), "bar"]),
    ],
)
def test_list_multi_token_union_tuple_or_str(app, assert_parse_args, cmd, expected):
    """Test list with union of multi-token type (tuple) and single-token type (str)."""

    @app.default
    def main(values: list[tuple[int, int] | str]):
        pass

    assert_parse_args(main, cmd, expected)


@pytest.mark.parametrize(
    "cmd,expected",
    [
        # Two ints -> one tuple
        ("1 2", [(1, 2)]),
        # "none" -> None
        ("none", [None]),
        # Mix of tuples and None
        ("1 2 none 3 4", [(1, 2), None, (3, 4)]),
        # Multiple None values
        ("none null NONE", [None, None, None]),
    ],
)
def test_list_multi_token_union_tuple_or_none(app, assert_parse_args, cmd, expected):
    """Test list with union of multi-token type (tuple) and None."""

    @app.default
    def main(values: list[tuple[int, int] | None]):
        pass

    assert_parse_args(main, cmd, expected)


def test_list_multi_token_union_literal(app, assert_parse_args):
    """Test list with union of multi-token type (tuple) and Literal."""
    from typing import Literal

    @app.default
    def main(values: list[tuple[int, int] | Literal["auto"]]):
        pass

    assert_parse_args(main, "auto 1 2 auto", ["auto", (1, 2), "auto"])


def test_set_multi_token_union(app, assert_parse_args):
    """Test set with union of multi-token type works."""

    @app.default
    def main(values: set[tuple[int, int] | str]):
        pass

    # Note: set order is not guaranteed, so we check the bound values
    _, bound, _ = app.parse_args("1 2 hello 3 4", print_error=False, exit_on_error=False)
    assert bound.arguments["values"] == {(1, 2), "hello", (3, 4)}


def test_list_union_str_first_always_matches_str(app, assert_parse_args):
    """When str is first in union, it should always match (left-to-right semantics)."""

    @app.default
    def main(values: list[str | tuple[int, int]]):
        pass

    # All values become strings because str matches first
    assert_parse_args(main, "1 2 hello", ["1", "2", "hello"])


def test_list_multi_token_union_three_token_type(app, assert_parse_args):
    """Test list with 3-token tuple type."""

    @app.default
    def main(values: list[tuple[int, int, int] | str]):
        pass

    assert_parse_args(main, "1 2 3 hello 4 5 6", [(1, 2, 3), "hello", (4, 5, 6)])
    # When not enough tokens for tuple, falls back to str
    assert_parse_args(main, "1 2", ["1", "2"])
