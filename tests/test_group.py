import itertools
from typing import Annotated, Sequence
from unittest.mock import Mock

import pytest

import cyclopts.group
from cyclopts import App, ArgumentCollection, Group, Parameter, Token
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


def test_group_sort_key_generator():
    """Test that Group.sort_key accepts and processes generators."""

    def sort_key_gen():
        yield 5

    # Test with generator function
    g1 = Group("Test1", sort_key=sort_key_gen())
    assert g1.sort_key == 5

    # Test with generator expression
    g2 = Group("Test2", sort_key=(x for x in [10]))
    assert g2.sort_key == 10

    # Test with create_ordered and generator
    g3 = Group.create_ordered("Test3", sort_key=(x * 2 for x in [7]))
    # create_ordered wraps the sort_key in a tuple with a counter
    assert g3.sort_key[0] == 14  # pyright: ignore[reportOptionalSubscript]


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


def test_multiple_anonymous_groups(app, assert_parse_args):
    """Test to ensure that multiple anonymous Groups do not get combined.

    https://github.com/BrianPugh/cyclopts/issues/479
    """

    def require_all_or_none(args: ArgumentCollection) -> None:
        got_args = args.filter_by(has_tokens=True)
        if len(got_args) == 0 or len(got_args) == len(args):
            return
        got_str = ", ".join(a.name for a in got_args)
        wanted_str = ", ".join(a.name for a in args)
        error_msg = f"Needs all of: {wanted_str}. Now only got: {got_str}."
        raise ValueError(error_msg)

    group1 = Group(validator=require_all_or_none)
    group2 = Group(validator=require_all_or_none)

    @app.default
    def default(
        *,
        foo: Annotated[str, Parameter(group=group1)] = "",
        bar: Annotated[str, Parameter(group=group1)] = "",
        fizz: Annotated[str, Parameter(group=group2)] = "",
        buzz: Annotated[str, Parameter(group=group2)] = "",
    ):
        pass

    with pytest.raises(ValidationError):
        app("--foo foo", exit_on_error=False)

    with pytest.raises(ValidationError):
        app("--fizz fizz", exit_on_error=False)

    with pytest.raises(ValidationError):
        app("--foo foo --bar bar --fizz fizz", exit_on_error=False)

    assert_parse_args(default, "--foo foo --bar bar", foo="foo", bar="bar")
    assert_parse_args(
        default,
        "--foo foo --bar bar --fizz fizz --buzz buzz",
        foo="foo",
        bar="bar",
        fizz="fizz",
        buzz="buzz",
    )


def test_nameless_group_parameters_in_help(app, console):
    """Test that parameters assigned to nameless groups still appear in default Parameters group.

    When a parameter is assigned to a nameless Group (where group.show == False),
    it should still appear in the default "Parameters" group in the help output
    if it's not assigned to any named group.
    """
    nameless_group = Group(validator=lambda args: None)  # Nameless group with validator

    @app.default
    def default(
        *,
        foo: Annotated[str, Parameter(group=nameless_group, help="Parameter in nameless group")] = "",
        bar: Annotated[str, Parameter(group=nameless_group, help="Another parameter in nameless group")] = "",
        baz: Annotated[str, Parameter(help="Parameter in default group")] = "",
    ):
        """Test function with parameters in nameless and default groups."""
        pass

    # Get the help output
    with console.capture() as capture:
        app(["--help"], console=console)

    help_output = capture.get()

    # Check that foo and bar parameters appear in the help
    # They should be in the default "Parameters" group even though assigned to nameless group
    assert "--foo" in help_output
    assert "--bar" in help_output
    assert "--baz" in help_output
    assert "Parameter in nameless group" in help_output
    assert "Another parameter in nameless group" in help_output
    assert "Parameter in default group" in help_output

    # Check that the Parameters group header appears
    assert "Parameters" in help_output


def test_nameless_group_validators_still_work(app, assert_parse_args):
    """Test that validators in nameless groups still function correctly."""

    def require_both(args: ArgumentCollection) -> None:
        got_args = args.filter_by(has_tokens=True)
        if len(got_args) == 1:
            raise ValueError("Must provide both foo and bar together")

    nameless_group = Group(validator=require_both)

    @app.default
    def default(
        *,
        foo: Annotated[str, Parameter(group=nameless_group)] = "",
        bar: Annotated[str, Parameter(group=nameless_group)] = "",
        baz: str = "",
    ):
        pass

    # Should work when both are provided
    assert_parse_args(default, "--foo hello --bar world", foo="hello", bar="world")

    # Should work when neither are provided
    assert_parse_args(default, "--baz test", baz="test")

    # Should fail when only one is provided
    with pytest.raises(ValidationError):
        app("--foo hello", exit_on_error=False)


def test_multiple_parameters_mixed_groups(app, console):
    """Test that multiple parameters with different group configurations work correctly.

    This tests the edge case where resolved_groups accumulation could cause bugs.
    """
    nameless_group1 = Group(validator=lambda args: None)  # First nameless group
    nameless_group2 = Group(validator=lambda args: None)  # Second nameless group
    named_group = Group(name="Special Options", help="Special configuration options")

    @app.default
    def default(
        *,
        foo: Annotated[str, Parameter(group=nameless_group1, help="First nameless group param")] = "",
        bar: Annotated[str, Parameter(group=nameless_group2, help="Second nameless group param")] = "",
        special: Annotated[str, Parameter(group=named_group, help="Named group param")] = "",
        normal: Annotated[str, Parameter(help="Normal param without explicit group")] = "",
    ):
        """Test function with mixed group configurations."""
        pass

    # Get the help output
    with console.capture() as capture:
        app(["--help"], console=console)

    help_output = capture.get()

    # All parameters should appear in help
    assert "--foo" in help_output
    assert "--bar" in help_output
    assert "--special" in help_output
    assert "--normal" in help_output

    # Check that both default Parameters group and named group appear
    assert "Parameters" in help_output
    assert "Special Options" in help_output

    # Check descriptions appear
    assert "First nameless group param" in help_output
    assert "Second nameless group param" in help_output
    assert "Named group param" in help_output
    assert "Normal param without explicit group" in help_output
