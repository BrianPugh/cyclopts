"""Tests for lazy command loading via import path strings."""

import sys
from types import ModuleType

import pytest

from cyclopts import App, Group
from cyclopts.command_spec import CommandSpec
from cyclopts.completion.bash import generate_completion_script
from cyclopts.exceptions import CommandCollisionError


@pytest.fixture
def lazy_module():
    """Fixture that provides a helper to create lazy-loadable test modules.

    Automatically cleans up all created modules after the test.

    Usage:
        def test_example(lazy_module):
            module = lazy_module()  # creates "test_lazy_module"
            module.cmd = lambda: "result"
            # ... test code ...
            # cleanup happens automatically
    """
    created_modules: list[str] = []

    def create(name: str = "test_lazy_module") -> ModuleType:
        module = ModuleType(name)
        sys.modules[name] = module
        created_modules.append(name)
        return module

    yield create

    for name in created_modules:
        if name in sys.modules:
            del sys.modules[name]


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


def test_lazy_command_execution(app, lazy_module):
    """Test executing a lazy command."""
    test_module = lazy_module()
    test_module.test_command = lambda x: f"executed with {x}"  # type: ignore[attr-defined]

    app.command("test_lazy_module:test_command", name="lazy")

    # Access the command - should resolve it
    resolved = app["lazy"]
    assert isinstance(resolved, App)
    assert resolved.default_command is not None

    # Execute the command
    result = app(["lazy", "--x", "value"])
    assert result == "executed with value"


def test_lazy_command_name_transform(app, lazy_module):
    """Test that name transform is applied to lazy command names."""
    test_module = lazy_module()
    test_module.create_user = lambda: "created"  # type: ignore[attr-defined]

    # Don't specify name - should auto-derive from function name
    app.command("test_lazy_module:create_user")

    # Should be registered with transformed name (underscores -> hyphens)
    assert "create-user" in app
    assert "create_user" not in app


def test_lazy_command_with_alias(app, lazy_module):
    """Test lazy command with alias."""
    test_module = lazy_module()
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]

    app.command("test_lazy_module:cmd", name="command", alias=["c", "cmd-alias"])

    assert "command" in app
    assert "c" in app
    assert "cmd-alias" in app

    # All should resolve to the same App
    assert app["command"] is app["c"] is app["cmd-alias"]


def test_lazy_command_collision(app):
    """Test that lazy commands detect collisions."""

    @app.command
    def existing():
        pass

    with pytest.raises(CommandCollisionError):
        app.command("os.path:join", name="existing")


def test_lazy_command_help(app, console, lazy_module):
    """Test that help generation works with lazy commands.

    Unresolved lazy commands are intentionally excluded from the parent
    --help output (groups_from_app skips them with resolve_lazy=False).
    The COMMAND placeholder in the usage line should still appear, and
    the lazy command should NOT be resolved.
    """
    test_module = lazy_module()

    def cmd(x):
        """Test command documentation."""
        return x

    test_module.cmd = cmd  # type: ignore[attr-defined]

    app.command("test_lazy_module:cmd", name="lazy-cmd")

    # Generate help — should NOT resolve the lazy command
    with console.capture() as capture:
        app(["--help"], console=console)

    output = capture.get()
    # Usage line should indicate commands exist
    assert "COMMAND" in output
    # The lazy command should NOT have been resolved
    assert not app._commands["lazy-cmd"].is_resolved


def test_lazy_and_immediate_commands_mixed(app, lazy_module):
    """Test mixing lazy and immediate command registration."""
    test_module = lazy_module()
    test_module.lazy_func = lambda: "lazy"  # type: ignore[attr-defined]

    # Immediate command
    @app.command
    def immediate():
        return "immediate"

    # Lazy command
    app.command("test_lazy_module:lazy_func", name="lazy")

    # Both should work
    assert app(["immediate"]) == "immediate"
    assert app(["lazy"]) == "lazy"


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


