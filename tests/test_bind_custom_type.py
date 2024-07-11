import sys

from cyclopts import Parameter

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


class OneToken:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value


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
