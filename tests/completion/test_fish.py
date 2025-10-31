"""Tests for fish completion script generation."""

from typing import Annotated, Literal

import pytest

from cyclopts import App, Parameter
from cyclopts.completion.fish import generate_completion_script

from .apps import (
    app_basic,
    app_disabled_negative,
    app_enum,
    app_list_path,
    app_markup,
    app_negative,
    app_nested,
    app_path,
    app_rst,
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
    """Test that fish completion generates a script."""
    script = generate_completion_script(app_basic, "basic")
    assert script
    assert "# Fish completion for basic" in script
    assert "complete -c basic" in script


def test_basic_option_completion(fish_tester):
    """Test basic option name completion."""
    tester = fish_tester(app_basic, "basic")

    assert "--verbose" in tester.completion_script or "-l verbose" in tester.completion_script
    assert "--count" in tester.completion_script or "-l count" in tester.completion_script
    assert "--help" in tester.completion_script or "-l help" in tester.completion_script


def test_command_completion(fish_tester):
    """Test command completion."""
    tester = fish_tester(app_basic, "basic")

    assert "deploy" in tester.completion_script


def test_literal_value_completion(fish_tester):
    """Test Literal type value completion."""
    tester = fish_tester(app_basic, "basic")

    assert "dev" in tester.completion_script
    assert "staging" in tester.completion_script
    assert "prod" in tester.completion_script


def test_enum_value_completion(fish_tester):
    """Test Enum type value completion."""
    tester = fish_tester(app_enum, "enumapp")

    assert "fast" in tester.completion_script
    assert "slow" in tester.completion_script


def test_nested_subcommand_completion(fish_tester):
    """Test nested subcommand completion."""
    tester = fish_tester(app_nested, "nested")

    assert "config" in tester.completion_script
    assert "get" in tester.completion_script
    assert "set" in tester.completion_script


def test_path_completion_action(fish_tester):
    """Test that Path types trigger file completion."""
    tester = fish_tester(app_path, "pathapp")

    assert tester.validate_script_syntax()
    assert "-F" in tester.completion_script or "__fish_complete_directories" in tester.completion_script


def test_negative_flag_completion(fish_tester):
    """Test negative flag handling."""
    tester = fish_tester(app_negative, "negapp")

    script = tester.completion_script
    assert "--verbose" in script or "-l verbose" in script
    assert "--no-verbose" in script or "-l no-verbose" in script
    assert "--colors" in script or "-l colors" in script
    assert "--no-colors" in script or "-l no-colors" in script


def test_disabled_negative_flag_completion(fish_tester):
    """Test that negative flags are not generated when disabled via App default_parameter."""
    tester = fish_tester(app_disabled_negative, "disabledneg")

    script = tester.completion_script
    assert "--param" in script or "-l param" in script
    assert "--empty-param" not in script
    assert "-l empty-param" not in script


def test_script_syntax_validation(fish_tester):
    """Test that generated script has valid fish syntax."""
    tester = fish_tester(app_basic, "basic")

    assert tester.validate_script_syntax()


def test_completion_command_format(fish_tester):
    """Test that completion uses correct fish command format."""
    tester = fish_tester(app_basic, "myapp")

    assert "complete -c myapp" in tester.completion_script


def test_special_characters_in_choices(fish_tester):
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

    tester = fish_tester(app, "special")
    assert tester.validate_script_syntax()


def test_help_descriptions(fish_tester):
    """Test that help descriptions appear in completions."""
    tester = fish_tester(app_basic, "basic")

    assert "Enable verbose output" in tester.completion_script
    assert "Deploy to environment" in tester.completion_script


def test_subcommand_conditions(fish_tester):
    """Test that subcommands use proper fish conditions."""
    tester = fish_tester(app_nested, "nested")

    assert (
        "__fish_use_subcommand" in tester.completion_script or "__fish_seen_subcommand_from" in tester.completion_script
    )


def test_description_escaping(fish_tester):
    """Test that descriptions with special chars are properly escaped."""
    app = App(name="escape_test")

    @app.default
    def main(
        param1: Annotated[str, Parameter(help="Test 'single' quotes")] = "",
        param2: Annotated[str, Parameter(help='Test "double" quotes')] = "",
        param3: Annotated[str, Parameter(help="Test $variable and `backticks`")] = "",
    ):
        """Test app."""

    tester = fish_tester(app, "escape_test")
    assert tester.validate_script_syntax()


def test_special_chars_in_literal_choices(fish_tester):
    """Test that Literal choices with special characters are properly escaped."""
    app = App(name="special_choices")

    @app.default
    def main(
        choice: Annotated[Literal["foo bar", "baz()", "test[1]"], Parameter()] = "foo bar",
    ):
        """Test app with special chars in choices."""

    tester = fish_tester(app, "special_choices")
    assert tester.validate_script_syntax()


def test_unicode_in_descriptions(fish_tester):
    """Test that Unicode characters in descriptions are handled properly."""
    app = App(name="unicode_test")

    @app.default
    def main(
        emoji: Annotated[str, Parameter(help="Enable 🚀 rocket mode")] = "",
        chinese: Annotated[str, Parameter(help="中文描述")] = "",
        arabic: Annotated[str, Parameter(help="وصف بالعربية")] = "",
    ):
        """Test app with Unicode."""

    tester = fish_tester(app, "unicode_test")
    assert "🚀" in tester.completion_script or "rocket mode" in tester.completion_script
    assert tester.validate_script_syntax()


def test_deeply_nested_commands(fish_tester):
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

    tester = fish_tester(root, "root")

    assert "level1" in tester.completion_script
    assert "level2" in tester.completion_script
    assert "level3" in tester.completion_script
    assert "action" in tester.completion_script
    assert tester.validate_script_syntax()


def test_nested_command_disambiguation(fish_tester):
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

    tester = fish_tester(root, "myapp")

    script = tester.completion_script

    assert "__fish_myapp_using_command" in script, "Helper function should be generated"

    assert "'__fish_myapp_using_command config'" in script, "Should use helper for config path"
    assert "'__fish_myapp_using_command admin'" in script, "Should use helper for admin path"

    config_get_lines = [line for line in script.split("\n") if "config" in line.lower() and "get" in line.lower()]
    admin_get_lines = [line for line in script.split("\n") if "admin" in line.lower() and "get" in line.lower()]

    assert any("config key" in line.lower() or "config" in line for line in config_get_lines), (
        "Config get should have config-specific completions"
    )

    assert any("username" in line.lower() or "admin" in line for line in admin_get_lines), (
        "Admin get should have admin-specific completions"
    )

    assert tester.validate_script_syntax()


def test_helper_function_generation(fish_tester):
    """Test that helper function is only generated when needed."""
    root_only = App(name="rootonly")

    @root_only.default
    def main(verbose: bool = False):
        """Root only app."""
        pass

    tester_root = fish_tester(root_only, "rootonly")
    assert "__fish_rootonly_using_command" not in tester_root.completion_script, "No helper for root-only app"

    nested = App(name="nested")
    sub = App(name="sub")

    @sub.default
    def action():
        """Sub action."""
        pass

    nested.command(sub)

    tester_nested = fish_tester(nested, "nested")
    assert "__fish_nested_using_command" in tester_nested.completion_script, "Helper should be generated for nested app"


def test_flag_vs_option_distinction(fish_tester):
    """Test that flags and options are distinguished correctly.

    Flags should not have -r (require parameter), while options should.
    """
    app = App(name="flagtest")

    @app.default
    def main(
        verbose: Annotated[bool, Parameter(help="Enable verbose")] = False,
        count: Annotated[int, Parameter(help="Count")] = 1,
    ):
        """Test app."""

    tester = fish_tester(app, "flagtest")

    lines = tester.completion_script.split("\n")

    verbose_lines = [line for line in lines if "verbose" in line.lower()]
    count_lines = [line for line in lines if "count" in line]

    has_verbose_flag_only = any("-l verbose" in line and "-r" not in line for line in verbose_lines)
    has_count_with_r = any("-l count" in line and "-r" in line for line in count_lines)

    assert has_verbose_flag_only, "Verbose flag should not require parameter"
    assert has_count_with_r, "Count option should require parameter"


def test_optional_path_completion(fish_tester):
    """Test that Optional[Path] and Path | None generate file completion."""
    tester = fish_tester(app_path, "pathapp")

    assert "-F" in tester.completion_script or "__fish_complete_directories" in tester.completion_script


def test_no_file_completion_for_strings(fish_tester):
    """Test that string options don't default to file completion."""
    app = App(name="strtest")

    @app.default
    def main(
        name: Annotated[str, Parameter(help="Name")] = "default",
    ):
        """Test app."""

    tester = fish_tester(app, "strtest")
    assert tester.validate_script_syntax()


def test_help_version_flags_in_subcommands(fish_tester):
    """Test that help and version flags appear in subcommand completions."""
    tester = fish_tester(app_basic, "basic")

    script_lines = tester.completion_script.split("\n")

    deploy_section = []
    in_deploy = False
    for line in script_lines:
        if "deploy" in line:
            in_deploy = True
        if in_deploy:
            deploy_section.append(line)
            if "__fish_seen_subcommand_from deploy" in line:
                for i in range(len(script_lines)):
                    if i > script_lines.index(line):
                        deploy_section.append(script_lines[i])
                        if "__fish_seen_subcommand_from" in script_lines[i] and "deploy" not in script_lines[i]:
                            break
                break

    deploy_text = "\n".join(deploy_section)

    assert "--help" in deploy_text or "-l help" in deploy_text


def test_empty_iterable_flag_completion(fish_tester):
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

    tester = fish_tester(app, "listapp")

    assert "--items" in tester.completion_script or "-l items" in tester.completion_script
    assert "--empty-items" in tester.completion_script or "-l empty-items" in tester.completion_script
    assert "--tags" in tester.completion_script or "-l tags" in tester.completion_script
    assert "--empty-tags" in tester.completion_script or "-l empty-tags" in tester.completion_script

    lines = tester.completion_script.split("\n")
    empty_items_lines = [line for line in lines if "empty-items" in line]

    for line in empty_items_lines:
        if "-l empty-items" in line:
            assert "-r" not in line, "Negative flags should not require parameter (-r)"

    assert tester.validate_script_syntax()


def test_helper_function_skips_option_values(fish_tester):
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

    tester = fish_tester(app, "myapp")
    script = tester.completion_script

    assert "options_with_values" in script, "Helper should track options that take values"
    assert "--config" in script or "config" in script

    lines = script.split("\n")
    options_line = None
    for line in lines:
        if "options_with_values" in line and "set -l" in line:
            options_line = line
            break

    assert options_line is not None, "Should have a line setting options_with_values"
    assert "--config" in options_line or "config" in options_line, "Should include --config in options_with_values"
    assert "--verbose" not in options_line, "Flags should not be in options_with_values"

    skip_check = [line for line in lines if "skip_next" in line]
    assert len(skip_check) > 0, "Helper should use skip_next logic to skip option values"

    assert tester.validate_script_syntax()


def test_markdown_markup_stripped_from_descriptions(fish_tester):
    """Test that markdown markup is stripped from help descriptions.

    Ensures that **bold**, *italic*, `code`, and other markdown syntax
    is properly removed from completion descriptions.
    """
    tester = fish_tester(app_markup, "markupapp")
    script = tester.completion_script

    assert "Enable verbose output with extra details" in script, "Should contain plain text version"
    assert "**verbose**" not in script, "Should not contain markdown bold syntax"
    assert "`extra`" not in script, "Should not contain markdown code syntax"

    assert "Choose execution mode: fast or slow" in script, "Should contain plain text version"
    assert "*execution*" not in script, "Should not contain markdown italic syntax"
    assert "**fast**" not in script, "Should not contain markdown bold in mode description"
    assert "**slow**" not in script, "Should not contain markdown bold in mode description"

    assert "Target environment like dev or prod" in script, "Should contain plain text version"
    assert "`environment`" not in script, "Should not contain markdown code in env description"
    assert "**dev**" not in script, "Should not contain markdown bold in env description"
    assert "**prod**" not in script, "Should not contain markdown bold in env description"

    assert "Deploy to environment" in script, "Should contain plain text command description"
    assert "`environment`" not in script, "Should not contain markdown code in command description"

    assert tester.validate_script_syntax()


def test_rst_markup_stripped_from_descriptions(fish_tester):
    """Test that RST markup is stripped from help descriptions.

    Ensures that **bold**, ``code``, and other RST syntax
    is properly removed from completion descriptions.
    """
    tester = fish_tester(app_rst, "rstapp")
    script = tester.completion_script

    assert "Enable verbose output with code samples" in script, "Should contain plain text version"
    assert "**verbose**" not in script, "Should not contain RST bold syntax"
    assert "``code``" not in script, "Should not contain RST code syntax (double backticks)"

    assert "Choose execution mode: fast or slow" in script, "Should contain plain text version"
    assert "*execution*" not in script, "Should not contain RST italic syntax"
    assert "**fast**" not in script, "Should not contain RST bold in mode description"
    assert "**slow**" not in script, "Should not contain RST bold in mode description"

    assert tester.validate_script_syntax()


def test_literal_with_show_choices_false(fish_tester):
    """Test that Literal with show_choices=False still provides completions.

    Regression test: When show_choices=False is set on a Literal parameter,
    the choices should still be available for shell completion, even though
    they are hidden from the help text.
    """
    app = App(name="deploy")

    @app.default
    def main(
        env: Annotated[
            Literal["dev", "staging", "prod"],
            Parameter(help="Environment to deploy to", show_choices=False),
        ],
    ):
        """Deploy to environment."""
        pass

    tester = fish_tester(app, "deploy")
    script = tester.completion_script

    # Choices should be in completion script even with show_choices=False
    assert "dev" in script
    assert "staging" in script
    assert "prod" in script


def test_command_with_multiple_names_and_aliases(fish_tester):
    """Test that commands registered with multiple names/aliases all appear in completions.

    Regression test for groups_from_app() deduplication - ensures all registered
    names are included in completion scripts.
    """
    app = App(name="myapp")
    sub = App()

    @sub.default
    def action(value: str = ""):
        """Perform an action."""
        pass

    app.command(sub, name="foo", alias=["bar", "baz"])

    tester = fish_tester(app, "myapp")
    script = tester.completion_script

    assert "foo" in script, "Primary name should be in completion script"
    assert "bar" in script, "First alias should be in completion script"
    assert "baz" in script, "Second alias should be in completion script"

    assert tester.validate_script_syntax()


def test_list_path_completion(fish_tester):
    """Test that list[Path] arguments generate file completion.

    Regression test for issue #654: list[Path] arguments should use
    file completion (-F) just like Path arguments.
    """
    tester = fish_tester(app_list_path, "listpath")
    script = tester.completion_script

    assert "-F" in script, "list[Path] should generate file completion"
    assert tester.validate_script_syntax()
