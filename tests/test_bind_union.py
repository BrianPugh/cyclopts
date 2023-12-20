import inspect
import sys
from typing import Union

import pytest

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import Parameter
from cyclopts.exceptions import CoercionError


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("foo 1", 1),
        ("foo --a=1", 1),
        ("foo --a 1", 1),
        ("foo bar", "bar"),
        ("foo --a=bar", "bar"),
        ("foo --a bar", "bar"),
    ],
)
@pytest.mark.parametrize("annotated", [False, True])
def test_union_required_implicit_coercion(app, cmd_str, expected, annotated):
    """
    For a union without an explicit coercion, the first non-None type annotation
    should be used. In this case, it's ``int``.
    """
    if annotated:

        @app.command
        def foo(a: Annotated[Union[None, int, str], Parameter(help="help for a")]):
            pass

    else:

        @app.command
        def foo(a: Union[None, int, str]):
            pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(expected)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_union_coercion_cannot_coerce_error(app):
    @app.default
    def default(a: Union[None, int, float]):
        pass

    with pytest.raises(CoercionError):
        app.parse_args("foo", exit_on_error=False)
