from textwrap import dedent

import pytest
from pydantic import PositiveInt, validate_call
from pydantic import ValidationError as PydanticValidationError


def test_pydantic_error_msg(app, console):
    @app.command
    @validate_call
    def foo(value: PositiveInt):
        print(value)

    assert app["foo"].default_command == foo

    foo(1)
    with pytest.raises(PydanticValidationError):
        foo(-1)

    with console.capture() as capture, pytest.raises(PydanticValidationError):
        app(["foo", "-1"], console=console, exit_on_error=False, print_error=True)

    actual = capture.get()

    expected_prefix = dedent(
        """\
        ╭─ Error ────────────────────────────────────────────────────────────╮
        │ 1 validation error for foo                                         │
        │ 0                                                                  │
        │   Input should be greater than 0 [type=greater_than,               │
        │ input_value=-1, input_type=int]                                    │
        │     For further information visit                                  │
        """
    )

    assert actual.startswith(expected_prefix)
