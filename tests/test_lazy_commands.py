"""Tests for lazy command loading via import path strings."""

import sys
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent
from types import ModuleType

import pytest

from cyclopts import App, Group
from cyclopts.command_spec import CommandSpec
from cyclopts.exceptions import CommandCollisionError


@contextmanager
def temp_module(tmp_path: Path, module_name: str, source: str):
    """Context manager that creates a temporary file-based module.

    Use this when you need AST extraction (requires actual .py file).

    Parameters
    ----------
    tmp_path : Path
        Temporary directory path (from pytest fixture).
    module_name : str
        Name for the module.
    source : str
        Python source code for the module.

    Yields
    ------
    Path
        Path to the created module file.
    """
    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(source)

    sys.path.insert(0, str(tmp_path))
    try:
        yield module_path
    finally:
        sys.path.remove(str(tmp_path))
        if module_name in sys.modules:
            del sys.modules[module_name]


@contextmanager
def fake_module(module_name: str = "test_lazy_module"):
    """Context manager that creates a fake in-memory module.

    Use this for simple tests that don't need AST extraction.

    Parameters
    ----------
    module_name : str
        Name for the module in sys.modules.

    Yields
    ------
    ModuleType
        The fake module object. Add attributes to it before using.
    """
    module = ModuleType(module_name)
    sys.modules[module_name] = module
    try:
        yield module
    finally:
        if module_name in sys.modules:
            del sys.modules[module_name]


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
    with fake_module() as m:
        m.test_command = lambda x: f"executed with {x}"  # type: ignore[attr-defined]
        app.command("test_lazy_module:test_command", name="lazy")

        # Access the command - should resolve it
        resolved = app["lazy"]
        assert isinstance(resolved, App)
        assert resolved.default_command is not None

        # Execute the command
        result = app(["lazy", "--x", "value"])
        assert result == "executed with value"


def test_lazy_command_name_transform(app):
    """Test that name transform is applied to lazy command names."""
    with fake_module() as m:
        m.create_user = lambda: "created"  # type: ignore[attr-defined]

        # Don't specify name - should auto-derive from function name
        app.command("test_lazy_module:create_user")

        # Should be registered with transformed name (underscores -> hyphens)
        assert "create-user" in app
        assert "create_user" not in app


def test_lazy_command_with_alias(app):
    """Test lazy command with alias."""
    with fake_module() as m:
        m.cmd = lambda: "result"  # type: ignore[attr-defined]
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


def test_lazy_command_help(console, tmp_path):
    """Test that help generation works with lazy commands."""
    source = dedent('''\
        def cmd(x):
            """Test command documentation."""
            return x
        ''')
    with temp_module(tmp_path, "test_lazy_help_module", source):
        app = App(name="test")
        app.command("test_lazy_help_module:cmd", name="lazy-cmd")

        # Generate help - should use AST extraction
        with console.capture() as capture:
            with pytest.raises(SystemExit):
                app(["--help"], console=console)

        output = capture.get()
        # The command name used for registration should appear
        assert "lazy-cmd" in output
        # The help should show the command documentation
        assert "Test command documentation" in output


def test_lazy_and_immediate_commands_mixed(app):
    """Test mixing lazy and immediate command registration."""
    with fake_module() as m:
        m.lazy_func = lambda: "lazy"  # type: ignore[attr-defined]

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
    assert app._commands["lazy"]._resolved_app is None

    # Now access it
    _ = app["lazy"]

    # Should now be resolved
    assert app._commands["lazy"]._resolved_app is not None


def test_lazy_command_app_kwargs(app):
    """Test that app_kwargs are passed when wrapping a function."""

    def test_func(x: int):
        """Test function."""
        return x * 2

    with fake_module() as m:
        m.test_func = test_func  # type: ignore[attr-defined]

        # Register with custom app configuration
        app.command(
            "test_lazy_module:test_func",
            name="custom",
            help="Custom help text",
            show=True,
        )

        resolved = app["custom"]
        assert resolved.help == "Custom help text"


