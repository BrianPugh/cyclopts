import itertools
from typing import Annotated, Sequence
from unittest.mock import Mock

import pytest

import cyclopts.group
from cyclopts import App, Group, Parameter, Token
from cyclopts.exceptions import ValidationError
from cyclopts.group import sort_groups


def upper(type_, tokens: Sequence[Token]):
    return tokens[0].value.upper()


def test_group_show_property():
    assert Group().show is False
    assert Group("Foo").show is True
    assert Group("Foo", show=False).show is False


def test_group_default_parameter_converter(app, assert_parse_args):
    food_group = Group("Food", default_parameter=Parameter(converter=upper))

    @app.default
    def foo(ice_cream: Annotated[str, Parameter(group=food_group)]):
        pass

    assert_parse_args(foo, "chocolate", "CHOCOLATE")


def test_command_validator(app, assert_parse_args):
    def bar_must_be_1(bar):
        if bar == 1:
            return
        raise ValueError

    @app.command(validator=bar_must_be_1)
    def foo(bar: int):
        pass

    assert_parse_args(foo, "foo 1", bar=1)

    with pytest.raises(ValidationError) as e:
        app("foo 2", exit_on_error=False)

    assert str(e.value) == "Invalid values for command 'foo'."


def test_command_validator_with_message(app, assert_parse_args):
    def bar_must_be_1(bar):
        if bar == 1:
            return
        raise ValueError("The value 'bar' must be 1.")

    @app.command(validator=bar_must_be_1)
    def foo(bar: int):
        pass

    assert_parse_args(foo, "foo 1", bar=1)

    with pytest.raises(ValidationError) as e:
        app("foo 2", exit_on_error=False)

    assert str(e.value) == "Invalid values for command 'foo'. The value 'bar' must be 1."


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

    validator.assert_called_once()
    provided_arguments = validator.call_args_list[0][0][0]
    assert len(provided_arguments) == 2
    assert provided_arguments[0].name == "--rock-salt"
    assert provided_arguments[1].name == "--peppercorn"


def test_group_sort_key_property():
    assert Group().sort_key is None
    assert Group()._sort_key is cyclopts.group.UNSET

    g = Group(sort_key=1)
    assert g.sort_key == 1


@pytest.fixture
def mock_sort_key_counter(mocker):
    mock = mocker.patch("cyclopts.group._sort_key_counter")
    mock.__next__.side_effect = itertools.count()
    return mock


def test_group_sorted_classmethod_basic(mock_sort_key_counter):
    g4 = Group("unsorted group")
    g1 = Group.create_ordered("foo")
    g2 = Group.create_ordered("bar")
    g3 = Group.create_ordered("baz", sort_key="non-int value")

    assert g1.sort_key == (cyclopts.group.UNSET, 0)
    assert g2.sort_key == (cyclopts.group.UNSET, 1)
    assert g3.sort_key == ("non-int value", 2)
    assert g4.sort_key is None

    res = sort_groups([g1, g2, g3, g4], ["a", "b", "c", "d"])
    assert ([g3, g1, g2, g4], ["c", "a", "b", "d"]) == res


def test_group_sorted_classmethod_tuple(mock_sort_key_counter):
    g1 = Group.create_ordered("foo1", sort_key=("tuple", 7))
    g2 = Group.create_ordered("foo2", sort_key=lambda x: ("tuple", 5))

    def f_tuple_str(x):
        return "tuple"

    g3 = Group.create_ordered("foo3", sort_key=(f_tuple_str, 3))
    g4 = Group.create_ordered("foo4", sort_key=("tuple", 3))

    res = sort_groups([g1, g2, g3, g4], ["a", "b", "c", "d"])
    assert ([g3, g4, g2, g1], ["c", "d", "b", "a"]) == res
