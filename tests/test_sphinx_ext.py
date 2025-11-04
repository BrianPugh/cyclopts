"""Tests for the Cyclopts Sphinx extension."""

import sys
from unittest.mock import ANY, MagicMock

import pytest
from docutils.statemachine import StringList

from cyclopts import App
from cyclopts.utils import import_app


class TestImportApp:
    """Test the import_app function."""

    def test_import_with_colon_notation(self, tmp_path):
        """Test importing an app using module:app notation."""
        # Create a temporary module
        module_file = tmp_path / "test_module.py"
        module_file.write_text("""
from cyclopts import App

my_app = App(name="test-app", help="Test application")

@my_app.command
def hello():
    '''Say hello.'''
    pass
""")

        # Add the temp directory to sys.path
        sys.path.insert(0, str(tmp_path))
        try:
            app = import_app("test_module:my_app")
            assert isinstance(app, App)
            assert app.name == ("test-app",)
        finally:
            sys.path.remove(str(tmp_path))

    def test_import_without_colon_finds_app(self, tmp_path):
        """Test importing when app name is not specified."""
        module_file = tmp_path / "test_cli.py"
        module_file.write_text("""
from cyclopts import App

app = App(name="auto-found", help="Automatically found app")
""")

        sys.path.insert(0, str(tmp_path))
        try:
            found_app = import_app("test_cli")
            assert isinstance(found_app, App)
            assert found_app.name == ("auto-found",)
        finally:
            sys.path.remove(str(tmp_path))

    def test_import_module_not_found(self):
        """Test error when module doesn't exist."""
        with pytest.raises(ImportError, match="Cannot import module"):
            import_app("nonexistent_module:app")

    def test_import_app_not_found(self, tmp_path):
        """Test error when specified app doesn't exist in module."""
        module_file = tmp_path / "test_module.py"
        module_file.write_text("""
from cyclopts import App

some_app = App(name="test", help="Test")
""")

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(AttributeError, match="has no attribute 'missing_app'"):
                import_app("test_module:missing_app")
        finally:
            sys.path.remove(str(tmp_path))

    def test_import_not_an_app(self, tmp_path):
        """Test error when object is not a Cyclopts App."""
        # Use a unique module name to avoid conflicts
        module_name = "test_not_app_module"
        module_file = tmp_path / f"{module_name}.py"
        module_file.write_text("not_an_app = 'This is just a string'")

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(TypeError, match="is not a Cyclopts App instance"):
                import_app(f"{module_name}:not_an_app")
        finally:
            # Clean up
            sys.path.remove(str(tmp_path))
            # Remove from sys.modules if it was imported
            if module_name in sys.modules:
                del sys.modules[module_name]


class TestCycloptsDirective:
    """Test the CycloptsDirective class."""

    @pytest.fixture
    def mock_directive(self):
        """Create a mock directive with necessary attributes."""
        from cyclopts.ext.sphinx import CycloptsDirective

        # Create a mock directive instance
        directive = MagicMock(spec=CycloptsDirective)
        directive.arguments = ["test_module:app"]
        directive.options = {}
        directive.content_offset = 0

        # Mock the state for RST parsing
        directive.state = MagicMock()
        directive.state.nested_parse = MagicMock()

        return directive

    def test_directive_run_success(self, mock_directive, tmp_path):
        """Test successful directive execution."""
        # Create a test module with an app
        module_file = tmp_path / "test_directive_module.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

