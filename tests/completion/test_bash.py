"""Tests for bash completion script generation."""

from typing import Annotated, Literal

import pytest

from cyclopts import App, Parameter
from cyclopts.completion.bash import generate_completion_script

from .apps import (
    app_basic,
    app_enum,
    app_negative,
    app_nested,
    app_path,
)


def test_generate_completion_script_invalid_prog_name():
    """Test that invalid prog_name raises ValueError."""
    with pytest.raises(ValueError, match="Invalid prog_name"):
        generate_completion_script(app_basic, "invalid prog")

    with pytest.raises(ValueError, match="Invalid prog_name"):
        generate_completion_script(app_basic, "")

    with pytest.raises(ValueError, match="Invalid prog_name"):
        generate_completion_script(app_basic, "prog$name")


def test_generate_completion_script_creates_script():
    """Test that bash completion generates a script."""
    script = generate_completion_script(app_basic, "basic")
    assert script
    assert "# Bash completion for basic" in script
    assert "complete -F _basic basic" in script


def test_basic_option_completion(bash_tester):
    """Test basic option name completion."""
    tester = bash_tester(app_basic, "basic")

    assert "--verbose" in tester.completion_script
    assert "--count" in tester.completion_script
    assert "--help" in tester.completion_script


def test_command_completion(bash_tester):
    """Test command completion."""
    tester = bash_tester(app_basic, "basic")

    assert "deploy" in tester.completion_script


def test_literal_value_completion(bash_tester):
    """Test Literal type value completion."""
    tester = bash_tester(app_basic, "basic")

    assert "dev" in tester.completion_script
    assert "staging" in tester.completion_script
    assert "prod" in tester.completion_script


def test_enum_value_completion(bash_tester):
    """Test Enum type value completion."""
    tester = bash_tester(app_enum, "enumapp")

    assert "fast" in tester.completion_script
    assert "slow" in tester.completion_script


def test_nested_subcommand_completion(bash_tester):
    """Test nested subcommand completion."""
    tester = bash_tester(app_nested, "nested")

    assert "config" in tester.completion_script
    assert "get" in tester.completion_script
    assert "set" in tester.completion_script


def test_path_completion_action(bash_tester):
    """Test that Path types trigger file completion."""
    tester = bash_tester(app_path, "pathapp")

    assert tester.validate_script_syntax()


def test_negative_flag_completion(bash_tester):
    """Test negative flag handling."""
    tester = bash_tester(app_negative, "negapp")

    assert "--verbose" in tester.completion_script
    assert "--no-verbose" in tester.completion_script
    assert "--colors" in tester.completion_script
    assert "--no-colors" in tester.completion_script


def test_script_syntax_validation(bash_tester):
    """Test that generated script has valid bash syntax."""
    tester = bash_tester(app_basic, "basic")

    assert tester.validate_script_syntax()


def test_completion_function_naming(bash_tester):
    """Test that completion function uses correct naming convention."""
    tester = bash_tester(app_basic, "myapp")

    assert "_myapp" in tester.completion_script or "_myapp_completion" in tester.completion_script
    assert "complete -F" in tester.completion_script


def test_special_characters_in_choices(bash_tester):
    """Test that special characters in choices are properly escaped."""
    app = App(name="special")

    @app.default
    def main(
        value: Annotated[
            Literal["normal", "with space", "with'quote", "with$dollar"],
            Parameter(help="Test value"),
        ] = "normal",
    ):
        """Test app with special characters."""
        pass

    tester = bash_tester(app, "special")
    assert tester.validate_script_syntax()


def test_help_descriptions(bash_tester):
    """Test that completion script contains relevant option and command names.

    Note: Bash completion uses a minimal format (compgen -W) without descriptions,
    unlike zsh/fish which support inline descriptions.
    """
    tester = bash_tester(app_basic, "basic")

    assert "--verbose" in tester.completion_script
    assert "deploy" in tester.completion_script


def test_description_escaping(bash_tester):
    """Test that descriptions with special chars are properly escaped."""
    app = App(name="escape_test")

    @app.default
    def main(
        param1: Annotated[str, Parameter(help="Test 'single' quotes")] = "",
        param2: Annotated[str, Parameter(help='Test "double" quotes')] = "",
        param3: Annotated[str, Parameter(help="Test $variable and `backticks`")] = "",
    ):
        """Test app."""

    tester = bash_tester(app, "escape_test")
    assert tester.validate_script_syntax()


def test_special_chars_in_literal_choices(bash_tester):
    """Test that Literal choices with special characters are properly escaped."""
    app = App(name="special_choices")

    @app.default
    def main(
        choice: Annotated[Literal["foo bar", "baz()", "test[1]"], Parameter()] = "foo bar",
    ):
        """Test app with special chars in choices."""

    tester = bash_tester(app, "special_choices")
    assert tester.validate_script_syntax()


def test_unicode_in_descriptions(bash_tester):
    """Test that apps with Unicode descriptions generate valid bash syntax.

    Note: Bash completion doesn't include descriptions, so we only verify
    syntax validity and presence of the options.
    """
    app = App(name="unicode_test")

    @app.default
    def main(
        emoji: Annotated[str, Parameter(help="Enable 🚀 rocket mode")] = "",
        chinese: Annotated[str, Parameter(help="中文描述")] = "",
        arabic: Annotated[str, Parameter(help="وصف بالعربية")] = "",
    ):
        """Test app with Unicode."""

    tester = bash_tester(app, "unicode_test")
    assert "--emoji" in tester.completion_script
    assert tester.validate_script_syntax()


