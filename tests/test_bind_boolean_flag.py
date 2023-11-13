import inspect

import pytest
from typing_extensions import Annotated

from cyclopts import Parameter


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--my-flag", True),
        ("--no-my-flag", False),
    ],
)
def test_boolean_flag_default(app, cmd_str, expected):
    @app.register_default
    def foo(my_flag: bool = True):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(expected)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--my-flag", True),
        ("--yesnt-my-flag", False),
    ],
)
def test_boolean_flag_custom_negative(app, cmd_str, expected):
    @app.register_default
    def foo(my_flag: Annotated[bool, Parameter(negative="--yesnt-my-flag")] = True):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(expected)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind
