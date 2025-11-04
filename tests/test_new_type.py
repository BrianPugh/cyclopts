from typing import Literal, NewType

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


@pytest.mark.parametrize(
    "cmd, expected",
    [
        ("test", "test"),
        ("other", "other"),
    ],
)
def test_new_type_union_literal_issue_677(app, assert_parse_args, cmd, expected):
    """Test for issue #677: NewType union with Literal should work like str union with Literal.

    This test verifies that a union of NewType and Literal behaves the same as a union
    of the base type and Literal. The issue reported a ValueError about required field
    not being accessible when providing an argument value.
    """
    NT = NewType("NT", str)

    @app.default
    def main(a: NT | Literal["test"] = "test"):
        pass

    assert_parse_args(main, cmd, expected)


@pytest.mark.parametrize(
    "cmd, expected",
    [
        ("test", "test"),
        ("other", "other"),
    ],
)
def test_new_type_union_literal_comparison_with_str(app, assert_parse_args, cmd, expected):
    """Verify NewType | Literal behaves identically to str | Literal."""
    NT = NewType("NT", str)

    @app.command
    def with_newtype(a: NT | Literal["test"] = "test"):
        pass

    @app.command
    def with_str(a: str | Literal["test"] = "test"):
        pass

    assert_parse_args(with_newtype, f"with-newtype {cmd}", expected)
    assert_parse_args(with_str, f"with-str {cmd}", expected)