def test_lazy_command_parse_commands(app):
    """Test that parse_commands works with lazy commands."""
    with fake_module() as m:
        m.cmd = lambda: "result"  # type: ignore[attr-defined]
        app.command("test_lazy_module:cmd", name="lazy")

        # Parse commands should resolve the lazy command
        command_chain, apps, unused = app.parse_commands(["lazy", "arg1", "arg2"])

        assert command_chain == ("lazy",)
        assert len(apps) == 2  # root app and lazy command app
        assert isinstance(apps[-1], App)
        assert unused == ["arg1", "arg2"]


def test_lazy_command_iteration(app):
    """Test that iterating over commands includes lazy commands."""
    with fake_module() as m:
        m.cmd = lambda: None  # type: ignore[attr-defined]
        app.command("test_lazy_module:cmd", name="lazy")

        @app.command
        def immediate():
            pass

        # Iteration should include both
        commands = list(app)
        assert "lazy" in commands
        assert "immediate" in commands


def test_lazy_command_contains(app):
    """Test that 'in' operator works with lazy commands."""
    with fake_module() as m:
        m.cmd = lambda: None  # type: ignore[attr-defined]
        app.command("test_lazy_module:cmd", name="lazy")

        # Should work without resolving
        assert "lazy" in app
        assert "nonexistent" not in app


def test_lazy_command_resolves_to_app_instance():
    """Test that if the import path points to an App, it's used directly."""
    with fake_module() as m:
        m.my_app = App(name="subapp", help="Subapp help")  # type: ignore[attr-defined]

        app = App()
        # Use explicit name since we're registering via import path
        app.command("test_lazy_module:my_app", name="subapp")

        # Resolve it
        resolved = app["subapp"]

        # Should be the same App instance, not wrapped
        assert resolved is m.my_app
        assert resolved.help == "Subapp help"


def test_lazy_subcommands(app):
    """Test lazy loading in nested command structures."""
    with fake_module() as m:
        m.subcmd = lambda: "sub result"  # type: ignore[attr-defined]

        # Create a subapp with a lazy command
        user_app = App(name="user")
        user_app.command("test_lazy_module:subcmd", name="create")
        app.command(user_app)

        # Execute nested lazy command
        result = app(["user", "create"])
        assert result == "sub result"


def test_lazy_command_custom_name_in_help(console, tmp_path):
    """Test that custom name (not function name) appears in help.

    Regression test for bug where lazy commands with custom names
    showed the function name instead of the custom name in help output.
    """
    source = dedent('''\
        def list_users(limit: int = 10):
            """List all user accounts."""
            return f"listing {limit} users"
        ''')
    with temp_module(tmp_path, "test_custom_name_module", source):
        app = App(name="test")
        # Register with custom name "list" instead of function name "list_users"
        app.command("test_custom_name_module:list_users", name="list")

        # Generate help
        with console.capture() as capture:
            with pytest.raises(SystemExit):
                app(["--help"], console=console)

        output = capture.get()

        # Should show custom name "list", NOT "list-users" (transformed function name)
        assert "list" in output.lower()
        # Make sure it's not showing the function name
        assert "list-users" not in output
        # Help text should still appear
        assert "List all user accounts" in output


def test_lazy_function_inherits_parent_help_flags():
    """Test that lazy function commands inherit parent's help_flags.

    This proves behavioral equivalence with direct function registration.
    """
    with fake_module() as m:
        m.cmd = lambda: "result"  # type: ignore[attr-defined]

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


def test_lazy_function_inherits_parent_version_flags():
    """Test that lazy function commands inherit parent's version_flags.

    This proves behavioral equivalence with direct function registration.
    """
    with fake_module() as m:
        m.cmd = lambda: "result"  # type: ignore[attr-defined]

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


