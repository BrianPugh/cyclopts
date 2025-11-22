"""Tests for lazy command loading via import path strings."""

import sys
from types import ModuleType

import pytest

from cyclopts import App, Group
from cyclopts.command_spec import CommandSpec
from cyclopts.exceptions import CommandCollisionError


def test_command_spec_basic_function(app):
    """Test CommandSpec can resolve a basic function."""
    spec = CommandSpec(import_path="os.path:join")
    resolved = spec.resolve(app)

    assert isinstance(resolved, App)
    assert resolved.default_command is not None
    assert resolved.default_command.__name__ == "join"


def test_command_spec_invalid_format(app):
    """Test CommandSpec raises error for invalid import path format."""
    spec = CommandSpec(import_path="invalid_format_no_colon")

    with pytest.raises(ValueError, match="Invalid import path"):
        spec.resolve(app)


def test_command_spec_module_not_found(app):
    """Test CommandSpec raises ImportError for non-existent module."""
    spec = CommandSpec(import_path="nonexistent_module:func")

    with pytest.raises(ImportError, match="Cannot import module"):
        spec.resolve(app)


def test_command_spec_attribute_not_found(app):
    """Test CommandSpec raises AttributeError for non-existent attribute."""
    spec = CommandSpec(import_path="os:nonexistent_function")

    with pytest.raises(AttributeError, match="has no attribute"):
        spec.resolve(app)


def test_command_spec_caching(app):
    """Test CommandSpec caches the resolved App."""
    spec = CommandSpec(import_path="os.path:join")

    resolved1 = spec.resolve(app)
    resolved2 = spec.resolve(app)

    assert resolved1 is resolved2  # Same object, not just equal


def test_lazy_command_registration():
    """Test registering a lazy command via import path."""
    app = App()

    # Register a lazy command
    app.command("os.path:join", name="join-path")

    # Command should be in the app
    assert "join-path" in app

    # Should be a CommandSpec before access
    assert isinstance(app._commands["join-path"], CommandSpec)


def test_lazy_command_execution(app):
    """Test executing a lazy command."""
    # Create a fake module with a command function
    test_module = ModuleType("test_lazy_module")
    test_module.test_command = lambda x: f"executed with {x}"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        app.command("test_lazy_module:test_command", name="lazy")

        # Access the command - should resolve it
        resolved = app["lazy"]
        assert isinstance(resolved, App)
        assert resolved.default_command is not None

        # Execute the command
        result = app(["lazy", "--x", "value"])
        assert result == "executed with value"
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_command_name_transform(app):
    """Test that name transform is applied to lazy command names."""
    test_module = ModuleType("test_lazy_module")
    test_module.create_user = lambda: "created"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Don't specify name - should auto-derive from function name
        app.command("test_lazy_module:create_user")

        # Should be registered with transformed name (underscores -> hyphens)
        assert "create-user" in app
        assert "create_user" not in app
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_command_with_alias(app):
    """Test lazy command with alias."""
    test_module = ModuleType("test_lazy_module")
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        app.command("test_lazy_module:cmd", name="command", alias=["c", "cmd-alias"])

        assert "command" in app
        assert "c" in app
        assert "cmd-alias" in app

        # All should resolve to the same App
        assert app["command"] is app["c"] is app["cmd-alias"]
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_command_collision(app):
    """Test that lazy commands detect collisions."""

    @app.command
    def existing():
        pass

    with pytest.raises(CommandCollisionError):
        app.command("os.path:join", name="existing")


