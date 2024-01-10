import sys
from typing import Any, Union

import pytest
from attrs import frozen

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import Parameter, coerce


@frozen
class OneToken:
    value: Any


@frozen
class TwoToken:
    value1: Any
    value2: Any


def test_custom_type_one_token_implicit_convert(app):
    @app.default
    def default(value: OneToken):
        return value

    res = app("foo")
    assert res == OneToken("foo")

    res = app("5")
    assert res == OneToken("5")


def test_custom_type_one_token_explicit_convert(app):
    def converter(type_, *args):
        assert len(args) == 1
        return type_(int(args[0]))

    @app.default
    def default(value: Annotated[OneToken, Parameter(converter=converter)]):
        return value

    res = app("5")
    assert res == OneToken(5)


@pytest.mark.parametrize(
    "cmd_str",
    [
        "--value1 foo bar 3",
        "foo bar 3",
        "foo bar --value2=3",
        "foo bar --value2 3",
    ],
)
def test_custom_type_two_token_explicit_convert(app, cmd_str):
    def converter(type_, *args):
        assert len(args) == 2
        return type_(coerce(Union[int, str], args[0]), coerce(Union[int, str], args[1]))

    @app.default
    def default(
        value1: Annotated[TwoToken, Parameter(converter=converter, token_count=2)],
        value2: int,
    ):
        assert value2 == 3
        return value1

    res = app(cmd_str, exit_on_error=False, print_error=True)
    assert res == TwoToken("foo", "bar")


# TODO: list of custom class
# TODO: tuple of custom class
