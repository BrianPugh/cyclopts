from typing import NewType

import pytest

from cyclopts._convert import token_count


def test_new_type_str(app, assert_parse_args):
    CustomStr = NewType("CustomStr", str)

    @app.default
    def main(a: CustomStr):
        pass

    assert_parse_args(main, "foo", CustomStr("foo"))


def test_new_type_token_count_str(app, assert_parse_args):
    CustomStr = NewType("CustomStr", str)
    assert (1, False) == token_count(CustomStr)


@pytest.mark.parametrize(
    "cmd, expected",
    [
        ("foo", ["foo"]),
        ("--a foo", ["foo"]),
        ("foo bar", ["foo", "bar"]),
        ("--a foo --a bar", ["foo", "bar"]),
        ("foo bar baz", ["foo", "bar", "baz"]),
        ("--a foo --a bar --a baz", ["foo", "bar", "baz"]),
    ],
)
def test_new_type_token_count_list_str(app, assert_parse_args, cmd, expected):
    CustomStr = NewType("CustomStr", str)

    @app.default
    def main(a: list[CustomStr]):
        pass

    assert_parse_args(main, cmd, expected)