def test_lazy_command_help(app, console):
    """Test that help generation works with lazy commands."""
    test_module = ModuleType("test_lazy_module")

    def cmd(x):
        """Test command documentation."""
        return x

    test_module.cmd = cmd  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        app.command("test_lazy_module:cmd", name="lazy-cmd")

        # Generate help - should resolve the lazy command
        with console.capture() as capture:
            app(["--help"], console=console)

        output = capture.get()
        # The command name used for registration should appear
        assert "lazy-cmd" in output or "cmd" in output
        # The help should show the command documentation
        assert "Test command documentation" in output
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_and_immediate_commands_mixed(app):
    """Test mixing lazy and immediate command registration."""
    test_module = ModuleType("test_lazy_module")
    test_module.lazy_func = lambda: "lazy"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Immediate command
        @app.command
        def immediate():
            return "immediate"

        # Lazy command
        app.command("test_lazy_module:lazy_func", name="lazy")

        # Both should work
        assert app(["immediate"]) == "immediate"
        assert app(["lazy"]) == "lazy"
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_command_not_resolved_until_accessed(app):
    """Test that lazy commands are not resolved until they are accessed."""
    # We can't easily test that a module isn't imported without filesystem access,
    # so instead we verify the CommandSpec is created without resolution
    app.command("os.path:join", name="lazy")

    # Should be CommandSpec, not resolved App
    assert isinstance(app._commands["lazy"], CommandSpec)
    assert not app._commands["lazy"].is_resolved

    # Now access it
    _ = app["lazy"]

    # Should now be resolved
    assert app._commands["lazy"].is_resolved


