import pytest

from cyclopts import App, Group, Parameter
from cyclopts.group_extractors import RegisteredCommand, groups_from_app


def test_groups_annotated_invalid_recursive_definition():
    """A default_parameter isn't allowed to have a group set, as it would introduce a paradox."""
    default_parameter = Parameter(group="Drink")  # pyright: ignore[reportGeneralTypeIssues]
    with pytest.raises(ValueError):
        Group("Food", default_parameter=default_parameter)


def test_groups_from_app_implicit():
    def validator(argument_collection):
        pass

    app = App(help_flags=[], version_flags=[])

    @app.command(group="Food")
    def food1():
        pass

    @app.command(group=Group("Food", validator=validator))
    def food2():
        pass

    @app.command(group="Drink")
    def drink1():
        pass

    actual_groups = groups_from_app(app)
    assert actual_groups == [
        (Group("Drink"), [RegisteredCommand(("drink1",), app["drink1"])]),
        (
            Group("Food", validator=validator),
            [RegisteredCommand(("food1",), app["food1"]), RegisteredCommand(("food2",), app["food2"])],
        ),
    ]


def test_commands_groups_name_collision(app):
    @app.command(group=Group("Foo"))
    def foo():
        pass

    @app.command(group=Group("Foo"))
    def bar():
        pass

    with pytest.raises(ValueError):
        groups_from_app(app)


def test_app_registered_with_multiple_names():
    """Test that when an app is registered with custom names, all names are collected."""
    app = App(help_flags=[], version_flags=[])
    sub = App()

    app.command(sub, name="foo", alias=["bar", "baz"])

    # Verify that sub's internal name wasn't mutated during registration
    assert sub._name is None

    groups = groups_from_app(app)
    assert len(groups) == 1
    assert len(groups[0][1]) == 1

    registered_command = groups[0][1][0]
    assert set(registered_command.names) == {"foo", "bar", "baz"}
    assert registered_command.app is sub


def test_same_app_registered_multiple_times():
    """Test that the same app instance registered separately with different names is tracked correctly."""
    app = App(help_flags=[], version_flags=[])
    sub = App()

    app.command(sub, name="first")
    app.command(sub, name="second")

    # Verify that sub's internal name wasn't mutated during registration
    assert sub._name is None

    groups = groups_from_app(app)
    assert len(groups) == 1
    assert len(groups[0][1]) == 1

    registered_command = groups[0][1][0]
    assert set(registered_command.names) == {"first", "second"}
    assert registered_command.app is sub
