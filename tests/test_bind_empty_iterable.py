from typing import Annotated

import pytest

from cyclopts import Parameter


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