def test_lazy_command_app_kwargs(app):
    """Test that app_kwargs are passed when wrapping a function."""
    test_module = ModuleType("test_lazy_module")

    def test_func(x: int):
        """Test function."""
        return x * 2

    test_module.test_func = test_func  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Register with custom app configuration
        app.command(
            "test_lazy_module:test_func",
            name="custom",
            help="Custom help text",
            show=True,
        )

        resolved = app["custom"]
        assert resolved.help == "Custom help text"
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_command_parse_commands(app):
    """Test that parse_commands works with lazy commands."""
    test_module = ModuleType("test_lazy_module")
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        app.command("test_lazy_module:cmd", name="lazy")

        # Parse commands should resolve the lazy command
        command_chain, apps, unused = app.parse_commands(["lazy", "arg1", "arg2"])

        assert command_chain == ("lazy",)
        assert len(apps) == 2  # root app and lazy command app
        assert isinstance(apps[-1], App)
        assert unused == ["arg1", "arg2"]
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_command_iteration(app):
    """Test that iterating over commands includes lazy commands."""
    test_module = ModuleType("test_lazy_module")
    test_module.cmd = lambda: None  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        app.command("test_lazy_module:cmd", name="lazy")

        @app.command
        def immediate():
            pass

        # Iteration should include both
        commands = list(app)
        assert "lazy" in commands
        assert "immediate" in commands
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_command_contains(app):
    """Test that 'in' operator works with lazy commands."""
    test_module = ModuleType("test_lazy_module")
    test_module.cmd = lambda: None  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        app.command("test_lazy_module:cmd", name="lazy")

        # Should work without resolving
        assert "lazy" in app
        assert "nonexistent" not in app
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_command_resolves_to_app_instance():
    """Test that if the import path points to an App, it's used directly."""
    test_module = ModuleType("test_lazy_module")
    test_module.my_app = App(name="subapp", help="Subapp help")  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        app = App()
        # Use explicit name since we're registering via import path
        app.command("test_lazy_module:my_app", name="subapp")

        # Resolve it
        resolved = app["subapp"]

        # Should be the same App instance, not wrapped
        assert resolved is test_module.my_app
        assert resolved.help == "Subapp help"
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_subcommands(app):
    """Test lazy loading in nested command structures."""
    test_module = ModuleType("test_lazy_module")
    test_module.subcmd = lambda: "sub result"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Create a subapp with a lazy command
        user_app = App(name="user")
        user_app.command("test_lazy_module:subcmd", name="create")
        app.command(user_app)

        # Execute nested lazy command
        result = app(["user", "create"])
        assert result == "sub result"
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_command_custom_name_in_help(app, console):
    """Test that custom name (not function name) appears in help.

    Regression test for bug where lazy commands with custom names
    showed the function name instead of the custom name in help output.
    """
    test_module = ModuleType("test_lazy_module")

    def list_users(limit: int = 10):
        """List all user accounts."""
        return f"listing {limit} users"

    test_module.list_users = list_users  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Register with custom name "list" instead of function name "list_users"
        app.command("test_lazy_module:list_users", name="list")

        # Generate help
        with console.capture() as capture:
            app(["--help"], console=console)

        output = capture.get()

        # Should show custom name "list", NOT "list-users" (transformed function name)
        assert "list" in output.lower()
        # Make sure it's not showing the function name
        assert "list-users" not in output
        # Help text should still appear
        assert "List all user accounts" in output
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_function_inherits_parent_help_flags():
    """Test that lazy function commands inherit parent's help_flags.

    This proves behavioral equivalence with direct function registration.
    """
    test_module = ModuleType("test_lazy_module")
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Create parent with custom help flags
        parent = App(name="parent", help_flags=["--custom-help", "-ch"])

        # Test 1: Direct function registration
        def direct_func():
            return "direct"

        parent.command(direct_func, name="direct")
        direct_app = parent["direct"]
        assert direct_app.help_flags == ("--custom-help", "-ch")

        # Test 2: Lazy function registration
        parent.command("test_lazy_module:cmd", name="lazy")
        lazy_app = parent["lazy"]
        assert lazy_app.help_flags == ("--custom-help", "-ch")

        # Both should be identical
        assert direct_app.help_flags == lazy_app.help_flags
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_function_inherits_parent_version_flags():
    """Test that lazy function commands inherit parent's version_flags.

    This proves behavioral equivalence with direct function registration.
    """
    test_module = ModuleType("test_lazy_module")
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Create parent with custom version flags
        parent = App(name="parent", version_flags=["--custom-version", "-cv"])

        # Test 1: Direct function registration
        def direct_func():
            return "direct"

        parent.command(direct_func, name="direct")
        direct_app = parent["direct"]
        assert direct_app.version_flags == ("--custom-version", "-cv")

        # Test 2: Lazy function registration
        parent.command("test_lazy_module:cmd", name="lazy")
        lazy_app = parent["lazy"]
        assert lazy_app.version_flags == ("--custom-version", "-cv")

        # Both should be identical
        assert direct_app.version_flags == lazy_app.version_flags
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_function_inherits_parent_groups():
    """Test that lazy function commands inherit parent's group settings.

    This proves behavioral equivalence with direct function registration.
    """
    test_module = ModuleType("test_lazy_module")
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Create parent with custom groups
        custom_cmd_group = Group("Custom Commands", sort_key=1)
        custom_param_group = Group("Custom Parameters", sort_key=2)
        custom_arg_group = Group("Custom Arguments", sort_key=3)

        parent = App(
            name="parent",
            group_commands=custom_cmd_group,
            group_parameters=custom_param_group,
            group_arguments=custom_arg_group,
        )

        # Test 1: Direct registration
        direct_app = App(name="direct")
        parent.command(direct_app)
        assert direct_app._group_commands == custom_cmd_group
        assert direct_app._group_parameters == custom_param_group
        assert direct_app._group_arguments == custom_arg_group

        # Test 2: Lazy registration
        parent.command("test_lazy_module:cmd", name="lazy")
        lazy_app = parent["lazy"]
        assert lazy_app._group_commands == custom_cmd_group
        assert lazy_app._group_parameters == custom_param_group
        assert lazy_app._group_arguments == custom_arg_group

        # Both should be identical
        assert direct_app._group_commands == lazy_app._group_commands
        assert direct_app._group_parameters == lazy_app._group_parameters
        assert direct_app._group_arguments == lazy_app._group_arguments
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_app_inherits_parent_groups_when_unset():
    """Test that lazy App imports inherit parent's unset groups.

    This proves behavioral equivalence with direct App registration.
    """
    test_module = ModuleType("test_lazy_module")
    # Create an App without groups set (None)
    test_module.subapp = App(name="subapp", help="Subapp help")  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Create parent with custom groups
        custom_cmd_group = Group("Parent Commands", sort_key=1)
        custom_param_group = Group("Parent Parameters", sort_key=2)

        parent = App(
            name="parent",
            group_commands=custom_cmd_group,
            group_parameters=custom_param_group,
        )

        # Test 1: Direct registration
        direct_subapp = App(name="direct-subapp", help="Direct subapp")
        parent.command(direct_subapp)
        assert direct_subapp._group_commands == custom_cmd_group
        assert direct_subapp._group_parameters == custom_param_group

        # Test 2: Lazy registration
        parent.command("test_lazy_module:subapp", name="subapp")
        lazy_subapp = parent["subapp"]
        assert lazy_subapp._group_commands == custom_cmd_group
        assert lazy_subapp._group_parameters == custom_param_group

        # Both should be identical
        assert direct_subapp._group_commands == lazy_subapp._group_commands
        assert direct_subapp._group_parameters == lazy_subapp._group_parameters
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_app_doesnt_override_existing_groups():
    """Test that lazy App imports don't override their own groups.

    An imported App with its own groups should keep them, not inherit parent's.
    """
    test_module = ModuleType("test_lazy_module")
    # Create an App WITH groups set
    subapp_group = Group("Subapp Commands", sort_key=99)
    test_module.subapp = App(name="subapp", group_commands=subapp_group)  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Create parent with different groups
        parent_group = Group("Parent Commands", sort_key=1)
        parent = App(name="parent", group_commands=parent_group)

        # Lazy registration
        parent.command("test_lazy_module:subapp", name="subapp")
        lazy_subapp = parent["subapp"]

        # Should keep its own group, not inherit parent's
        assert lazy_subapp._group_commands == subapp_group
        assert lazy_subapp._group_commands != parent_group
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_app_rejects_kwargs():
    """Test that CommandSpec rejects app_kwargs for App imports."""
    test_module = ModuleType("test_lazy_module")
    test_module.subapp = App(name="subapp")  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        parent = App(name="parent")

        # Registration succeeds (creates CommandSpec)
        parent.command("test_lazy_module:subapp", name="subapp", help="Custom help")

        # Error occurs during resolution (access)
        with pytest.raises(ValueError, match="Cannot apply configuration to imported App"):
            _ = parent["subapp"]
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_app_name_must_match():
    """Test that CommandSpec validates App name matches CLI command name."""
    test_module = ModuleType("test_lazy_module")
    test_module.subapp = App(name="actual-name")  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        parent = App(name="parent")

        # Register with different name - should fail on resolution
        parent.command("test_lazy_module:subapp", name="wrong-name")

        with pytest.raises(ValueError, match="Imported App name mismatch"):
            _ = parent["wrong-name"]
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_app_name_match_allows_resolution():
    """Test that CommandSpec allows resolution when name matches."""
    test_module = ModuleType("test_lazy_module")
    test_module.subapp = App(name="matching-name")  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        parent = App(name="parent")

        # Register with matching name - should succeed
        parent.command("test_lazy_module:subapp", name="matching-name")
        resolved = parent["matching-name"]

        assert resolved.name[0] == "matching-name"
        assert resolved is test_module.subapp
    finally:
        del sys.modules["test_lazy_module"]


