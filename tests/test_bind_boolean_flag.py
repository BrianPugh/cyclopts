import sys

import pytest

from cyclopts import (
    Group,
    Parameter,
    UnknownOptionError,
)
from cyclopts.exceptions import CoercionError

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--my-flag", True),
        ("--my-flag=true", True),
        ("--my-flag=false", False),
        ("--no-my-flag", False),
    ],
)
def test_boolean_flag_default(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_flag: bool = True):
        pass

    assert_parse_args(foo, cmd_str, expected)


def test_boolean_flag_app_parameter_default(app, assert_parse_args):
    app.default_parameter = Parameter(negative="")

    @app.default
    def foo(my_flag: bool = True):
        pass

    # Normal positive flag should still work.
    assert_parse_args(foo, "--my-flag", True)

    with pytest.raises(UnknownOptionError) as e:
        app.parse_args("--no-my-flag", exit_on_error=False)
    assert str(e.value) == 'Unknown option: "--no-my-flag".'


def test_boolean_flag_app_parameter_negative(app, assert_parse_args):
    @app.default
    def foo(my_flag: Annotated[bool, Parameter("", negative="--no-my-flag")] = True):
        pass

    assert_parse_args(foo, "--no-my-flag", False)

    with pytest.raises(UnknownOptionError):
        app.parse_args("--my-flag", exit_on_error=False, print_error=True)

    assert_parse_args(foo, "--no-my-flag=True", False)
    assert_parse_args(foo, "--no-my-flag=False", True)

    with pytest.raises(CoercionError):
        app("--no-my-flag=", exit_on_error=False)


def test_boolean_flag_app_parameter_default_annotated_override(app, assert_parse_args):
    app.default_parameter = Parameter(negative="")

    @app.default
    def foo(my_flag: Annotated[bool, Parameter(negative="--NO-flag")] = True):
        pass

    assert_parse_args(foo, "--my-flag", True)
    assert_parse_args(foo, "--NO-flag", False)


def test_boolean_flag_app_parameter_default_nested_annotated_override(app, assert_parse_args):
    app.default_parameter = Parameter(negative="")

    def my_converter(type_, tokens):
        return 5

    my_int = Annotated[int, Parameter(converter=my_converter)]

    @app.default
    def foo(*, foo: Annotated[my_int, Parameter(name="--bar")] = True):  # pyright: ignore[reportInvalidTypeForm]
        pass

    assert_parse_args(foo, "--bar=10", foo=5)


def test_boolean_flag_group_default_parameter_resolution_1(app, assert_parse_args):
    food_group = Group("Food", default_parameter=Parameter(negative_bool="--group-"))

    @app.default
    def foo(flag: Annotated[bool, Parameter(group=food_group)]):
        pass

    assert_parse_args(foo, "--group-flag", False)


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--bar", True),
        ("--no-bar", False),
    ],
)
def test_boolean_flag_custom_positive(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_flag: Annotated[bool, Parameter(name="--bar")] = True):
        pass

    assert_parse_args(foo, cmd_str, expected)


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--bar", True),
        ("--no-bar", False),
    ],
)
def test_boolean_flag_custom_short_positive(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_flag: Annotated[bool, Parameter(name=["--bar", "-b"])] = True):
        pass

    assert_parse_args(foo, cmd_str, expected)


@pytest.mark.parametrize(
    "cmd_str,expected",
    [
        ("--my-flag", True),
        ("--yesnt-my-flag", False),
    ],
)
def test_boolean_flag_custom_negative(app, cmd_str, expected, assert_parse_args):
    @app.default
    def foo(my_flag: Annotated[bool, Parameter(negative="--yesnt-my-flag")] = True):
        pass

    assert_parse_args(foo, cmd_str, expected)


@pytest.mark.parametrize(
    "negative",
    ["", (), []],
)
def test_boolean_flag_disable_negative(app, negative, assert_parse_args):
    @app.default
    def foo(my_flag: Annotated[bool, Parameter(negative=negative)] = True):
        pass

    assert_parse_args(foo, "--my-flag", True)
    with pytest.raises(UnknownOptionError):
        assert_parse_args(foo, "--no-my-flag", True)
