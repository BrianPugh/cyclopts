from typing import Any, Union

import pytest
from attrs import frozen
from typing_extensions import Annotated

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


def test_custom_type_two_token_implicit_convert_must_take_converter(app):
    with pytest.raises(ValueError):

        @app.default
        def default(value: Annotated[TwoToken, Parameter(token_count=2)]):
            return value


def test_custom_type_two_token_explicit_convert(app):
    def converter(type_, *args):
        assert len(args) == 2
        return type_(coerce(Union[int, str], args[0]), coerce(Union[int, str], args[1]))

    @app.default
    def default(value: Annotated[TwoToken, Parameter(converter=converter, token_count=2)]):
        return value

    res = app("foo bar")
    assert res == TwoToken("foo", "bar")

    res = app("5 6")
    assert res == TwoToken(5, 6)