def test_lazy_command_app_kwargs(app, lazy_module):
    """Test that app_kwargs are passed when wrapping a function."""
    test_module = lazy_module()

    def test_func(x: int):
        """Test function."""
        return x * 2

    test_module.test_func = test_func  # type: ignore[attr-defined]

    # Register with custom app configuration
    app.command(
        "test_lazy_module:test_func",
        name="custom",
        help="Custom help text",
        show=True,
    )

    resolved = app["custom"]
    assert resolved.help == "Custom help text"


def test_lazy_command_parse_commands(app, lazy_module):
    """Test that parse_commands works with lazy commands."""
    test_module = lazy_module()
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]

    app.command("test_lazy_module:cmd", name="lazy")

    # Parse commands should resolve the lazy command
    command_chain, apps, unused = app.parse_commands(["lazy", "arg1", "arg2"])

    assert command_chain == ("lazy",)
    assert len(apps) == 2  # root app and lazy command app
    assert isinstance(apps[-1], App)
    assert unused == ["arg1", "arg2"]


def test_lazy_command_iteration(app, lazy_module):
    """Test that iterating over commands includes lazy commands."""
    test_module = lazy_module()
    test_module.cmd = lambda: None  # type: ignore[attr-defined]

    app.command("test_lazy_module:cmd", name="lazy")

    @app.command
    def immediate():
        pass

    # Iteration should include both
    commands = list(app)
    assert "lazy" in commands
    assert "immediate" in commands


def test_lazy_command_contains(app, lazy_module):
    """Test that 'in' operator works with lazy commands."""
    test_module = lazy_module()
    test_module.cmd = lambda: None  # type: ignore[attr-defined]

    app.command("test_lazy_module:cmd", name="lazy")

    # Should work without resolving
    assert "lazy" in app
    assert "nonexistent" not in app


def test_lazy_command_resolves_to_app_instance(lazy_module):
    """Test that if the import path points to an App, it's used directly."""
    test_module = lazy_module()
    test_module.my_app = App(name="subapp", help="Subapp help")  # type: ignore[attr-defined]

    app = App()
    # Use explicit name since we're registering via import path
    app.command("test_lazy_module:my_app", name="subapp")

    # Resolve it
    resolved = app["subapp"]

    # Should be the same App instance, not wrapped
    assert resolved is test_module.my_app
    assert resolved.help == "Subapp help"


def test_lazy_subcommands(app, lazy_module):
    """Test lazy loading in nested command structures."""
    test_module = lazy_module()
    test_module.subcmd = lambda: "sub result"  # type: ignore[attr-defined]

    # Create a subapp with a lazy command
    user_app = App(name="user")
    user_app.command("test_lazy_module:subcmd", name="create")
    app.command(user_app)

    # Execute nested lazy command
    result = app(["user", "create"])
    assert result == "sub result"


def test_lazy_command_custom_name_in_help(app, console, lazy_module):
    """Test that custom name appears in help after the command is resolved.

    Unresolved lazy commands are skipped from parent --help output.
    Once resolved (e.g., via subcommand --help), the custom name is used.
    """
    test_module = lazy_module()

    def list_users(limit: int = 10):
        """List all user accounts."""
        return f"listing {limit} users"

    test_module.list_users = list_users  # type: ignore[attr-defined]

    # Register with custom name "list" instead of function name "list_users"
    app.command("test_lazy_module:list_users", name="list")

    # Before resolution: parent --help should not resolve it
    assert not app._commands["list"].is_resolved

    # Explicitly resolve to check name is correct
    resolved = app["list"]
    assert resolved.name[0] == "list"

    # After resolution it should appear in help
    with console.capture() as capture:
        app(["--help"], console=console)

    output = capture.get()
    assert "list" in output.lower()
    # Make sure it's not showing the function name
    assert "list-users" not in output
    # Help text should appear now that it's resolved
    assert "List all user accounts" in output