def test_lazy_function_inherits_parent_groups():
    """Test that lazy function commands inherit parent's group settings.

    This proves behavioral equivalence with direct function registration.
    """
    with fake_module() as m:
        m.cmd = lambda: "result"  # type: ignore[attr-defined]

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


def test_lazy_app_inherits_parent_groups_when_unset():
    """Test that lazy App imports inherit parent's unset groups.

    This proves behavioral equivalence with direct App registration.
    """
    with fake_module() as m:
        # Create an App without groups set (None)
        m.subapp = App(name="subapp", help="Subapp help")  # type: ignore[attr-defined]

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


def test_lazy_app_doesnt_override_existing_groups():
    """Test that lazy App imports don't override their own groups.

    An imported App with its own groups should keep them, not inherit parent's.
    """
    # Create an App WITH groups set
    subapp_group = Group("Subapp Commands", sort_key=99)

    with fake_module() as m:
        m.subapp = App(name="subapp", group_commands=subapp_group)  # type: ignore[attr-defined]

        # Create parent with different groups
        parent_group = Group("Parent Commands", sort_key=1)
        parent = App(name="parent", group_commands=parent_group)

        # Lazy registration
        parent.command("test_lazy_module:subapp", name="subapp")
        lazy_subapp = parent["subapp"]

        # Should keep its own group, not inherit parent's
        assert lazy_subapp._group_commands == subapp_group
        assert lazy_subapp._group_commands != parent_group


def test_lazy_app_rejects_kwargs():
    """Test that CommandSpec rejects app_kwargs for App imports."""
    with fake_module() as m:
        m.subapp = App(name="subapp")  # type: ignore[attr-defined]

        parent = App(name="parent")

        # Registration succeeds (creates CommandSpec)
        parent.command("test_lazy_module:subapp", name="subapp", help="Custom help")

        # Error occurs during resolution (access)
        with pytest.raises(ValueError, match="Cannot apply configuration to imported App"):
            _ = parent["subapp"]


def test_lazy_app_name_must_match():
    """Test that CommandSpec validates App name matches CLI command name."""
    with fake_module() as m:
        m.subapp = App(name="actual-name")  # type: ignore[attr-defined]

        parent = App(name="parent")

        # Register with different name - should fail on resolution
        parent.command("test_lazy_module:subapp", name="wrong-name")

        with pytest.raises(ValueError, match="Imported App name mismatch"):
            _ = parent["wrong-name"]


def test_lazy_app_name_match_allows_resolution():
    """Test that CommandSpec allows resolution when name matches."""
    with fake_module() as m:
        m.subapp = App(name="matching-name")  # type: ignore[attr-defined]

        parent = App(name="parent")

        # Register with matching name - should succeed
        parent.command("test_lazy_module:subapp", name="matching-name")
        resolved = parent["matching-name"]

        assert resolved.name[0] == "matching-name"
        assert resolved is m.subapp


def test_lazy_command_not_resolved_when_executing_different_command():
    """Test that lazy commands are not resolved when executing a different command.

    Regression test for issue #709.
    When executing a specific command (e.g., "b run"), other lazy-loaded commands
    (e.g., "c") should NOT be imported/resolved.
    """

    def run_b():
        return "running b"

    def run_c():
        return "running c"

    # Create sub-apps for each module
    b_app = App(name="b", result_action="return_value")
    b_app.command(run_b, name="run")

    c_app = App(name="c", result_action="return_value")
    c_app.command(run_c, name="run")

    with fake_module("test_lazy_module_b") as mb, fake_module("test_lazy_module_c") as mc:
        mb.b_app = b_app  # type: ignore[attr-defined]
        mc.c_app = c_app  # type: ignore[attr-defined]

        # Create parent app with lazy-loaded sub-apps
        app = App(name="a", result_action="return_value")
        app.command("test_lazy_module_b:b_app", name="b")
        app.command("test_lazy_module_c:c_app", name="c")

        # Verify both are registered as lazy (not resolved yet)
        assert isinstance(app._commands["b"], CommandSpec)
        assert isinstance(app._commands["c"], CommandSpec)
        assert app._commands["b"]._resolved_app is None
        assert app._commands["c"]._resolved_app is None

        # Execute only command "b run"
        result = app(["b", "run"])
        assert result == "running b"

        # Command "b" should now be resolved
        assert app._commands["b"]._resolved_app is not None

        # Command "c" should NOT be resolved - this is the bug!
        # Currently fails because groups_from_app() resolves all lazy commands
        assert app._commands["c"]._resolved_app is None, (
            "Lazy command 'c' was resolved even though it was not executed. "
            "This indicates that lazy loading is not working correctly."
        )


