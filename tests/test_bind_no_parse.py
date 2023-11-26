import inspect

import pytest
from typing_extensions import Annotated

from cyclopts import Parameter


def test_no_parse_pos(app):
    @app.default
    def foo(buzz: str, *, fizz: Annotated[str, Parameter(parse=False)]):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind_partial("buzz_value")

    actual_command, actual_bind = app.parse_args("buzz_value")
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_no_parse_invalid_kind(app):
    # Parameter.parse=False must be used with KEYWORD_ONLY.
    with pytest.raises(ValueError):

        @app.default
        def foo(buzz: str, fizz: Annotated[str, Parameter(parse=False)]):
            pass
