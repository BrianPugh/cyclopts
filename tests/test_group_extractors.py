import sys
from types import ModuleType

import pytest

from cyclopts import App, Group, Parameter
from cyclopts.command_spec import CommandSpec
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


def test_groups_from_app_resolve_lazy():
    """Test that resolve_lazy parameter controls whether lazy commands are resolved.

    With resolve_lazy=False (default), unresolved lazy commands appear as stubs
    with their pre-specified help text but without triggering module imports.
    With resolve_lazy=True, lazy commands are fully imported and resolved.
    """
    test_module = ModuleType("test_lazy_module")
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        app = App(help_flags=[], version_flags=[])

        # Register a lazy command with pre-specified help
        app.command("test_lazy_module:cmd", name="lazy-cmd", help="Lazy help text.")

        # Also register a regular command
        @app.command
        def regular():
            pass

        # Verify lazy command is not resolved
        assert isinstance(app._commands["lazy-cmd"], CommandSpec)
        assert not app._commands["lazy-cmd"].is_resolved

        # With resolve_lazy=False (default), lazy commands appear as stubs
        groups = groups_from_app(app, resolve_lazy=False)
        all_names = [name for _, cmds in groups for cmd in cmds for name in cmd.names]
        assert "regular" in all_names
        assert "lazy-cmd" in all_names

        # The stub should carry the pre-specified help text
        lazy_cmds = [cmd for _, cmds in groups for cmd in cmds if "lazy-cmd" in cmd.names]
        assert len(lazy_cmds) == 1
        assert lazy_cmds[0].app.help == "Lazy help text."

        # Lazy command should still be unresolved (stub, not imported)
        assert not app._commands["lazy-cmd"].is_resolved

        # With resolve_lazy=True, should include fully resolved lazy commands
        groups = groups_from_app(app, resolve_lazy=True)
        all_names = [name for _, cmds in groups for cmd in cmds for name in cmd.names]
        assert "regular" in all_names
        assert "lazy-cmd" in all_names

        # Lazy command should now be resolved
        assert app._commands["lazy-cmd"].is_resolved
    finally:
        del sys.modules["test_lazy_module"]


def test_groups_from_app_lazy_hidden():
    """Test that lazy commands with show=False are excluded from groups."""
    test_module = ModuleType("test_lazy_module_hidden")
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module_hidden"] = test_module

    try:
        app = App(help_flags=[], version_flags=[])

        # Register a hidden lazy command
        app.command("test_lazy_module_hidden:cmd", name="hidden-cmd", show=False)

        # Also register a visible regular command
        @app.command
        def visible():
            pass

        groups = groups_from_app(app, resolve_lazy=False)
        all_names = [name for _, cmds in groups for cmd in cmds for name in cmd.names]
        assert "visible" in all_names
        assert "hidden-cmd" not in all_names

        # Should not have resolved the hidden command
        assert isinstance(app._commands["hidden-cmd"], CommandSpec)
        assert not app._commands["hidden-cmd"].is_resolved
    finally:
        del sys.modules["test_lazy_module_hidden"]