@app.command
def cmd():
    '''A command.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            # Create actual directive instance
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_directive_module:app"],
                options={},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_directive.state,
                state_machine=MagicMock(),
            )

            # Run the directive
            result = directive.run()

            # Should return nodes (may be multiple sections/literal blocks)
            assert len(result) >= 1
            # The state.nested_parse should have been called
            mock_directive.state.nested_parse.assert_called()

        finally:
            sys.path.remove(str(tmp_path))

    def test_directive_with_options(self, mock_directive, tmp_path):
        """Test directive with various options."""
        module_file = tmp_path / "test_options_module.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

@app.command
def visible():
    '''Visible command.'''
    pass

@app.command(show=False)
def hidden():
    '''Hidden command.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            # Create directive with options
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_options_module:app"],
                options={"heading-level": 2, "recursive": True, "include-hidden": True},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_directive.state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) >= 1

            # Verify the nested_parse was called with RST content
            # Note: nested_parse may be called multiple times for different sections
            all_calls = mock_directive.state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                rst_lines = call_args[0][0]  # First argument is the list of lines
                all_content.extend(rst_lines)

            # Join all lines to check content
            rst_content = "\n".join(all_content)

            # Hidden command should be included
            assert (
                "hidden" in rst_content.lower() or len(result) >= 2
            )  # Multiple nodes indicate multiple commands processed

        finally:
            sys.path.remove(str(tmp_path))

    def test_directive_import_error(self, mock_directive):
        """Test directive handles import errors gracefully."""
        from cyclopts.ext.sphinx import CycloptsDirective

        directive = CycloptsDirective(
            name="cyclopts",
            arguments=["nonexistent_module:app"],
            options={},
            content=StringList(),
            lineno=1,
            content_offset=0,
            block_text="",
            state=MagicMock(),
            state_machine=MagicMock(),
        )

        result = directive.run()

        # Should return an error node
        assert len(result) == 1
        # The result should be an error node (we can't check the exact type without docutils)


class TestSphinxSetup:
    """Test the setup function for Sphinx integration."""

    def test_setup_function(self):
        """Test the setup function registers the directive."""
        from cyclopts.ext.sphinx import setup

        # Create a mock Sphinx app
        mock_app = MagicMock()

        # Call setup
        result = setup(mock_app)

        # Verify directive was registered
        mock_app.add_directive.assert_called_once_with("cyclopts", ANY)

        # Verify metadata
        assert result["version"] == "1.0.0"
        assert result["parallel_read_safe"] is True
        assert result["parallel_write_safe"] is True


class TestNewDirectiveOptions:
    """Test the new directive options for distinct headings."""

    def test_flatten_commands_option(self, tmp_path):
        """Test flatten-commands option generates consistent heading levels."""
        module_file = tmp_path / "test_flatten_module.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

sub1 = App(name="sub1", help="First subcommand")
sub2 = App(name="sub2", help="Second subcommand")

@sub1.command
def action():
    '''Sub1 action command.'''
    pass

@sub2.command
def process():
    '''Sub2 process command.'''
    pass

app.command(sub1)
app.command(sub2)
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            # Create mock state
            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            # Create directive with flatten-commands option
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_flatten_module:app"],
                options={"flatten-commands": True, "recursive": True},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) >= 1

            # Verify the nested_parse was called with RST content
            # Note: nested_parse may be called multiple times for different sections
            all_calls = mock_state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                if call_args:  # Check if there are call args
                    rst_lines = call_args[0][0]  # First argument is the list of lines
                    all_content.extend(rst_lines)

            # Join lines to check content
            rst_content = "\n".join(all_content)

            # All commands should be documented
            assert "sub1" in rst_content
            assert "sub2" in rst_content
            assert "action" in rst_content
            assert "process" in rst_content

        finally:
            sys.path.remove(str(tmp_path))

    def test_automatic_anchors(self, tmp_path):
        """Test that RST reference labels are automatically generated."""
        module_file = tmp_path / "test_anchors_module.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

sub_cmd = App(name="sub", help="Subcommand")
app.command(sub_cmd)