def test_deeply_nested_commands(bash_tester):
    """Test completion for deeply nested commands (3+ levels)."""
    root = App(name="root")
    level1 = App(name="level1")
    level2 = App(name="level2")
    level3 = App(name="level3")

    @level3.command
    def action(value: str):
        """Perform action at level 3."""
        pass

    level2.command(level3)
    level1.command(level2)
    root.command(level1)

    tester = bash_tester(root, "root")

    assert "level1" in tester.completion_script
    assert "level2" in tester.completion_script
    assert "level3" in tester.completion_script
    assert "action" in tester.completion_script
    assert tester.validate_script_syntax()


def test_nested_command_disambiguation(bash_tester):
    """Test that nested commands are properly disambiguated.

    This test verifies that the helper function correctly distinguishes between
    commands with overlapping names (e.g., 'config get' vs 'admin get').
    """
    root = App(name="myapp")

    config = App(name="config")
    admin = App(name="admin")

    @config.command(name="get")
    def config_get(key: Annotated[str, Parameter(help="Config key")] = ""):
        """Get config value."""
        pass

    @config.command(name="set")
    def config_set(key: str = "", value: str = ""):
        """Set config value."""
        pass

    @admin.command(name="get")
    def admin_get(user: Annotated[str, Parameter(help="Username")] = ""):
        """Get admin user."""
        pass

    root.command(config)
    root.command(admin)

    tester = bash_tester(root, "myapp")

    script = tester.completion_script

    assert "cmd_path" in script, "Should use command path detection"

    config_lines = [line for line in script.split("\n") if "config" in line.lower()]
    admin_lines = [line for line in script.split("\n") if "admin" in line.lower()]

    assert any("config" in line for line in config_lines), "Should have config-specific completions"
    assert any("admin" in line for line in admin_lines), "Should have admin-specific completions"

    assert tester.validate_script_syntax()


def test_helper_function_generation(bash_tester):
    """Test that command path detection logic works correctly.

    Note: Bash always generates cmd_path detection logic (even for root-only apps)
    unlike fish which conditionally generates helper functions. This is fine since
    the logic is minimal and doesn't hurt performance.
    """
    root_only = App(name="rootonly")

    @root_only.default
    def main(verbose: bool = False):
        """Root only app."""
        pass

    tester_root = bash_tester(root_only, "rootonly")
    assert tester_root.validate_script_syntax()

    nested = App(name="nested")
    sub = App(name="sub")

    @sub.default
    def action():
        """Sub action."""
        pass

    nested.command(sub)

    tester_nested = bash_tester(nested, "nested")
    assert "cmd_path" in tester_nested.completion_script
    assert tester_nested.validate_script_syntax()


def test_optional_path_completion(bash_tester):
    """Test that Optional[Path] and Path | None generate file completion."""
    tester = bash_tester(app_path, "pathapp")

    assert "compgen -f" in tester.completion_script or "compgen -d" in tester.completion_script


def test_no_file_completion_for_strings(bash_tester):
    """Test that string options don't default to file completion."""
    app = App(name="strtest")

    @app.default
    def main(
        name: Annotated[str, Parameter(help="Name")] = "default",
    ):
        """Test app."""

    tester = bash_tester(app, "strtest")
    assert tester.validate_script_syntax()


def test_empty_iterable_flag_completion(bash_tester):
    """Test that --empty-* flags for list parameters are treated as flags.

    Regression test for issue where --empty-items on list[str] parameters
    would expect a value instead of being treated as a flag.
    """
    app = App(name="listapp")

    @app.command
    def process(
        items: Annotated[list[str], Parameter(help="Items to process")],
        tags: Annotated[list[str] | None, Parameter(help="Optional tags")] = None,
    ):
        """Process items."""
        pass

    tester = bash_tester(app, "listapp")

    assert "--items" in tester.completion_script
    assert "--empty-items" in tester.completion_script
    assert "--tags" in tester.completion_script
    assert "--empty-tags" in tester.completion_script

    lines = tester.completion_script.split("\n")
    options_line = None
    for line in lines:
        if "options_with_values" in line:
            options_line = line
            break

    if options_line:
        assert "--empty-items" not in options_line, "Empty flags should not be in options_with_values"
        assert "--empty-tags" not in options_line, "Empty flags should not be in options_with_values"

    assert tester.validate_script_syntax()


def test_helper_function_skips_option_values(bash_tester):
    """Test that helper function correctly identifies and skips option values.

    Critical bug fix test: ensures that when building command path,
    the helper function skips values for options that take arguments.
    Without this, 'myapp --config file.yaml subcommand' would incorrectly
    extract [file.yaml, subcommand] instead of [subcommand].
    """
    app = App(name="myapp")
    sub = App(name="sub")

    @sub.default
    def action():
        """Subcommand action."""
        pass

    @app.default
    def main(
        config: Annotated[str, Parameter(help="Config file path")],
        verbose: bool = False,
    ):
        """Main app."""
        pass

    app.command(sub)

    tester = bash_tester(app, "myapp")
    script = tester.completion_script

    assert "options_with_values" in script, "Helper should track options that take values"
    assert "--config" in script or "config" in script

    lines = script.split("\n")
    options_line = None
    for line in lines:
        if "options_with_values" in line and "local" in line:
            options_line = line
            break

    assert options_line is not None, "Should have a line setting options_with_values"
    assert "--config" in options_line or "config" in options_line, "Should include --config in options_with_values"
    assert "--verbose" not in options_line, "Flags should not be in options_with_values"

    skip_check = [line for line in lines if "skip_next" in line]
    assert len(skip_check) > 0, "Helper should use skip_next logic to skip option values"

    assert tester.validate_script_syntax()