def test_lazy_subapp_help_excludes_help_version_flags(console):
    """Test that lazy-loaded subapps don't show --help/--version in their help.

    Regression test for issue #697.
    When a subapp is registered via lazy loading, its help output should NOT
    include --help and --version flags (matching behavior of direct registration).
    """
    # Create a subapp with a default command
    subapp = App(name="greet")

    @subapp.default
    def greet(name: str):
        """Greet a person by name."""
        print(f"Hello, {name}!")

    with fake_module() as m:
        m.subapp = subapp  # type: ignore[attr-defined]

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


# ============================================================================
# AST-based Lazy Help Tests
# ============================================================================


def test_lazy_help_uses_ast_extraction(console, tmp_path):
    """Test that --help for parent app extracts lazy command help via AST without importing."""
    module_name = "ast_test_heavy_module"
    source = dedent(f'''\
        # This module sets a global when imported to track if it was imported
        _IMPORT_TRACKER = "{module_name}_imported"

        import sys
        if not hasattr(sys, _IMPORT_TRACKER):
            setattr(sys, _IMPORT_TRACKER, True)

        def train_model():
            """Train the machine learning model with heavy dependencies."""
            pass
        ''')
    # Ensure the import tracker is not set
    if hasattr(sys, f"{module_name}_imported"):
        delattr(sys, f"{module_name}_imported")

    try:
        with temp_module(tmp_path, module_name, source):
            app = App(name="ml", result_action="return_value")
            app.command(f"{module_name}:train_model", name="train")

            # Generate help - should use AST and NOT import the module
            with console.capture() as capture:
                app(["--help"], console=console)

            output = capture.get()

            # The command should appear in help
            assert "train" in output
            # The docstring should be extracted via AST
            assert "Train the machine learning model" in output

            # CRITICAL: The module should NOT have been imported
            assert not hasattr(sys, f"{module_name}_imported"), (
                "Module was imported during --help! AST extraction should have been used instead."
            )

            # The CommandSpec should still be unresolved
            assert isinstance(app._commands["train"], CommandSpec)
            assert app._commands["train"]._resolved_app is None
    finally:
        if hasattr(sys, f"{module_name}_imported"):
            delattr(sys, f"{module_name}_imported")


def test_lazy_help_raises_on_ast_failure(console):
    """Test that lazy help raises an error when AST extraction fails."""

    def dynamic_func():
        """Dynamic function documentation."""
        return "dynamic"

    # Use a module that exists but where AST extraction will fail
    # (dynamically created module with no .py source file)
    with fake_module("dynamic_module") as m:
        m.dynamic_func = dynamic_func  # type: ignore[attr-defined]

        app = App(name="test", result_action="return_value")
        app.command("dynamic_module:dynamic_func", name="dynamic")

        # Generate help - AST will fail (no .py file), should raise ValueError
        with pytest.raises(ValueError, match="Cannot extract help text"):
            app(["--help"], console=console)

        # The CommandSpec should still be unresolved
        cmd = app._commands["dynamic"]
        assert isinstance(cmd, CommandSpec)
        assert cmd._resolved_app is None