def test_lazy_function_inherits_parent_help_flags(lazy_module):
    """Test that lazy function commands inherit parent's help_flags.

    This proves behavioral equivalence with direct function registration.
    """
    test_module = lazy_module()
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]

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


def test_lazy_function_inherits_parent_version_flags(lazy_module):
    """Test that lazy function commands inherit parent's version_flags.

    This proves behavioral equivalence with direct function registration.
    """
    test_module = lazy_module()
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]

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


def test_lazy_function_inherits_parent_groups(lazy_module):
    """Test that lazy function commands inherit parent's group settings.

    This proves behavioral equivalence with direct function registration.
    """
    test_module = lazy_module()
    test_module.cmd = lambda: "result"  # type: ignore[attr-defined]

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


def test_lazy_app_inherits_parent_groups_when_unset(lazy_module):
    """Test that lazy App imports inherit parent's unset groups.

    This proves behavioral equivalence with direct App registration.
    """
    test_module = lazy_module()
    # Create an App without groups set (None)
    test_module.subapp = App(name="subapp", help="Subapp help")  # type: ignore[attr-defined]

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


def test_lazy_app_doesnt_override_existing_groups(lazy_module):
    """Test that lazy App imports don't override their own groups.

    An imported App with its own groups should keep them, not inherit parent's.
    """
    test_module = lazy_module()
    # Create an App WITH groups set
    subapp_group = Group("Subapp Commands", sort_key=99)
    test_module.subapp = App(name="subapp", group_commands=subapp_group)  # type: ignore[attr-defined]

    # Create parent with different groups
    parent_group = Group("Parent Commands", sort_key=1)
    parent = App(name="parent", group_commands=parent_group)

    # Lazy registration
    parent.command("test_lazy_module:subapp", name="subapp")
    lazy_subapp = parent["subapp"]

    # Should keep its own group, not inherit parent's
    assert lazy_subapp._group_commands == subapp_group
    assert lazy_subapp._group_commands != parent_group


def test_lazy_app_rejects_kwargs(lazy_module):
    """Test that CommandSpec rejects app_kwargs for App imports."""
    test_module = lazy_module()
    test_module.subapp = App(name="subapp")  # type: ignore[attr-defined]

    parent = App(name="parent")

    # Registration succeeds (creates CommandSpec)
    parent.command("test_lazy_module:subapp", name="subapp", help="Custom help")

    # Error occurs during resolution (access)
    with pytest.raises(ValueError, match="Cannot apply configuration to imported App"):
        _ = parent["subapp"]


def test_lazy_app_name_must_match(lazy_module):
    """Test that CommandSpec validates App name matches CLI command name."""
    test_module = lazy_module()
    test_module.subapp = App(name="actual-name")  # type: ignore[attr-defined]

    parent = App(name="parent")

    # Register with different name - should fail on resolution
    parent.command("test_lazy_module:subapp", name="wrong-name")

    with pytest.raises(ValueError, match="Imported App name mismatch"):
        _ = parent["wrong-name"]


def test_lazy_app_name_match_allows_resolution(lazy_module):
    """Test that CommandSpec allows resolution when name matches."""
    test_module = lazy_module()
    test_module.subapp = App(name="matching-name")  # type: ignore[attr-defined]

    parent = App(name="parent")

    # Register with matching name - should succeed
    parent.command("test_lazy_module:subapp", name="matching-name")
    resolved = parent["matching-name"]

    assert resolved.name[0] == "matching-name"
    assert resolved is test_module.subapp


