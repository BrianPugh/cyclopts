import inspect

import pytest
from typing_extensions import Annotated

from cyclopts import CoercionError, Parameter


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--my-flag", True),
        ("--no-my-flag", False),
    ],
)
def test_boolean_flag_default(app, cmd_str, expected):
    @app.default
    def foo(my_flag: bool = True):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(expected)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_boolean_flag_app_parameter_default(app):
    app.default_parameter = Parameter(negative="")

    @app.default
    def foo(my_flag: bool = True):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(True)

    # Normal positive flag should still work.
    actual_command, actual_bind = app.parse_args("--my-flag")
    assert actual_command == foo
    assert actual_bind == expected_bind

    # The negative flag should be disabled.
    with pytest.raises(CoercionError):
        app.parse_args("--no-my-flag", exit_on_error=False)


def test_boolean_flag_app_parameter_default_annotated_override(app):
    app.default_parameter = Parameter(negative="")

    @app.default
    def foo(my_flag: Annotated[bool, Parameter(negative="--NO-flag")] = True):
        pass

    signature = inspect.signature(foo)

    expected_bind = signature.bind(True)
    actual_command, actual_bind = app.parse_args("--my-flag")
    assert actual_command == foo
    assert actual_bind == expected_bind

    expected_bind = signature.bind(False)
    actual_command, actual_bind = app.parse_args("--NO-flag")
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--bar", True),
        ("--no-bar", False),
    ],
)
def test_boolean_flag_custom_positive(app, cmd_str, expected):
    @app.default
    def foo(my_flag: Annotated[bool, Parameter(name="--bar")] = True):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(expected)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--bar", True),
        ("--no-bar", False),
    ],
)
def test_boolean_flag_custom_short_positive(app, cmd_str, expected):
    @app.default
    def foo(my_flag: Annotated[bool, Parameter(name=["--bar", "-b"])] = True):
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
    @app.default
    def foo(my_flag: Annotated[bool, Parameter(negative="--yesnt-my-flag")] = True):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(expected)

    actual_command, actual_bind = app.parse_args(cmd_str)
    assert actual_command == foo
    assert actual_bind == expected_bind


@pytest.mark.parametrize(
    "negative",
    ["", (), []],
)
def test_boolean_flag_disable_negative(app, negative):
    @app.default
    def foo(my_flag: Annotated[bool, Parameter(negative=negative)] = True):
        pass

    signature = inspect.signature(foo)
    expected_bind = signature.bind(True)

    actual_command, actual_bind = app.parse_args("--my-flag")
    assert actual_command == foo
    assert actual_bind == expected_bind

    with pytest.raises(CoercionError):
        app.parse_args("--no-my-flag", exit_on_error=False)
