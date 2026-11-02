from pathlib import Path
from typing import Literal, NewType

import pytest

from cyclopts._convert import token_count
from cyclopts.exceptions import CoercionError


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


UserId = NewType("UserId", int)
CustomPath = NewType("CustomPath", Path)


@pytest.mark.parametrize(
    "hint, cmd, expected",
    [
        (list[UserId], "1 2", [1, 2]),
        (set[UserId], "1", {1}),
        (tuple[UserId, str], "1 foo", (1, "foo")),
        (UserId | Literal["auto"], "1", 1),
        (list[UserId | None], "1", [1]),
        (list[CustomPath], "foo", [Path("foo")]),
    ],
)
def test_new_type_nested(app, assert_parse_args, hint, cmd, expected):
    """A nested NewType converts to its underlying type instead of staying a string."""

    @app.default
    def main(a: hint):  # pyright: ignore[reportInvalidTypeForm]
        pass

    assert_parse_args(main, cmd, expected)


def test_new_type_nested_invalid(app):
    @app.default
    def main(a: list[UserId]):
        pass

    with pytest.raises(CoercionError):
        app.parse_args("foo", print_error=False, exit_on_error=False)