def test_lazy_command_not_resolved_when_executing_different_command(lazy_module):
    """Test that lazy commands are not resolved when executing a different command.

    Regression test for issue #709.
    When executing a specific command (e.g., "b run"), other lazy-loaded commands
    (e.g., "c") should NOT be imported/resolved.
    """
    # Create two fake modules for lazy loading
    module_b = lazy_module("test_lazy_module_b")
    module_c = lazy_module("test_lazy_module_c")

    def run_b():
        return "running b"

    def run_c():
        return "running c"

    # Create sub-apps for each module
    b_app = App(name="b", result_action="return_value")
    b_app.command(run_b, name="run")

    c_app = App(name="c", result_action="return_value")
    c_app.command(run_c, name="run")

    module_b.b_app = b_app  # type: ignore[attr-defined]
    module_c.c_app = c_app  # type: ignore[attr-defined]

    # Create parent app with lazy-loaded sub-apps
    app = App(name="a", result_action="return_value")
    app.command("test_lazy_module_b:b_app", name="b")
    app.command("test_lazy_module_c:c_app", name="c")

    # Verify both are registered as lazy (not resolved yet)
    assert isinstance(app._commands["b"], CommandSpec)
    assert isinstance(app._commands["c"], CommandSpec)
    assert not app._commands["b"].is_resolved
    assert not app._commands["c"].is_resolved

    # Execute only command "b run"
    result = app(["b", "run"])
    assert result == "running b"

    # Command "b" should now be resolved
    assert app._commands["b"].is_resolved

    # Command "c" should NOT be resolved - this is the bug!
    # Currently fails because groups_from_app() resolves all lazy commands
    assert not app._commands["c"].is_resolved, (
        "Lazy command 'c' was resolved even though it was not executed. "
        "This indicates that lazy loading is not working correctly."
    )


def test_format_usage_does_not_resolve_lazy_commands(lazy_module):
    """Test that format_usage() does not resolve lazy commands.

    Regression test: format_usage() accessed _registered_commands which
    called __getitem__ on every command, triggering resolution of all
    lazy CommandSpecs.  The fix in #710 addressed groups_from_app but
    missed this code path.
    """
    module_a = lazy_module("test_lazy_fmt_a")
    module_b = lazy_module("test_lazy_fmt_b")

    a_app = App(name="cmd-a")
    module_a.a_app = a_app  # type: ignore[attr-defined]

    b_app = App(name="cmd-b")
    module_b.b_app = b_app  # type: ignore[attr-defined]

    app = App(name="myapp", help_flags=["--help"], version_flags=[], result_action="return_value")
    app.command("test_lazy_fmt_a:a_app", name="cmd-a")
    app.command("test_lazy_fmt_b:b_app", name="cmd-b")

    # Both should be unresolved
    assert not app._commands["cmd-a"].is_resolved
    assert not app._commands["cmd-b"].is_resolved

    # Render --help (output goes to console, we just care about resolution)
    from io import StringIO

    from rich.console import Console

    buf = StringIO()
    console = Console(file=buf, width=70, force_terminal=True)
    app(["--help"], console=console)

    # The usage line should include COMMAND (lazy commands are visible)
    output = buf.getvalue()
    assert "COMMAND" in output

    # Neither lazy command should have been resolved
    assert not app._commands["cmd-a"].is_resolved, (
        "Lazy command 'cmd-a' was resolved during --help rendering. "
        "format_usage() should not trigger lazy resolution."
    )
    assert not app._commands["cmd-b"].is_resolved, (
        "Lazy command 'cmd-b' was resolved during --help rendering. "
        "format_usage() should not trigger lazy resolution."
    )


def test_lazy_subapp_help_excludes_help_version_flags(console, lazy_module):
    """Test that lazy-loaded subapps don't show --help/--version in their help.

    Regression test for issue #697.
    When a subapp is registered via lazy loading, its help output should NOT
    include --help and --version flags (matching behavior of direct registration).
    """
    test_module = lazy_module()

    # Create a subapp with a default command
    subapp = App(name="greet")

    @subapp.default
    def greet(name: str):
        """Greet a person by name."""
        print(f"Hello, {name}!")

    test_module.subapp = subapp  # type: ignore[attr-defined]

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