@sub_cmd.command
def action():
    '''Perform action.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_anchors_module:app"],
                options={"recursive": True},  # No generate-anchors option needed
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) >= 1

            # Check that anchors are automatically generated with new format
            # Note: nested_parse may be called multiple times
            all_calls = mock_state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                if call_args:
                    rst_lines = call_args[0][0]
                    all_content.extend(rst_lines)

            rst_content = "\n".join(all_content)

            # Should contain RST reference labels with new format
            assert ".. _cyclopts-test-cli:" in rst_content
            # Check for the subcommand anchor
            assert ".. _cyclopts-test-cli-sub:" in rst_content
            assert ".. _cyclopts-test-cli-sub-action:" in rst_content

        finally:
            sys.path.remove(str(tmp_path))

    def test_commands_filter_option(self, tmp_path):
        """Test :commands: option to filter specific commands."""
        module_file = tmp_path / "test_commands_filter.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

@app.command
def include_me():
    '''This command should be included.'''
    pass

@app.command
def exclude_me():
    '''This command should be excluded.'''
    pass

@app.command
def also_include():
    '''This command should also be included.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            # Test with commands filter
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_commands_filter:app"],
                options={"commands": "include_me, also_include"},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) >= 1

            # Verify the content includes only specified commands
            all_calls = mock_state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                if call_args:
                    rst_lines = call_args[0][0]
                    all_content.extend(rst_lines)

            rst_content = "\n".join(all_content)

            # Should include specified commands
            assert "include_me" in rst_content or "include-me" in rst_content
            assert "also_include" in rst_content or "also-include" in rst_content
            # Should exclude non-specified command
            assert "exclude_me" not in rst_content and "exclude-me" not in rst_content

        finally:
            sys.path.remove(str(tmp_path))

    def test_exclude_commands_option(self, tmp_path):
        """Test :exclude-commands: option to exclude specific commands."""
        module_file = tmp_path / "test_exclude_commands.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

@app.command
def keep_me():
    '''This command should be kept.'''
    pass

@app.command
def exclude_me():
    '''This command should be excluded.'''
    pass

@app.command
def also_keep():
    '''This command should also be kept.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            # Test with exclude filter
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_exclude_commands:app"],
                options={"exclude-commands": "exclude_me"},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) >= 1

            # Verify the content excludes specified command
            all_calls = mock_state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                if call_args:
                    rst_lines = call_args[0][0]
                    all_content.extend(rst_lines)

            rst_content = "\n".join(all_content)

            # Should include non-excluded commands
            assert "keep_me" in rst_content or "keep-me" in rst_content
            assert "also_keep" in rst_content or "also-keep" in rst_content
            # Should exclude specified command
            assert "exclude_me" not in rst_content and "exclude-me" not in rst_content

        finally:
            sys.path.remove(str(tmp_path))

    def test_nested_command_filtering(self, tmp_path):
        """Test filtering nested commands with dot notation."""
        module_file = tmp_path / "test_nested_filter.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

# Database commands
db_app = App(name="db", help="Database commands")

@db_app.command
def migrate():
    '''Run migrations.'''
    pass

@db_app.command
def backup():
    '''Backup database.'''
    pass

# API commands
api_app = App(name="api", help="API commands")

@api_app.command
def start():
    '''Start API server.'''
    pass

@api_app.command
def stop():
    '''Stop API server.'''
    pass

app.command(db_app)
app.command(api_app)
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            # Test filtering nested commands
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_nested_filter:app"],
                options={"commands": "db.migrate, api", "recursive": True},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) >= 1

            # Verify the content
            all_calls = mock_state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                if call_args:
                    rst_lines = call_args[0][0]
                    all_content.extend(rst_lines)

            rst_content = "\n".join(all_content)

            # Should include db.migrate
            assert "migrate" in rst_content
            # Should include all api commands (parent was specified)
            assert "api" in rst_content
            assert "start" in rst_content
            assert "stop" in rst_content
            # Should exclude db.backup (not specified)
            # Note: "backup" might appear in help text, so check more specifically
            lines = rst_content.split("\n")
            backup_as_command = any("backup" in line and ("``" in line or "::" in line) for line in lines)
            assert not backup_as_command

        finally:
            sys.path.remove(str(tmp_path))

    def test_mixed_underscore_dash_names(self, tmp_path):
        """Test that underscore and dash command names are handled correctly."""
        module_file = tmp_path / "test_mixed_names.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

@app.command
def my_command():
    '''Command with underscore in function name.'''
    pass

@app.command(name="another-command")
def another_func():
    '''Command with explicit dash name.'''
    pass

@app.command
def third_command():
    '''Another underscore command.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            # Test filtering with underscore notation
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_mixed_names:app"],
                options={"commands": "my_command, another-command"},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) >= 1

            # Verify the content
            all_calls = mock_state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                if call_args:
                    rst_lines = call_args[0][0]
                    all_content.extend(rst_lines)

            rst_content = "\n".join(all_content)

            # Should include both commands regardless of underscore/dash
            assert "my-command" in rst_content or "my_command" in rst_content
            assert "another-command" in rst_content
            # Should exclude third_command
            assert "third-command" not in rst_content and "third_command" not in rst_content

        finally:
            sys.path.remove(str(tmp_path))

    def test_deeply_nested_commands(self, tmp_path):
        """Test filtering with deeply nested command hierarchies (3+ levels)."""
        module_file = tmp_path / "test_deep_nested.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

