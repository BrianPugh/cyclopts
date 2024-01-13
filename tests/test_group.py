import itertools
import sys
from unittest.mock import Mock

import pytest

import cyclopts.group
from cyclopts import App, Group, Parameter
from cyclopts.group import sort_groups

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


class SentinelError(Exception):
    pass


def upper(type_, *args: str):
    return args[0].upper()


def test_group_parameter_converter(app, assert_parse_args):
    def converter(**kwargs):
        return {k: v.upper() for k, v in kwargs.items()}

    food_group = Group("Food", converter=converter)

    @app.default
    def foo(
        ice_cream: Annotated[str, Parameter(group=food_group)],
        cone: Annotated[str, Parameter(group="Food")],
    ):
        pass

    assert_parse_args(foo, "chocolate sugar", "CHOCOLATE", "SUGAR")


def test_group_parameter_converter_delete_arg(app, assert_parse_args):
    def converter(**kwargs):
        # This doesn't have a "cone" key in the response, meaning it should not be
        # in the resulting bound arguments.
        return {k: v.upper() for k, v in kwargs.items() if k != "cone"}

    food_group = Group("Food", converter=converter)

    @app.default
    def foo(
        ice_cream: Annotated[str, Parameter(group=food_group)],
        cone: Annotated[str, Parameter(group="Food")] = "waffle",
    ):
        pass

    assert_parse_args(foo, "chocolate sugar", "CHOCOLATE")


def test_group_default_parameter_converter(app, assert_parse_args):
    food_group = Group("Food", default_parameter=Parameter(converter=upper))

    @app.default
    def foo(ice_cream: Annotated[str, Parameter(group=food_group)]):
        pass

    assert_parse_args(foo, "chocolate", "CHOCOLATE")


def test_group_command_default_parameter_resolution(app):
    app_validator = Mock()
    sub_app_validator = Mock()
    command_validator = Mock()
    command_group_validator = Mock()

    app.validator = app_validator
    app.command(bar := App("bar", validator=sub_app_validator))

    @bar.command(validator=command_validator, group=Group("Test", validator=command_group_validator))
    def cmd(foo=5):
        return 100

    assert 100 == app("bar cmd")

    app_validator.assert_not_called()
    command_group_validator.assert_called_once()

    sub_app_validator.assert_not_called()
    command_validator.assert_called_once()


def test_group_default_parameter_validator(app):
    validator = Mock()

    food_group = Group("Food", default_parameter=Parameter(validator=validator))

    @app.default
    def foo(ice_cream: Annotated[str, Parameter(group=food_group)]):
        pass

    app.parse_args("chocolate")
    validator.assert_called_once()


def test_group_validator(app):
    validator = Mock()

    group = Group("Spices", validator=validator)

    @app.default
    def foo(
        salt: Annotated[bool, Parameter("--rock-salt", group=group)] = False,
        pepper: Annotated[bool, Parameter("--peppercorn", group=group)] = False,
        ketchup: bool = False,
    ):
        pass

    app.parse_args("--rock-salt --peppercorn --ketchup")

    validator.assert_called_once_with(salt=True, pepper=True)


def test_group_sorted_classmethod_basic(mocker):
    mock_sort_key_counter = mocker.patch("cyclopts.group._sort_key_counter")
    mock_sort_key_counter.__next__.side_effect = itertools.count()

    g4 = Group("unsorted group")
    g1 = Group.create_ordered("foo")
    g2 = Group.create_ordered("bar")
    g3 = Group.create_ordered("baz", sort_key="non-int value")

    assert g1.sort_key == (cyclopts.group.NO_USER_SORT_KEY, 0)
    assert g2.sort_key == (cyclopts.group.NO_USER_SORT_KEY, 1)
    assert g3.sort_key == (("non-int value",), 2)
    assert g4.sort_key is None

    res = sort_groups([g1, g2, g3, g4], ["a", "b", "c", "d"])
    assert ([g3, g1, g2, g4], ["c", "a", "b", "d"]) == res
