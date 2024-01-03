import inspect
import sys

import pytest

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from cyclopts import CoercionError, Group, Parameter


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


def test_boolean_flag_app_parameter_default_nested_annotated_override(app):
    app.default_parameter = Parameter(negative="")

    def my_converter(type_, *values):
        return 5

    my_int = Annotated[int, Parameter(converter=my_converter)]

    @app.default
    def foo(*, foo: Annotated[my_int, Parameter(name="--bar")] = True):  # pyright: ignore[reportGeneralTypeIssues]
        pass

    signature = inspect.signature(foo)

    expected_bind = signature.bind(foo=5)
    actual_command, actual_bind = app.parse_args("--bar=10")
    assert actual_command == foo
    assert actual_bind == expected_bind


def test_boolean_flag_group_default_parameter_resolution_1(app):
    food_group = Group("Food", default_parameter=Parameter(negative_bool="--group-"))

    @app.default
    def foo(flag: Annotated[bool, Parameter(group=food_group)]):
        pass

    signature = inspect.signature(foo)

    expected_bind = signature.bind(False)
    actual_command, actual_bind = app.parse_args("--group-flag", exit_on_error=False)
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