# Level 1: admin
admin_app = App(name="admin", help="Admin commands")

# Level 2: admin.users
users_app = App(name="users", help="User management")

@users_app.command
def list():
    '''List all users.'''
    pass

@users_app.command
def create():
    '''Create a new user.'''
    pass

# Level 3: admin.users.permissions
permissions_app = App(name="permissions", help="Permission management")

@permissions_app.command
def grant():
    '''Grant permissions.'''
    pass

@permissions_app.command
def revoke():
    '''Revoke permissions.'''
    pass

users_app.command(permissions_app)
admin_app.command(users_app)

# Level 2: admin.logs
logs_app = App(name="logs", help="Log management")

@logs_app.command
def view():
    '''View logs.'''
    pass

@logs_app.command
def clear():
    '''Clear logs.'''
    pass

admin_app.command(logs_app)
app.command(admin_app)

# Another top-level command
@app.command
def status():
    '''Show status.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            # Test filtering specific deep nested command
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_deep_nested:app"],
                options={"commands": "admin.users.permissions.grant, status", "recursive": True},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) >= 1

            # Verify the content
            all_calls = mock_state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                if call_args:
                    rst_lines = call_args[0][0]
                    all_content.extend(rst_lines)

            rst_content = "\n".join(all_content)

            # Should include the path to grant and the grant command itself
            assert "admin" in rst_content
            # The filtering works such that we include admin and show it has users,
            # but users content comes from recursive generation with filtered commands
            assert "users" in rst_content or "User management" in rst_content
            # These should be in the recursively generated content
            assert "permissions" in rst_content or "Permission management" in rst_content
            assert "grant" in rst_content or "Grant permissions" in rst_content
            # Should include status
            assert "status" in rst_content
            # Should exclude other commands not in path
            assert "logs" not in rst_content
            assert "clear" not in rst_content
            # Revoke should not be included (not in filter)
            lines = rst_content.split("\n")
            revoke_as_command = any(
                "revoke" in line and ("``" in line or "::" in line or "revoke" == line.strip()) for line in lines
            )
            assert not revoke_as_command

        finally:
            sys.path.remove(str(tmp_path))

    def test_conflicting_filters(self, tmp_path):
        """Test behavior when include and exclude filters conflict."""
        module_file = tmp_path / "test_conflicts.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

@app.command
def cmd1():
    '''Command 1.'''
    pass

@app.command
def cmd2():
    '''Command 2.'''
    pass

@app.command
def cmd3():
    '''Command 3.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            # Test with conflicting filters (cmd2 is both included and excluded)
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_conflicts:app"],
                options={"commands": "cmd1, cmd2", "exclude-commands": "cmd2, cmd3"},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) >= 1

            # Verify the content
            all_calls = mock_state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                if call_args:
                    rst_lines = call_args[0][0]
                    all_content.extend(rst_lines)

            rst_content = "\n".join(all_content)

            # Exclusion should take precedence
            assert "cmd1" in rst_content
            assert "cmd2" not in rst_content  # Excluded even though included
            assert "cmd3" not in rst_content  # Excluded

        finally:
            sys.path.remove(str(tmp_path))

    def test_empty_filter_lists(self, tmp_path):
        """Test behavior with empty filter lists."""
        module_file = tmp_path / "test_empty_filters.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

