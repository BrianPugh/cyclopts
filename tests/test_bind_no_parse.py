import inspect
import sys

import pytest

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import Parameter


def test_parse_false_keyword_only(app, assert_parse_args_partial):
    @app.default
    def foo(buzz: str, *, fizz: Annotated[str, Parameter(parse=False)]):
        pass

    assert_parse_args_partial(foo, "buzz_value", "buzz_value")


def test_parse_false_trailing_positional_or_keyword(app, assert_parse_args_partial):
    @app.default
    def foo(fizz: str, buzz: Annotated[str, Parameter(parse=False)]):
        pass

    assert_parse_args_partial(foo, "fizz_value", "fizz_value")


def test_parse_false_trailing_positional_only(app, assert_parse_args_partial):
    @app.default
    def foo(fizz: str, buzz: Annotated[str, Parameter(parse=False)], /):
        pass

    assert_parse_args_partial(foo, "fizz_value", "fizz_value")


def test_parse_false_leading_exceptions_positional_or_keyword(app):
    # Parameter.parse=False cannot be used with a non-trailing positional argument
    with pytest.raises(ValueError):

        @app.default
        def foo(fizz: Annotated[str, Parameter(parse=False)], buzz: str):
            pass


def test_parse_false_leading_exceptions_positional_only(app):
    with pytest.raises(ValueError):

        @app.default
        def foo(fizz: Annotated[str, Parameter(parse=False)], buzz: str, /):
            pass
