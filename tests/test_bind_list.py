from typing import List, Optional, Tuple

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


def test_list_tuple_missing_arguments_no_arguments(app, assert_parse_args):
    """Missing values."""

    @app.command
    def foo(item: List[Tuple[int, str]]):
        pass

    with pytest.raises(MissingArgumentError):
        app("foo --item", exit_on_error=False)


def test_list_tuple_missing_arguments_non_divisible(app, assert_parse_args):
    """Missing values."""

    @app.command
    def foo(item: List[Tuple[int, str]]):
        pass

    with pytest.raises(MissingArgumentError):
        app("foo --item 1 alice 2", exit_on_error=False)
