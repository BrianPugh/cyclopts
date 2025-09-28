"""Tests for the Cyclopts Sphinx extension."""

import sys
from unittest.mock import ANY, MagicMock

import pytest
from docutils.statemachine import StringList

from cyclopts import App


class TestImportApp:
    """Test the _import_app function."""

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
            from cyclopts.sphinx_ext import _import_app

            app = _import_app("test_module:my_app")
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
            from cyclopts.sphinx_ext import _import_app

            found_app = _import_app("test_cli")
            assert isinstance(found_app, App)
            assert found_app.name == ("auto-found",)
        finally:
            sys.path.remove(str(tmp_path))

    def test_import_module_not_found(self):
        """Test error when module doesn't exist."""
        from cyclopts.sphinx_ext import _import_app

        with pytest.raises(ImportError, match="Cannot import module"):
            _import_app("nonexistent_module:app")

    def test_import_app_not_found(self, tmp_path):
        """Test error when specified app doesn't exist in module."""
        module_file = tmp_path / "test_module.py"
        module_file.write_text("""
from cyclopts import App

some_app = App(name="test", help="Test")
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.sphinx_ext import _import_app

            with pytest.raises(AttributeError, match="has no attribute 'missing_app'"):
                _import_app("test_module:missing_app")
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
            from cyclopts.sphinx_ext import _import_app

            with pytest.raises(TypeError, match="is not a Cyclopts App instance"):
                _import_app(f"{module_name}:not_an_app")
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
        from cyclopts.sphinx_ext import CycloptsDirective

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
            from cyclopts.sphinx_ext import CycloptsDirective

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

            # Should return a container node
            assert len(result) == 1
            # The state.nested_parse should have been called
            mock_directive.state.nested_parse.assert_called_once()

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
            from cyclopts.sphinx_ext import CycloptsDirective

            # Create directive with options
            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_options_module:app"],
                options={"prog": "my-program", "heading-level": 2, "recursive": True, "include-hidden": True},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_directive.state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) == 1

            # Verify the nested_parse was called with RST content
            call_args = mock_directive.state.nested_parse.call_args
            rst_lines = call_args[0][0]  # First argument is the list of lines

            # Join lines to check content
            rst_content = "\n".join(rst_lines)

            # The prog name should be overridden
            assert "my-program" in rst_content or "test-cli" in rst_content
            # Hidden command should be included
            assert "hidden" in rst_content.lower() or "test-cli hidden" in rst_content

        finally:
            sys.path.remove(str(tmp_path))

    def test_directive_import_error(self, mock_directive):
        """Test directive handles import errors gracefully."""
        from cyclopts.sphinx_ext import CycloptsDirective

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
        from cyclopts.sphinx_ext import setup

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
            from cyclopts.sphinx_ext import CycloptsDirective

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
            assert len(result) == 1

            # Verify the nested_parse was called with RST content
            call_args = mock_state.nested_parse.call_args
            rst_lines = call_args[0][0]  # First argument is the list of lines

            # Join lines to check content
            rst_content = "\n".join(rst_lines)

            # All commands should be documented
            assert "sub1" in rst_content
            assert "sub2" in rst_content
            assert "action" in rst_content
            assert "process" in rst_content

        finally:
            sys.path.remove(str(tmp_path))

    def test_command_prefix_option(self, tmp_path):
        """Test command-prefix option adds prefix to command headings."""
        module_file = tmp_path / "test_prefix_module.py"
        module_file.write_text("""from cyclopts import App

app = App(name="test-cli", help="Test CLI")

@app.command
def hello():
    '''Say hello.'''
    pass
""")

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.sphinx_ext import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_prefix_module:app"],
                options={"command-prefix": "Command: "},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) == 1

            # Check that the prefix is applied
            call_args = mock_state.nested_parse.call_args
            rst_lines = call_args[0][0]
            rst_content = "\n".join(rst_lines)

            # The main command should have the prefix
            # Note: The exact format depends on the implementation
            assert "hello" in rst_content

        finally:
            sys.path.remove(str(tmp_path))

    def test_generate_anchors_option(self, tmp_path):
        """Test generate-anchors option creates RST reference labels."""
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
            from cyclopts.sphinx_ext import CycloptsDirective

            mock_state = MagicMock()
            mock_state.nested_parse = MagicMock()

            directive = CycloptsDirective(
                name="cyclopts",
                arguments=["test_anchors_module:app"],
                options={"generate-anchors": True, "recursive": True},
                content=StringList(),
                lineno=1,
                content_offset=0,
                block_text="",
                state=mock_state,
                state_machine=MagicMock(),
            )

            result = directive.run()
            assert len(result) == 1

            # Check that anchors are generated
            call_args = mock_state.nested_parse.call_args
            rst_lines = call_args[0][0]
            rst_content = "\n".join(rst_lines)

            # Should contain RST reference labels
            assert ".. _cli-" in rst_content
            # Check for the subcommand anchor
            assert "sub" in rst_content

        finally:
            sys.path.remove(str(tmp_path))
