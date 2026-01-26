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


def test_list_multi_token_non_union_keyword(app, assert_parse_args):
    """Test list with non-union multi-token type using keyword arguments.

    For non-union element types, each --values captures the exact number of
    tokens needed for one element (2 for tuple[int, str]).
    """

    @app.default
    def main(values: list[tuple[int, str]]):
        pass

    # Each --values captures 2 tokens (one complete tuple)
    assert_parse_args(main, "--values 1 one", [(1, "one")])

    # Multiple tuples via keyword
    assert_parse_args(main, "--values 1 one --values 2 two", [(1, "one"), (2, "two")])

    # Three tuples
    assert_parse_args(main, "--values 1 a --values 2 b --values 3 c", [(1, "a"), (2, "b"), (3, "c")])


def test_list_multi_token_union_keyword(app, assert_parse_args):
    """Test list with union of multi-token types using keyword arguments.

    For union element types with varying token counts, each --values captures
    one token. Tokens are accumulated across multiple --values invocations,
    then dynamic conversion is applied to all accumulated tokens together.
    """

    @app.default
    def main(values: list[tuple[int, int] | str]):
        pass

    # Each --values captures one token; tokens are combined then converted dynamically
    # Two numeric tokens -> one tuple
    assert_parse_args(main, "--values 1 --values 2", [(1, 2)])

    # Four numeric tokens -> two tuples
    assert_parse_args(main, "--values 1 --values 2 --values 3 --values 4", [(1, 2), (3, 4)])

    # Mixed: numeric and string tokens
    assert_parse_args(main, "--values 1 --values 2 --values hello --values 3 --values 4", [(1, 2), "hello", (3, 4)])

    # All strings
    assert_parse_args(main, "--values hello --values world", ["hello", "world"])


def test_list_multi_token_union_two_multi_token_types(app, assert_parse_args):
    """Test list with union of two different multi-token tuple types.

    With tuple[int, int] | tuple[int, int, int], left-to-right semantics apply:
    - First try tuple[int, int] (needs 2 tokens)
    - If that fails, try tuple[int, int, int] (needs 3 tokens)

    Since tuple[int, int] comes first and always succeeds when 2+ int tokens
    are available, tuple[int, int, int] will only match when exactly 3 tokens
    remain and the first 2 can't form a valid tuple[int, int] (which won't happen
    with ints). So effectively tuple[int, int] always wins.
    """

    @app.default
    def main(values: list[tuple[int, int] | tuple[int, int, int]]):
        pass

    # 4 tokens -> two tuple[int, int] (first type matches)
    assert_parse_args(main, "1 2 3 4", [(1, 2), (3, 4)])

    # 6 tokens -> three tuple[int, int]
    assert_parse_args(main, "1 2 3 4 5 6", [(1, 2), (3, 4), (5, 6)])


def test_list_multi_token_union_three_token_first(app, assert_parse_args):
    """Test with 3-token type first in union - it gets priority."""

    @app.default
    def main(values: list[tuple[int, int, int] | tuple[int, int]]):
        pass

    # 6 tokens -> two tuple[int, int, int] (first type matches when enough tokens)
    assert_parse_args(main, "1 2 3 4 5 6", [(1, 2, 3), (4, 5, 6)])

    # 4 tokens -> first takes 3, leaving 1 which isn't enough for either
    # tuple[int, int, int] needs 3, only 1 left -> skip
    # tuple[int, int] needs 2, only 1 left -> skip
    # This should raise an error or the last token is unparsable
    # Actually, let's test 5 tokens: first takes 3, leaving 2 for tuple[int, int]
    assert_parse_args(main, "1 2 3 4 5", [(1, 2, 3), (4, 5)])


def test_list_multi_token_union_consume_all(app, assert_parse_args):
    """Test list with union where one type has consume_all (tuple[T, ...])."""

    @app.default
    def main(values: list[tuple[int, int] | tuple[str, ...]]):
        pass

    # Two ints -> tuple[int, int] matches first
    assert_parse_args(main, "1 2", [(1, 2)])

    # Four ints -> two tuple[int, int]
    assert_parse_args(main, "1 2 3 4", [(1, 2), (3, 4)])

    # Strings that can't be ints -> tuple[str, ...] consumes all
    assert_parse_args(main, "hello world foo", [("hello", "world", "foo")])

    # Mix: two ints first, then strings trigger consume_all for rest
    # Actually this is tricky - after (1,2), remaining is ["hello", "world"]
    # tuple[int, int] fails on "hello", tuple[str, ...] consumes all remaining
    assert_parse_args(main, "1 2 hello world", [(1, 2), ("hello", "world")])


def test_frozenset_multi_token_union(app, assert_parse_args):
    """Test frozenset with union of multi-token type works like set."""

    @app.default
    def main(values: frozenset[tuple[int, int] | str]):
        pass

    _, bound, _ = app.parse_args("1 2 hello 3 4", print_error=False, exit_on_error=False)
    assert bound.arguments["values"] == frozenset({(1, 2), "hello", (3, 4)})
