"""Tests for the Cyclopts MkDocs plugin."""

import sys
import textwrap

import pytest

from cyclopts import App
from cyclopts.utils import import_app


class TestImportApp:
    """Test the import_app function."""

    def test_import_with_colon_notation(self, tmp_path):
        """Test importing an app using module:app notation."""
        module_file = tmp_path / "test_module.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                my_app = App(name="test-app", help="Test application")

                @my_app.command
                def hello():
                    '''Say hello.'''
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            app = import_app("test_module:my_app")
            assert isinstance(app, App)
            assert app.name == ("test-app",)
        finally:
            sys.path.remove(str(tmp_path))
            if "test_module" in sys.modules:
                del sys.modules["test_module"]

    def test_import_without_colon_finds_app(self, tmp_path):
        """Test importing when app name is not specified (auto-discovery)."""
        module_file = tmp_path / "test_cli.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="auto-found", help="Automatically found app")
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            found_app = import_app("test_cli")
            assert isinstance(found_app, App)
            assert found_app.name == ("auto-found",)
        finally:
            sys.path.remove(str(tmp_path))
            if "test_cli" in sys.modules:
                del sys.modules["test_cli"]

    def test_import_module_not_found(self):
        """Test error when module doesn't exist."""
        with pytest.raises(ImportError, match="Cannot import module"):
            import_app("nonexistent_module:app")

    def test_import_app_not_found(self, tmp_path):
        """Test error when specified app doesn't exist in module."""
        module_file = tmp_path / "test_no_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                some_app = App(name="test", help="Test")
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(AttributeError, match="has no attribute 'missing_app'"):
                import_app("test_no_app:missing_app")
        finally:
            sys.path.remove(str(tmp_path))
            if "test_no_app" in sys.modules:
                del sys.modules["test_no_app"]

    def test_import_not_an_app(self, tmp_path):
        """Test error when object is not a Cyclopts App."""
        module_name = "test_not_app_module"
        module_file = tmp_path / f"{module_name}.py"
        module_file.write_text("not_an_app = 'This is just a string'")

        sys.path.insert(0, str(tmp_path))
        try:
            with pytest.raises(TypeError, match="is not a Cyclopts App instance"):
                import_app(f"{module_name}:not_an_app")
        finally:
            sys.path.remove(str(tmp_path))
            if module_name in sys.modules:
                del sys.modules[module_name]