def test_lazy_help_with_explicit_help_avoids_ast_failure(console):
    """Test that providing explicit help avoids AST extraction failure."""

    def dynamic_func():
        """Dynamic function documentation."""
        return "dynamic"

    # Use a module that would fail AST extraction
    with fake_module("dynamic_module2") as m:
        m.dynamic_func = dynamic_func  # type: ignore[attr-defined]

        app = App(name="test", result_action="return_value")
        # Provide explicit help to avoid AST extraction
        app.command("dynamic_module2:dynamic_func", name="dynamic", help="Explicit help works")

        with console.capture() as capture:
            app(["--help"], console=console)

        output = capture.get()

        # The explicit help should be shown
        assert "Explicit help works" in output
        assert "dynamic" in output


def test_lazy_help_explicit_help_kwarg(console, tmp_path):
    """Test that explicit help kwarg is used without AST or import."""
    # Create a module with a DIFFERENT docstring than the help kwarg
    source = dedent('''\
        import sys
        sys.modules["explicit_help_module"]._was_imported = True

        def my_func():
            """This is the actual docstring."""
            pass
        ''')
    module_path = tmp_path / "explicit_help_module.py"
    module_path.write_text(source)

    sys.path.insert(0, str(tmp_path))
    try:
        sentinel = ModuleType("explicit_help_module")
        sentinel._was_imported = False  # type: ignore[attr-defined]
        sys.modules["explicit_help_module"] = sentinel

        app = App(name="test", result_action="return_value")
        # Provide explicit help that differs from docstring
        app.command("explicit_help_module:my_func", name="cmd", help="Explicit help text here")

        with console.capture() as capture:
            app(["--help"], console=console)

        output = capture.get()

        # The explicit help should be shown
        assert "Explicit help text here" in output
        # The actual docstring should NOT be shown
        assert "actual docstring" not in output

        # Module should NOT have been imported
        assert not sentinel._was_imported  # type: ignore[attr-defined]
    finally:
        sys.path.remove(str(tmp_path))
        if "explicit_help_module" in sys.modules:
            del sys.modules["explicit_help_module"]


def test_lazy_help_no_docstring(console, tmp_path):
    """Test that lazy commands without docstrings still appear in help."""
    source = dedent("""\
        def no_doc_func():
            pass
        """)
    with temp_module(tmp_path, "no_doc_module", source):
        app = App(name="test", result_action="return_value")
        app.command("no_doc_module:no_doc_func", name="nodoc")

        with console.capture() as capture:
            app(["--help"], console=console)

        output = capture.get()

        # The command should still appear even without a docstring
        assert "nodoc" in output


def test_lazy_help_multiline_short_description(console, tmp_path):
    """Test that multiline first paragraphs are collapsed correctly."""
    source = dedent('''\
        def multiline_func():
            """This is a multiline
            short description that spans
            several lines.

            This is the long description.
            """
            pass
        ''')
    with temp_module(tmp_path, "multiline_module", source):
        app = App(name="test", result_action="return_value")
        app.command("multiline_module:multiline_func", name="multi")

        with console.capture() as capture:
            app(["--help"], console=console)

        output = capture.get()

        # The multiline first paragraph should be collapsed
        assert "multiline" in output.lower()
        # Long description should not appear in command listing
        assert "long description" not in output.lower()


def test_command_spec_help_property(tmp_path):
    """Test CommandSpec.help property directly."""
    source = dedent('''\
        def test_func():
            """Short description for testing.

            This is the longer description.
            """
            pass
        ''')
    with temp_module(tmp_path, "spec_test_module", source):
        spec = CommandSpec(import_path="spec_test_module:test_func")

        # Should not be resolved yet
        assert spec._resolved_app is None

        # Get full docstring via AST
        doc = spec.help
        assert "Short description for testing." in doc
        assert "longer description" in doc

        # Should still not be resolved
        assert spec._resolved_app is None

        # Calling again should return cached result
        doc2 = spec.help
        assert doc2 == doc


