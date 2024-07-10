import sys
from typing import Any, Union

import pytest
from attrs import frozen

from cyclopts import Parameter, convert

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


@frozen
class OneToken:
    value: Any


@frozen
class TwoToken:
    value1: Any
    value2: Any


class AllToken:
    def __init__(self, *args):
        self.args = args


def test_custom_type_one_token_implicit_convert(app):
    @app.default
    def default(value: OneToken):
        return value

    res = app("foo")
    assert res == OneToken("foo")

    res = app("5")
    assert res == OneToken("5")


def test_custom_type_one_token_explicit_convert(app):
    def converter(type_, tokens):
        assert len(tokens) == 1
        return type_(int(tokens[0]))

    @app.default
    def default(value: Annotated[OneToken, Parameter(converter=converter)]):
        return value

    res = app("5")
    assert res == OneToken(5)