class TestDirectiveOptions:
    """Test the DirectiveOptions class."""

    def test_parse_basic_directive(self):
        """Test parsing a basic directive with minimal options."""
        from cyclopts.ext.mkdocs import DirectiveOptions

        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli:app
            """
        )

        options = DirectiveOptions.from_directive_block(directive_text)
        assert options.module == "myapp.cli:app"
        assert options.heading_level == 2  # default
        assert options.recursive is True  # default
        assert options.include_hidden is False  # default

    def test_parse_full_directive(self):
        """Test parsing a directive with all options."""
        from cyclopts.ext.mkdocs import DirectiveOptions

        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli:app
                heading_level: 3
                recursive: false
                include_hidden: true
                flatten_commands: true
                generate_toc: false
                commands:
                  - init
                  - build
                  - deploy
                exclude_commands:
                  - debug
                  - internal
            """
        )

        options = DirectiveOptions.from_directive_block(directive_text)
        assert options.module == "myapp.cli:app"
        assert options.heading_level == 3
        assert options.recursive is False
        assert options.include_hidden is True
        assert options.flatten_commands is True
        assert options.generate_toc is False
        assert options.commands == ["init", "build", "deploy"]
        assert options.exclude_commands == ["debug", "internal"]

    def test_parse_comma_separated_commands(self):
        """Test parsing YAML list format for commands."""
        from cyclopts.ext.mkdocs import DirectiveOptions

        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli
                commands: [cmd1, cmd2, cmd3]
            """
        )

        options = DirectiveOptions.from_directive_block(directive_text)
        assert options.commands == ["cmd1", "cmd2", "cmd3"]

    def test_parse_single_command_string_raises_error(self):
        """Test that a single command string (not a list) raises ValueError.

        YAML parses 'commands: files.cp' as a string, not a list.
        We enforce that commands must be a list for clarity.
        """
        from cyclopts.ext.mkdocs import DirectiveOptions

        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli
                commands: files.cp
            """
        )

        with pytest.raises(ValueError, match="'commands'.*must be.*list"):
            DirectiveOptions.from_directive_block(directive_text)

    def test_parse_single_exclude_command_string_raises_error(self):
        """Test that a single exclude command string raises ValueError."""
        from cyclopts.ext.mkdocs import DirectiveOptions

        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli
                exclude_commands: debug
            """
        )

        with pytest.raises(ValueError, match="'exclude_commands'.*must be.*list"):
            DirectiveOptions.from_directive_block(directive_text)

    def test_parse_missing_module_raises_error(self):
        """Test that missing module option raises an error."""
        from cyclopts.ext.mkdocs import DirectiveOptions

        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                heading_level: 2
            """
        )

        with pytest.raises(ValueError, match="module.*required"):
            DirectiveOptions.from_directive_block(directive_text)

    def test_parse_invalid_heading_level_type_raises_error(self):
        """Test that non-integer heading_level raises TypeError."""
        from cyclopts.ext.mkdocs import DirectiveOptions

        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli
                heading_level: "3"
            """
        )

        with pytest.raises(ValueError, match="'heading_level'.*must be.*int"):
            DirectiveOptions.from_directive_block(directive_text)

    def test_parse_invalid_recursive_type_raises_error(self):
        """Test that non-boolean recursive raises TypeError."""
        from cyclopts.ext.mkdocs import DirectiveOptions

        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli
                recursive: "yes"
            """
        )

        with pytest.raises(ValueError, match="'recursive'.*must be.*bool"):
            DirectiveOptions.from_directive_block(directive_text)

    def test_parse_boolean_variations(self):
        """Test parsing various boolean value formats."""
        from cyclopts.ext.mkdocs import DirectiveOptions

        # Test "true"
        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli
                recursive: true
            """
        )
        options = DirectiveOptions.from_directive_block(directive_text)
        assert options.recursive is True

        # Test "yes"
        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli
                recursive: yes
            """
        )
        options = DirectiveOptions.from_directive_block(directive_text)
        assert options.recursive is True

        # Test "false"
        directive_text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli
                recursive: false
            """
        )
        options = DirectiveOptions.from_directive_block(directive_text)
        assert options.recursive is False


class TestProcessDirectives:
    """Test the process_cyclopts_directives function."""

    def test_process_simple_directive(self, tmp_path):
        """Test processing a simple directive in markdown."""
        module_file = tmp_path / "simple_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="simple-cli", help="A simple CLI app")

                @app.default
                def main(name: str):
                    '''Greet someone by name.'''
                    print(f"Hello, {name}!")
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import process_cyclopts_directives

            markdown = textwrap.dedent(
                """\
                # My CLI Tool

                Here's the documentation:

                ::: cyclopts
                    module: simple_app:app
                    heading_level: 2

                More content here.
                """
            )

            result = process_cyclopts_directives(markdown, None)

            # Verify the directive was replaced
            assert "::: cyclopts" not in result
            assert "simple-cli" in result or "simple_cli" in result
            assert "More content here." in result
            assert "# My CLI Tool" in result

        finally:
            sys.path.remove(str(tmp_path))
            if "simple_app" in sys.modules:
                del sys.modules["simple_app"]

    def test_process_multiple_directives(self, tmp_path):
        """Test processing multiple directives in one page."""
        module_file = tmp_path / "multi_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="cli", help="Main CLI")

                @app.default
                def main():
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import process_cyclopts_directives

            markdown = textwrap.dedent(
                """\
                # First Section

                ::: cyclopts
                    module: multi_app:app
                    heading_level: 2
                    generate_toc: false

                # Second Section

                ::: cyclopts
                    module: multi_app:app
                    heading_level: 3
                    generate_toc: false
                """
            )

            result = process_cyclopts_directives(markdown, None)

            # Both directives should be processed
            assert result.count("::: cyclopts") == 0
            assert "# First Section" in result
            assert "# Second Section" in result

        finally:
            sys.path.remove(str(tmp_path))
            if "multi_app" in sys.modules:
                del sys.modules["multi_app"]

    def test_process_directive_with_error(self):
        """Test that errors in directive processing raise PluginError."""
        pytest.importorskip("mkdocs")
        from cyclopts.ext.mkdocs import PluginError, process_cyclopts_directives

        markdown = textwrap.dedent(
            """\
            # My Documentation

            ::: cyclopts
                module: nonexistent_module:app

            More content.
            """
        )

        # Should raise PluginError instead of returning error markdown
        with pytest.raises(PluginError, match="Error processing ::: cyclopts directive"):
            process_cyclopts_directives(markdown, None)

    def test_no_directives_unchanged(self):
        """Test that markdown without directives is unchanged."""
        from cyclopts.ext.mkdocs import process_cyclopts_directives

        markdown = textwrap.dedent(
            """\
            # My Documentation

            This is just regular markdown content.

            No directives here!
            """
        )

        result = process_cyclopts_directives(markdown, None)
        assert result == markdown

    def test_default_heading_level_from_config(self, tmp_path):
        """Test that default_heading_level from config is used when not specified in directive."""
        module_file = tmp_path / "config_test_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="config-test", help="Test app")

                @app.default
                def main():
                    '''Main function.'''
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import DirectiveOptions

            # Test with default_heading_level=3
            directive_text = textwrap.dedent(
                """\
                ::: cyclopts
                    module: config_test_app:app
                """
            )

            options = DirectiveOptions.from_directive_block(directive_text, default_heading_level=3)
            assert options.heading_level == 3

            # Test that explicit heading-level overrides default
            directive_text_with_level = textwrap.dedent(
                """\
                ::: cyclopts
                    module: config_test_app:app
                    heading_level: 4
                """
            )

            options_override = DirectiveOptions.from_directive_block(directive_text_with_level, default_heading_level=3)
            assert options_override.heading_level == 4

        finally:
            sys.path.remove(str(tmp_path))
            if "config_test_app" in sys.modules:
                del sys.modules["config_test_app"]

    def test_no_root_title_in_output(self, tmp_path):
        """Test that the root app title is not included in generated docs."""
        module_file = tmp_path / "no_title_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="no-title-test", help="This app should not show its title")

                @app.default
                def main(arg: str):
                    '''Do something.'''
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import process_cyclopts_directives

            markdown = textwrap.dedent(
                """\
                # Documentation

                ::: cyclopts
                    module: no_title_app:app
                    generate_toc: false

                More content.
                """
            )

            result = process_cyclopts_directives(markdown, None)

            # Should not contain the app name as a header
            assert "# no-title-test" not in result
            assert "## no-title-test" not in result
            # Should still contain the description
            assert "This app should not show its title" in result
            assert "More content." in result

        finally:
            sys.path.remove(str(tmp_path))
            if "no_title_app" in sys.modules:
                del sys.modules["no_title_app"]

    def test_skip_preamble_skips_description_and_usage(self, tmp_path):
        """Test that skip_preamble skips description and usage for filtered command."""
        module_file = tmp_path / "skip_preamble_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="main-app", help="Main app description")

                sub = App(name="sub", help="This description should be skipped")

                @sub.default
                def sub_cmd(arg: str):
                    '''Sub command.'''
                    pass

                app.command(sub)
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import process_cyclopts_directives

            # Test without skip_preamble (default) - description should be present
            markdown_without_skip = textwrap.dedent(
                """\
                # Sub Commands

                ::: cyclopts
                    module: skip_preamble_app:app
                    commands: [sub]
                    generate_toc: false
                """
            )

            result_without_skip = process_cyclopts_directives(markdown_without_skip, None)
            assert "This description should be skipped" in result_without_skip

            # Clear module cache for fresh import
            del sys.modules["skip_preamble_app"]

            # Test with skip_preamble=true - description should be absent
            markdown_with_skip = textwrap.dedent(
                """\
                # Sub Commands

                ::: cyclopts
                    module: skip_preamble_app:app
                    commands: [sub]
                    generate_toc: false
                    skip_preamble: true
                """
            )

            result_with_skip = process_cyclopts_directives(markdown_with_skip, None)
            assert "This description should be skipped" not in result_with_skip
            # The command's parameters should still be present
            assert "arg" in result_with_skip.lower()

        finally:
            sys.path.remove(str(tmp_path))
            if "skip_preamble_app" in sys.modules:
                del sys.modules["skip_preamble_app"]


class TestDirectivePattern:
    """Test the directive pattern regex."""

    def test_pattern_matches_simple_directive(self):
        """Test that the pattern matches a simple directive."""
        from cyclopts.ext.mkdocs import DIRECTIVE_PATTERN

        text = textwrap.dedent(
            """\
            ::: cyclopts
                module: myapp.cli
            """
        )

        match = DIRECTIVE_PATTERN.search(text)
        assert match is not None
        assert match.group(0).startswith("::: cyclopts")

    def test_pattern_matches_multiline_directive(self):
        """Test that the pattern matches directives with multiple options."""
        from cyclopts.ext.mkdocs import DIRECTIVE_PATTERN

        text = textwrap.dedent(
            """\
            Some text before.

            ::: cyclopts
                module: myapp.cli:app
                heading_level: 2
                recursive: true
                commands: cmd1, cmd2

            Some text after.
            """
        )

        match = DIRECTIVE_PATTERN.search(text)
        assert match is not None
        matched_text = match.group(0)
        assert "module:" in matched_text
        assert "heading_level:" in matched_text
        assert "recursive:" in matched_text
        assert "commands:" in matched_text

    def test_pattern_finds_all_directives(self):
        """Test that the pattern finds all directives in text."""
        from cyclopts.ext.mkdocs import DIRECTIVE_PATTERN

        text = textwrap.dedent(
            """\
            # First

            ::: cyclopts
                module: app1

            # Second

            ::: cyclopts
                module: app2
            """
        )

        matches = list(DIRECTIVE_PATTERN.finditer(text))
        assert len(matches) == 2


class TestPluginIntegration:
    """Test the MkDocs plugin integration."""

    @pytest.fixture
    def plugin(self):
        """Create a plugin instance."""
        pytest.importorskip("mkdocs")
        from cyclopts.ext.mkdocs import CycloptsPlugin

        return CycloptsPlugin()

    def test_plugin_has_config(self, plugin):
        """Test that the plugin has configuration."""
        assert hasattr(plugin, "config")

    def test_plugin_on_page_markdown_with_directive(self, plugin, tmp_path):
        """Test the on_page_markdown event with a cyclopts directive."""
        module_file = tmp_path / "plugin_test_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="test", help="Test app")

                @app.default
                def main(arg: str):
                    '''Main function.'''
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            markdown = textwrap.dedent(
                """\
                # Documentation

                ::: cyclopts
                    module: plugin_test_app:app
                    heading_level: 2
                    generate_toc: false
                """
            )

            # Mock the required arguments
            result = plugin.on_page_markdown(markdown, page=None, config=None, files=None)

            assert "::: cyclopts" not in result
            assert "test" in result.lower()

        finally:
            sys.path.remove(str(tmp_path))
            if "plugin_test_app" in sys.modules:
                del sys.modules["plugin_test_app"]

    def test_plugin_on_page_markdown_without_directive(self, plugin):
        """Test that pages without directives are unchanged."""
        markdown = "# Just a regular page\n\nNo directives here."
        result = plugin.on_page_markdown(markdown, page=None, config=None, files=None)
        assert result == markdown


@pytest.mark.skipif(not pytest.importorskip("mkdocs", reason="mkdocs not installed"), reason="mkdocs not installed")
class TestMkDocsAvailable:
    """Tests that require mkdocs to be installed."""

    def test_plugin_class_exists(self):
        """Test that the plugin class can be imported."""
        from cyclopts.ext.mkdocs import CycloptsPlugin

        assert CycloptsPlugin is not None

    def test_plugin_config_class_exists(self):
        """Test that the config class can be imported."""
        from cyclopts.ext.mkdocs import CycloptsPluginConfig

        assert CycloptsPluginConfig is not None


class TestCommandFiltering:
    """Test command filtering functionality."""

    def test_filter_specific_commands(self, tmp_path):
        """Test filtering to include only specific commands."""
        module_file = tmp_path / "multi_cmd_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="multi-app", help="Multi-command app")

                @app.command
                def init():
                    '''Initialize project.'''
                    pass

                @app.command
                def build():
                    '''Build project.'''
                    pass

                @app.command
                def deploy():
                    '''Deploy project.'''
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import process_cyclopts_directives

            markdown = textwrap.dedent(
                """\
                # CLI Reference

                ::: cyclopts
                    module: multi_cmd_app:app
                    commands: [init, build]
                """
            )

            result = process_cyclopts_directives(markdown, None)

            # Should include init and build
            assert "init" in result.lower()
            assert "build" in result.lower()
            # Should NOT include deploy
            assert "deploy" not in result.lower()

        finally:
            sys.path.remove(str(tmp_path))
            if "multi_cmd_app" in sys.modules:
                del sys.modules["multi_cmd_app"]

    def test_exclude_specific_commands(self, tmp_path):
        """Test excluding specific commands."""
        module_file = tmp_path / "exclude_cmd_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="exclude-app", help="App with exclusions")

                @app.command
                def public_cmd():
                    '''Public command.'''
                    pass

                @app.command
                def debug():
                    '''Debug command.'''
                    pass

                @app.command
                def internal():
                    '''Internal command.'''
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import process_cyclopts_directives

            markdown = textwrap.dedent(
                """\
                # CLI Reference

                ::: cyclopts
                    module: exclude_cmd_app:app
                    exclude_commands: [debug, internal]
                """
            )

            result = process_cyclopts_directives(markdown, None)

            # Should include public_cmd
            assert "public" in result.lower()
            # Should NOT include debug or internal
            assert "debug" not in result.lower()
            assert "internal" not in result.lower()

        finally:
            sys.path.remove(str(tmp_path))
            if "exclude_cmd_app" in sys.modules:
                del sys.modules["exclude_cmd_app"]


class TestCodeBlockDetection:
    """Test code block detection to avoid processing directives in code."""

    def test_directive_in_fenced_code_block_ignored(self, tmp_path):
        """Test that directives in fenced code blocks are not processed."""
        module_file = tmp_path / "fence_test_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="fence-test", help="Test app")

                @app.default
                def main():
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import process_cyclopts_directives

            markdown = textwrap.dedent(
                """\
                # Documentation

                Here's an example directive:

                ```markdown
                ::: cyclopts
                    module: fence_test_app:app
                ```

                The above should not be processed.
                """
            )

            result = process_cyclopts_directives(markdown, None)

            # The directive should remain unchanged since it's in a code block
            assert "::: cyclopts" in result
            assert "fence-test" not in result.lower()

        finally:
            sys.path.remove(str(tmp_path))
            if "fence_test_app" in sys.modules:
                del sys.modules["fence_test_app"]

    def test_directive_in_indented_code_block_ignored(self, tmp_path):
        """Test that directives in indented code blocks are not processed."""
        module_file = tmp_path / "indent_test_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="indent-test", help="Test app")

                @app.default
                def main():
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import process_cyclopts_directives

            markdown = textwrap.dedent(
                """\
                # Documentation

                Here's an example directive:

                    ::: cyclopts
                        module: indent_test_app:app

                The above should not be processed.
                """
            )

            result = process_cyclopts_directives(markdown, None)

            # The directive should remain unchanged since it's in an indented code block
            assert "::: cyclopts" in result
            assert "indent-test" not in result.lower()

        finally:
            sys.path.remove(str(tmp_path))
            if "indent_test_app" in sys.modules:
                del sys.modules["indent_test_app"]


class TestDirectiveEOFEdgeCases:
    """Test directive pattern edge cases at end of file."""

    def test_directive_at_eof_without_trailing_newline(self, tmp_path):
        """Test directive at EOF without trailing newline."""
        module_file = tmp_path / "eof_test_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="eof-test", help="EOF test app")

                @app.default
                def main():
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import DIRECTIVE_PATTERN

            # Directive at EOF without trailing newline
            markdown = "::: cyclopts\n    module: eof_test_app:app"

            matches = list(DIRECTIVE_PATTERN.finditer(markdown))
            assert len(matches) == 1
            assert matches[0].group(0) == markdown

        finally:
            sys.path.remove(str(tmp_path))
            if "eof_test_app" in sys.modules:
                del sys.modules["eof_test_app"]

    def test_directive_with_trailing_whitespace_at_eof(self, tmp_path):
        """Test directive with trailing whitespace at EOF."""
        module_file = tmp_path / "eof_ws_test_app.py"
        module_file.write_text(
            textwrap.dedent(
                """\
                from cyclopts import App

                app = App(name="eof-ws-test", help="EOF whitespace test app")

                @app.default
                def main():
                    pass
                """
            )
        )

        sys.path.insert(0, str(tmp_path))
        try:
            from cyclopts.ext.mkdocs import DIRECTIVE_PATTERN

            # Directive at EOF with trailing spaces but no newline
            markdown = "::: cyclopts\n    module: eof_ws_test_app:app    "

            matches = list(DIRECTIVE_PATTERN.finditer(markdown))
            assert len(matches) == 1

        finally:
            sys.path.remove(str(tmp_path))
            if "eof_ws_test_app" in sys.modules:
                del sys.modules["eof_ws_test_app"]