def test_command_spec_help_with_explicit_help():
    """Test that explicit help kwarg is preferred over AST extraction."""
    spec = CommandSpec(
        import_path="os.path:join",  # Has its own docstring
        app_kwargs={"help": "Custom help text"},
    )

    doc = spec.help
    assert doc == "Custom help text"


def test_command_spec_help_raises_on_failure():
    """Test that help property raises ValueError on failure."""
    # Use an import path that can't be resolved via AST
    spec = CommandSpec(import_path="nonexistent_module_12345:func")

    with pytest.raises(ValueError, match="Cannot extract help text"):
        _ = spec.help

    # Calling again should also raise (not cached, will retry)
    with pytest.raises(ValueError, match="Cannot extract help text"):
        _ = spec.help


def test_lazy_help_with_show_false(console, tmp_path):
    """Test that lazy commands with show=False are hidden from help."""
    source = dedent('''\
        def hidden_func():
            """This should be hidden."""
            pass
        ''')
    with temp_module(tmp_path, "hidden_module", source):
        app = App(name="test", result_action="return_value")
        app.command("hidden_module:hidden_func", name="hidden", show=False)

        with console.capture() as capture:
            app(["--help"], console=console)

        output = capture.get()

        # The hidden command should not appear
        assert "hidden" not in output.lower()


def test_resolve_commands(tmp_path):
    """Test that resolve_commands resolves all lazy commands."""
    source = dedent('''\
        def func1():
            """First function."""
            pass

        def func2():
            """Second function."""
            pass
        ''')
    with temp_module(tmp_path, "resolve_commands_module", source):
        app = App(name="test")
        app.command("resolve_commands_module:func1", name="cmd1")
        app.command("resolve_commands_module:func2", name="cmd2")

        # Both should be unresolved
        assert isinstance(app._commands["cmd1"], CommandSpec)
        assert isinstance(app._commands["cmd2"], CommandSpec)
        assert app._commands["cmd1"]._resolved_app is None
        assert app._commands["cmd2"]._resolved_app is None

        # resolve_commands should resolve both and return dict
        commands = app.resolve_commands()

        # Should return resolved App instances
        assert "cmd1" in commands
        assert "cmd2" in commands
        assert isinstance(commands["cmd1"], App)
        assert isinstance(commands["cmd2"], App)

        # Both should now be resolved in the original app too
        assert app._commands["cmd1"]._resolved_app is not None
        assert app._commands["cmd2"]._resolved_app is not None


def test_resolve_commands_catches_errors(tmp_path):
    """Test that resolve_commands raises on invalid lazy commands."""
    source = dedent('''\
        def valid_func():
            """Valid function."""
            pass
        ''')
    with temp_module(tmp_path, "resolve_errors_module", source):
        app = App(name="test")
        app.command("resolve_errors_module:valid_func", name="valid")
        app.command("resolve_errors_module:nonexistent", name="invalid")

        # Should raise AttributeError for the nonexistent function
        with pytest.raises(AttributeError):
            app.resolve_commands()


# ============================================================================
# AST-based Parameter Help Tests
# ============================================================================