@app.command
def cmd1():
    '''Command 1.'''
    pass

@app.command
def cmd2():
    '''Command 2.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            # Test with empty commands filter (empty string)
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_empty_filters:app"],
                options={"commands": ""},  # Empty string
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            directive.run()
            # With empty filter, we might get no nodes or minimal content
            # The important thing is that no commands are shown

            # Verify the content if there are nested_parse calls
            all_calls = mock_state.nested_parse.call_args_list
            all_content = []
            for call_args in all_calls:
                if call_args:
                    rst_lines = call_args[0][0]
                    all_content.extend(rst_lines)

            if all_content:
                rst_content = "\n".join(all_content)
                # Empty filter should show no commands
                assert "cmd1" not in rst_content
                assert "cmd2" not in rst_content
            else:
                # If no content was parsed, that's also valid for empty filter
                pass

        finally:
            sys.path.remove(str(tmp_path))


class TestRstContentParsing:
    """Test RST content parsing and formatting."""

    def test_consecutive_lines_in_same_paragraph(self, tmp_path):
        """Test that consecutive non-empty lines are kept in the same paragraph."""
        module_file = tmp_path / "test_paragraph_module.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test", help="Test")

@app.command
def cmd():
    '''A command with multiline description.

    Shell completion is available. Run once to install (persistent):
    ``cyclopts --install-completion``
    '''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.sphinx import CycloptsDirective

            mock_state = MagicMock()

            # Track nested_parse calls to inspect generated nodes
            parsed_content = []

            def capture_nested_parse(string_list, offset, parent):
                # Capture the content being parsed
                content = "\n".join(string_list)
                parsed_content.append(content)

            mock_state.nested_parse = capture_nested_parse

            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_paragraph_module:app"],
                options={},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            directive.run()

            # The two lines should be parsed together, not separately
            # This means they should appear in the same nested_parse call
            # Check that we don't have separate paragraph parsing for these lines
            consecutive_line_found = False
            for content in parsed_content:
                if "Shell completion is available" in content and "cyclopts --install-completion" in content:
                    consecutive_line_found = True
                    break

            # The lines should be parsed together in one block
            assert consecutive_line_found, "Consecutive lines should be parsed together in the same paragraph"

        finally:
            sys.path.remove(str(tmp_path))


class TestBackwardCompatibility:
    """Test backward compatibility of cyclopts.sphinx_ext."""

    def test_deprecation_warning(self):
        """Test that importing cyclopts.sphinx_ext shows a deprecation warning."""
        import sys

        # Remove module if already imported to ensure fresh import
        if "cyclopts.sphinx_ext" in sys.modules:
            del sys.modules["cyclopts.sphinx_ext"]

        with pytest.warns(DeprecationWarning, match="Importing from 'cyclopts.sphinx_ext' is deprecated"):
            import cyclopts.sphinx_ext  # noqa: F401

    def test_backward_compatible_imports(self):
        """Test that old import path still works."""
        import warnings

        # Suppress the deprecation warning for this test
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from cyclopts.sphinx_ext import CycloptsDirective, DirectiveOptions, setup

            assert CycloptsDirective is not None
            assert DirectiveOptions is not None
            assert setup is not None
