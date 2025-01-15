from typing import Annotated

import pytest

from cyclopts import Parameter


def test_no_parse_pos(app, assert_parse_args_partial):
    @app.default
    def foo(buzz: str, *, fizz: Annotated[str, Parameter(parse=False)]):
        pass

    assert_parse_args_partial(foo, "buzz_value", "buzz_value")
    _, _, ignored = app.parse_args("buzz_value")
    assert ignored == {"fizz": str}


def test_no_parse_invalid_kind(app):
    # Parameter.parse=False must be used with KEYWORD_ONLY.
    with pytest.raises(ValueError):

        @app.default
        def foo(buzz: str, fizz: Annotated[str, Parameter(parse=False)]):
            pass

        app([])