def test_lazy_command_help_shows_parameters_without_import(console, tmp_path):
    """Test that --help for a lazy command shows parameters without importing."""
    module_name = "ast_param_test_module"
    source = dedent(f'''\
        import sys
        sys.modules["{module_name}"]._was_imported = True

        def train(model: str, *, epochs: int = 10, lr: float = 0.001):
            """Train a machine learning model.

            Parameters
            ----------
            model
                Model architecture name.
            epochs
                Number of training epochs.
            lr
                Learning rate.
            """
            pass
        ''')

    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(source)
    sys.path.insert(0, str(tmp_path))

    try:
        # Create a sentinel module to track if import happens
        sentinel = ModuleType(module_name)
        sentinel._was_imported = False  # type: ignore[attr-defined]
        sys.modules[module_name] = sentinel

        app = App(name="ml", result_action="return_value")
        app.command(f"{module_name}:train", name="train")

        # Generate help for the command - should NOT import
        with console.capture() as capture:
            app(["train", "--help"], console=console)

        output = capture.get()

        # Should show command description
        assert "Train a machine learning model" in output

        # Should show parameters from AST extraction
        assert "model" in output.lower()
        assert "epochs" in output.lower()
        assert "lr" in output.lower()

        # Should show defaults
        assert "10" in output
        assert "0.001" in output

        # CRITICAL: The module should NOT have been imported
        assert not sentinel._was_imported, "Module was imported during 'train --help'! AST extraction should be used."
    finally:
        sys.path.remove(str(tmp_path))
        if module_name in sys.modules:
            del sys.modules[module_name]


def test_lazy_command_help_with_annotated_parameter(console, tmp_path):
    """Test that --help extracts Parameter metadata from Annotated types."""
    module_name = "ast_annotated_test"
    source = dedent(f'''\
        import sys
        sys.modules["{module_name}"]._was_imported = True

        from typing import Annotated
        from cyclopts import Parameter

        def process(
            verbose: Annotated[bool, Parameter(negative="--quiet")] = False,
            output: Annotated[str, Parameter(help="Output file path.")] = "out.txt"
        ):
            """Process data with options."""
            pass
        ''')

    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(source)
    sys.path.insert(0, str(tmp_path))

    try:
        sentinel = ModuleType(module_name)
        sentinel._was_imported = False  # type: ignore[attr-defined]
        sys.modules[module_name] = sentinel

        app = App(name="test", result_action="return_value")
        app.command(f"{module_name}:process", name="process")

        with console.capture() as capture:
            app(["process", "--help"], console=console)

        output = capture.get()

        # Should show the command
        assert "Process data" in output

        # Should show custom help from Parameter
        assert "Output file path" in output

        # Should show negative option from Parameter
        assert "--quiet" in output

        # Should NOT have imported the module
        assert not sentinel._was_imported
    finally:
        sys.path.remove(str(tmp_path))
        if module_name in sys.modules:
            del sys.modules[module_name]


def test_lazy_command_help_with_positional_args(console, tmp_path):
    """Test that positional arguments are displayed correctly in AST-based help."""
    module_name = "ast_positional_test"
    source = dedent(f'''\
        import sys
        sys.modules["{module_name}"]._was_imported = True

        def greet(name: str, age: int, *, greeting: str = "Hello"):
            """Greet a person.

            Parameters
            ----------
            name
                Person's name.
            age
                Person's age.
            greeting
                Greeting to use.
            """
            pass
        ''')

    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(source)
    sys.path.insert(0, str(tmp_path))

    try:
        sentinel = ModuleType(module_name)
        sentinel._was_imported = False  # type: ignore[attr-defined]
        sys.modules[module_name] = sentinel

        app = App(name="test", result_action="return_value")
        app.command(f"{module_name}:greet", name="greet")

        with console.capture() as capture:
            app(["greet", "--help"], console=console)

        output = capture.get()

        # Should show positional args in usage
        assert "NAME" in output
        assert "AGE" in output

        # Should show descriptions
        assert "Person's name" in output
        assert "Person's age" in output
        assert "Greeting to use" in output

        # Should show default
        assert "Hello" in output

        # Should NOT have imported
        assert not sentinel._was_imported
    finally:
        sys.path.remove(str(tmp_path))
        if module_name in sys.modules:
            del sys.modules[module_name]