def test_lazy_command_appears_in_completion_script(lazy_module):
    """Test that lazy commands appear in shell completion scripts.

    Regression test for issue #742.
    Shell completion scripts are generated once and installed, so they need
    ALL commands including lazy-loaded ones.
    """
    test_module = lazy_module()

    def deploy(env: str):
        """Deploy to an environment."""
        return f"deploying to {env}"

    test_module.deploy = deploy  # type: ignore[attr-defined]

    app = App(name="myapp", help_flags=[], version_flags=[])

    # Register lazy command
    app.command("test_lazy_module:deploy", name="deploy")

    # Also register a regular command
    @app.command
    def status():
        """Show status."""
        pass

    # Verify lazy command is not resolved yet
    assert isinstance(app._commands["deploy"], CommandSpec)
    assert not app._commands["deploy"].is_resolved

    # Generate completion script
    script = generate_completion_script(app, "myapp")

    # Both commands should appear in the completion script
    assert "deploy" in script, "Lazy command should appear in completion script"
    assert "status" in script, "Regular command should appear in completion script"

    # The lazy command should now be resolved (completion generation resolves it)
    assert app._commands["deploy"].is_resolved


def test_lazy_nested_commands_appear_in_completion_script(lazy_module):
    """Test that nested lazy commands appear in shell completion scripts.

    Regression test for issue #742.
    """
    test_module = lazy_module()

    # Create a subapp with a command
    subapp = App(name="user")

    @subapp.command
    def create(name: str):
        """Create a user."""
        return f"creating {name}"

    @subapp.command
    def delete(name: str):
        """Delete a user."""
        return f"deleting {name}"

    test_module.user_app = subapp  # type: ignore[attr-defined]

    app = App(name="myapp", help_flags=[], version_flags=[])

    # Register lazy subapp
    app.command("test_lazy_module:user_app", name="user")

    # Verify lazy command is not resolved yet
    assert isinstance(app._commands["user"], CommandSpec)
    assert not app._commands["user"].is_resolved

    # Generate completion script
    script = generate_completion_script(app, "myapp")

    # The subapp and its commands should appear
    assert "user" in script, "Lazy subapp should appear in completion script"
    assert "create" in script, "Nested command 'create' should appear in completion script"
    assert "delete" in script, "Nested command 'delete' should appear in completion script"

    # The lazy command should now be resolved
    assert app._commands["user"].is_resolved


def test_iterate_commands_resolve_lazy(lazy_module):
    """Test that iterate_commands respects the resolve_lazy parameter."""
    from cyclopts.docs.base import iterate_commands

    test_module = lazy_module()

    def lazy_cmd():
        """A lazy command."""
        pass

    test_module.lazy_cmd = lazy_cmd  # type: ignore[attr-defined]

    app = App(name="myapp", help_flags=[], version_flags=[])

    # Register lazy command
    app.command("test_lazy_module:lazy_cmd", name="lazy")

    # Also register a regular command
    @app.command
    def regular():
        """A regular command."""
        pass

    # Verify lazy command is not resolved yet
    assert isinstance(app._commands["lazy"], CommandSpec)
    assert not app._commands["lazy"].is_resolved

    # With resolve_lazy=False, should skip unresolved lazy commands
    commands_without_lazy = list(iterate_commands(app, resolve_lazy=False))
    command_names = [name for name, _ in commands_without_lazy]
    assert "regular" in command_names
    assert "lazy" not in command_names

    # Lazy command should still be unresolved
    assert not app._commands["lazy"].is_resolved

    # With resolve_lazy=True (default), should include lazy commands
    commands_with_lazy = list(iterate_commands(app, resolve_lazy=True))
    command_names = [name for name, _ in commands_with_lazy]
    assert "regular" in command_names
    assert "lazy" in command_names

    # Lazy command should now be resolved
    assert app._commands["lazy"].is_resolved