def test_lazy_subapp_help_excludes_help_version_flags(console):
    """Test that lazy-loaded subapps don't show --help/--version in their help.

    Regression test for issue #697.
    When a subapp is registered via lazy loading, its help output should NOT
    include --help and --version flags (matching behavior of direct registration).
    """
    test_module = ModuleType("test_lazy_module")

    # Create a subapp with a default command
    subapp = App(name="greet")

    @subapp.default
    def greet(name: str):
        """Greet a person by name."""
        print(f"Hello, {name}!")

    test_module.subapp = subapp  # type: ignore[attr-defined]
    sys.modules["test_lazy_module"] = test_module

    try:
        # Test lazy registration (should not show --help/--version)
        app_lazy = App(name="App", result_action="return_value")
        app_lazy.command("test_lazy_module:subapp", name="greet")

        with console.capture() as capture:
            app_lazy(["greet", "--help"], console=console)

        output_lazy = capture.get()

        # Lazy registration should not include --help/--version in the subapp help
        assert "--help" not in output_lazy
        assert "--version" not in output_lazy
        assert "Commands" not in output_lazy  # Should not have a Commands section at all
        assert "NAME" in output_lazy
        assert "Greet a person by name" in output_lazy
    finally:
        del sys.modules["test_lazy_module"]