def test_lazy_command_help_with_converter_skipped(console, tmp_path):
    """Test that converter (safe-to-skip kwarg) doesn't break AST extraction."""
    module_name = "ast_converter_test"
    source = dedent(f'''\
        import sys
        sys.modules["{module_name}"]._was_imported = True

        from typing import Annotated
        from cyclopts import Parameter

        def my_converter(type_, tokens):
            return int(tokens[0]) * 2

        def double(
            value: Annotated[int, Parameter(converter=my_converter, help="A value to double.")]
        ):
            """Double a value."""
            pass
        ''')

    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(source)
    sys.path.insert(0, str(tmp_path))

    try:
        sentinel = ModuleType(module_name)
        sentinel._was_imported = False  # type: ignore[attr-defined]
        sys.modules[module_name] = sentinel

        app = App(name="test", result_action="return_value")
        app.command(f"{module_name}:double", name="double")

        with console.capture() as capture:
            app(["double", "--help"], console=console)

        output = capture.get()

        # Should show the help text (converter was skipped, but help was extracted)
        assert "A value to double" in output

        # Should NOT have imported
        assert not sentinel._was_imported
    finally:
        sys.path.remove(str(tmp_path))
        if module_name in sys.modules:
            del sys.modules[module_name]


def test_lazy_command_help_with_unevaluable_negative_degrades(tmp_path):
    """Test that unevaluable help-relevant kwargs cause Parameter extraction to fail gracefully.

    When a help-relevant kwarg like `negative=func()` can't be evaluated, the entire
    Parameter extraction fails (correctly), falling back to default behavior. This is
    different from safe-to-skip kwargs like `converter` which are simply skipped while
    other kwargs are still extracted.
    """
    from cyclopts.ast_utils import extract_signature_from_import_path

    module_name = "ast_negative_func_test"
    source = dedent('''\
        from typing import Annotated
        from cyclopts import Parameter

        def get_negative():
            return "--disable"

        def toggle(
            enabled: Annotated[bool, Parameter(negative=get_negative(), help="Custom help")]
        ):
            """Toggle something."""
            pass
        ''')

    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(source)
    sys.path.insert(0, str(tmp_path))

    try:
        sig = extract_signature_from_import_path(f"{module_name}:toggle")

        # The Parameter extraction should have failed because negative=get_negative()
        # is not evaluable and 'negative' is not in the safe-to-skip list.
        # This means no Parameter is extracted for 'enabled'.
        assert "enabled" not in sig.parameters

        # But the docstring and field info should still be available
        assert "Toggle something" in sig.docstring
        assert "enabled" in sig.fields
    finally:
        sys.path.remove(str(tmp_path))
        if module_name in sys.modules:
            del sys.modules[module_name]


def test_lazy_command_help_converter_skipped_but_help_extracted(tmp_path):
    """Test that safe-to-skip kwargs are skipped while help-relevant kwargs are extracted.

    When `converter=my_func` (safe to skip) is combined with `help="..."` (help-relevant),
    the converter is skipped but the help text is still extracted into the Parameter.
    """
    from cyclopts.ast_utils import extract_signature_from_import_path

    module_name = "ast_converter_help_test"
    source = dedent('''\
        from typing import Annotated
        from cyclopts import Parameter

        def my_converter(type_, tokens):
            return int(tokens[0]) * 2

        def double(
            value: Annotated[int, Parameter(converter=my_converter, help="A value to double.")]
        ):
            """Double a value."""
            pass
        ''')

    module_path = tmp_path / f"{module_name}.py"
    module_path.write_text(source)
    sys.path.insert(0, str(tmp_path))

    try:
        sig = extract_signature_from_import_path(f"{module_name}:double")

        # The Parameter SHOULD be extracted because converter is safe to skip
        assert "value" in sig.parameters

        # The help text should be present in the extracted Parameter
        assert sig.parameters["value"].help == "A value to double."

        # The converter should NOT be set (it was skipped)
        assert sig.parameters["value"].converter is None
    finally:
        sys.path.remove(str(tmp_path))
        if module_name in sys.modules:
            del sys.modules[module_name]
