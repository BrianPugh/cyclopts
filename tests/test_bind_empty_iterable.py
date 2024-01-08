import inspect
from typing import List, Optional, Set

import pytest


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("", None),
        ("--empty-my-list", []),
    ],
)
def test_optional_list_empty_flag_default(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_list: Optional[List[int]] = None):
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
    ],
)
def test_optional_set_empty_flag_default(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_set: Optional[Set[int]] = None):
        pass

    if expected is None:
        assert_parse_args(foo, cmd_str)
    else:
        assert_parse_args(foo, cmd_str, expected)
