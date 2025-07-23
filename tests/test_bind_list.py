from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pytest

from cyclopts.exceptions import MissingArgumentError


def test_pos_list(app, assert_parse_args):
    @app.command
    def foo(a: List[int]):
        pass

    assert_parse_args(foo, "foo 1 2 3", [1, 2, 3])


def test_keyword_list(app, assert_parse_args):
    @app.command
    def foo(a: List[int]):
        pass

    assert_parse_args(foo, "foo --a=1 --a=2 --a 3", [1, 2, 3])


def test_keyword_list_mutable_default(app, assert_parse_args):
    @app.command
    def foo(a: List[int] = []):  # noqa: B006
        pass

    assert_parse_args(foo, "foo --a=1 --a=2 --a 3", [1, 2, 3])
    assert_parse_args(foo, "foo")


def test_keyword_list_pos(app, assert_parse_args):
    @app.command
    def foo(a: List[int]):
        pass

    assert_parse_args(foo, "foo 1 2 3", [1, 2, 3])


def test_keyword_optional_list_none_default(app, assert_parse_args):
    @app.command
    def foo(a: Optional[List[int]] = None):
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
    def foo(*, verbose: Optional[list[bool]] = None):
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
    def foo(*, verbose: Optional[tuple[bool, ...]] = None):
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
def test_keyword_sequence_of_bool(app, assert_parse_args, cmd_expected):
    cmd, expected = cmd_expected

    @app.default
    def foo(*, verbose: Optional[Sequence[bool]] = None):
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
    def foo(item: List[Tuple[int, str]]):
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
    def foo(item: List[Tuple[int, str]], stuff: str = ""):
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
