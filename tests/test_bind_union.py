from textwrap import dedent
from typing import Annotated

import pytest

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
def test_union_required_implicit_coercion(app, cmd_str, expected, annotated, assert_parse_args):
    """
    For a union without an explicit coercion, the first non-None type annotation
    should be used. In this case, it's ``int``.
    """
    if annotated:

        @app.command
        def foo(a: Annotated[None | int | str, Parameter(help="help for a")]):
            pass

    else:

        @app.command
        def foo(a: None | int | str):
            pass

    assert_parse_args(foo, cmd_str, expected)


def test_union_coercion_cannot_coerce_error(app, console):
    @app.default
    def default(a: None | int | float):
        pass

    with console.capture() as capture, pytest.raises(CoercionError):
        app.parse_args("foo", error_console=console, exit_on_error=False)

    actual = capture.get()

    expected = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ Invalid value for "A": unable to convert "foo" into int|float.     │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )

    assert actual == expected
