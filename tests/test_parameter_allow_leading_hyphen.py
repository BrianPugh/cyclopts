from typing import Annotated

import pytest

from cyclopts import Parameter
from cyclopts.exceptions import UnknownOptionError


def test_allow_leading_hyphen_false(app):
    @app.default
    def foo(bar: Annotated[str, Parameter()]):
        pass

    with pytest.raises(UnknownOptionError):
        app("--buzz", exit_on_error=False, print_error=True)


def test_allow_leading_hyphen_true(app, assert_parse_args):
    @app.default
    def foo(bar: Annotated[str, Parameter(allow_leading_hyphen=True)]):
        pass

    assert_parse_args(foo, "--buzz", bar="--buzz")
