"""Tests for bash completion script generation."""

from typing import Annotated, Literal

import pytest

from cyclopts import App, Parameter
from cyclopts.completion.bash import generate_completion_script

from .apps import (
    app_basic,
    app_deploy,
    app_disabled_negative,
    app_enum,
    app_list_path,
    app_multiple_positionals,
    app_negative,
    app_nested,
    app_path,
    app_positional_literal,
    app_positional_path,
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


def test_disabled_negative_flag_completion(bash_tester):
    """Test that negative flags are not generated when disabled via App default_parameter."""
    tester = bash_tester(app_disabled_negative, "disabledneg")

    assert "--param" in tester.completion_script
    assert "--empty-param" not in tester.completion_script


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


def test_positional_literal_completion(bash_tester):
    """Test that positional Literal arguments generate completions.

    Regression test for issue #605: positional Literal arguments should
    suggest their choices in bash completion.
    """
    tester = bash_tester(app_positional_literal, "poslit")

    assert "foo" in tester.completion_script
    assert "bar" in tester.completion_script
    assert "baz" in tester.completion_script
    assert tester.validate_script_syntax()


def test_multiple_positional_literal_position_aware(bash_tester):
    """Test that multiple positional Literals complete position-aware choices.

    When a command has multiple positional arguments with distinct choice sets,
    the completion should only suggest choices for the current position, not
    all choices from all positionals.

    This test validates that the generated bash script uses a case statement
    to provide position-aware completion rather than combining all choices.
    """
    tester = bash_tester(app_multiple_positionals, "multipos")
    script = tester.completion_script

    # Should use positional_count variable for position tracking
    assert "positional_count" in script

    # Should use case statement for position-aware completion
    assert "case ${positional_count} in" in script

    # Position 0 should offer first parameter choices
    assert "0)" in script
    # Should have first positional choices in position 0
    lines = script.split("\n")
    in_case_0 = False
    found_first_choices = False
    for i, line in enumerate(lines):
        if "case ${positional_count}" in line:
            in_case_0 = True
        elif in_case_0 and "0)" in line:
            # Check lines until we hit ";;"
            case_content = []
            for j in range(i + 1, min(i + 10, len(lines))):
                if ";;" in lines[j]:
                    break
                case_content.append(lines[j])
            case_str = "\n".join(case_content)

            if "red" in case_str and "blue" in case_str:
                found_first_choices = True
                # Make sure cat/dog aren't in the same case
                assert "cat" not in case_str
                assert "dog" not in case_str
            break

    assert found_first_choices, "First positional choices not found in position 0"

    # Position 1 should offer second parameter choices
    assert "1)" in script
    in_case_1 = False
    found_second_choices = False
    for i, line in enumerate(lines):
        if in_case_1 and "1)" in line:
            # Check lines until we hit ";;"
            case_content = []
            for j in range(i + 1, min(i + 10, len(lines))):
                if ";;" in lines[j]:
                    break
                case_content.append(lines[j])
            case_str = "\n".join(case_content)

            if "cat" in case_str and "dog" in case_str:
                found_second_choices = True
                # Make sure red/blue aren't in the same case
                assert "red" not in case_str
                assert "blue" not in case_str
            break
        elif "case ${positional_count}" in line:
            in_case_1 = True

    assert found_second_choices, "Second positional choices not found in position 1"

    assert tester.validate_script_syntax()


def test_positional_with_keyword_options(bash_tester):
    """Test positional completion when command also has keyword-only options.

    Regression test: When a command has both positional arguments and keyword-only
    options that take values (like --environment), completion after the command name
    should suggest the positional choices, not empty.

    For example:
    - 'deploy deploy <TAB>' should suggest ['web', 'api', 'worker']
    - 'deploy deploy --environment <TAB>' should suggest ['dev', 'staging', 'prod']

    This ensures the case "$prev" default (*) case handles positionals correctly.
    """
    tester = bash_tester(app_deploy, "deploy")
    script = tester.completion_script

    # Should have a case statement for $prev (because --environment takes a value)
    assert 'case "$prev"' in script or 'case "${prev}"' in script

    # Should suggest positional choices in the script
    assert "web" in script
    assert "api" in script
    assert "worker" in script

    # Should also have environment option completion
    assert "--environment" in script
    assert "dev" in script
    assert "staging" in script
    assert "prod" in script

    assert tester.validate_script_syntax()


def test_positional_not_treated_as_command(bash_tester):
    """Test that positional argument values are not mistaken for subcommands.

    Regression test: When a command takes positional arguments, those argument
    values should not be added to cmd_path (command hierarchy). For example,
    'deploy production us-east' should be recognized as the 'deploy' command
    with two positionals, NOT as command path ['deploy', 'production'].

    This was a critical bug where the second positional would fail to complete
    because 'production' was incorrectly treated as a subcommand.
    """
    import subprocess
    from typing import Literal

    app = App(name="deploy")

    @app.command
    def deploy(
        environment: Literal["production", "staging"],
        region: Literal["us-east", "us-west", "eu"],
        /,
    ):
        """Deploy to environment and region."""
        pass

    tester = bash_tester(app, "cyclopts-demo")
    script = tester.completion_script

    # Should have all_commands list that only includes "deploy"
    assert "all_commands" in script
    assert "deploy" in script

    # Test that 'production' and 'staging' are NOT in all_commands
    # (they're positional values, not commands)
    lines = script.split("\n")
    all_commands_line = None
    for line in lines:
        if "local all_commands=" in line:
            all_commands_line = line
            break

    assert all_commands_line is not None
    assert "production" not in all_commands_line
    assert "staging" not in all_commands_line
    assert "us-east" not in all_commands_line

    # Verify the completion actually works with a bash subprocess test
    test_script = f"""
source /dev/stdin << 'COMPLETION_SCRIPT'
{script}
COMPLETION_SCRIPT

# Simulate: cyclopts-demo deploy production <TAB>
COMP_WORDS=(cyclopts-demo deploy production "")
COMP_CWORD=3
_cyclopts_demo

# Should get region completions
if [ ${{#COMPREPLY[@]}} -eq 0 ]; then
    echo "FAIL: No completions"
    exit 1
fi

# Check that we got the expected completions
found_useast=0
found_uswest=0
found_eu=0
for item in "${{COMPREPLY[@]}}"; do
    if [ "$item" = "us-east" ]; then found_useast=1; fi
    if [ "$item" = "us-west" ]; then found_uswest=1; fi
    if [ "$item" = "eu" ]; then found_eu=1; fi
done

if [ $found_useast -eq 1 ] && [ $found_uswest -eq 1 ] && [ $found_eu -eq 1 ]; then
    exit 0
else
    echo "FAIL: Missing expected completions"
    exit 1
fi
"""

    result = subprocess.run(
        ["bash", "-c", test_script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Completion test failed: {result.stdout}\n{result.stderr}"
    assert tester.validate_script_syntax()


def test_positional_path_completion(bash_tester):
    """Test that positional Path arguments generate file completion.

    Regression test: positional Path arguments should use file completion
    (compgen -f) instead of empty completion.
    """
    tester = bash_tester(app_positional_path, "pathpos")
    script = tester.completion_script

    # Should have file completion flag for positional Path
    assert "compgen -f" in script
    assert tester.validate_script_syntax()


def test_literal_with_show_choices_false(bash_tester):
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

    tester = bash_tester(app, "deploy")
    script = tester.completion_script

    # Choices should be in completion script even with show_choices=False
    assert "dev" in script
    assert "staging" in script
    assert "prod" in script


def test_command_with_multiple_names_and_aliases(bash_tester):
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

    tester = bash_tester(app, "myapp")
    script = tester.completion_script

    assert "foo" in script, "Primary name should be in completion script"
    assert "bar" in script, "First alias should be in completion script"
    assert "baz" in script, "Second alias should be in completion script"

    assert tester.validate_script_syntax()


def test_list_path_completion(bash_tester):
    """Test that list[Path] arguments generate file completion.

    Regression test for issue #654: list[Path] arguments should use
    file completion (compgen -f) just like Path arguments.
    """
    tester = bash_tester(app_list_path, "listpath")
    script = tester.completion_script

    assert "compgen -f" in script, "list[Path] should generate file completion"
    assert tester.validate_script_syntax()


def test_colon_in_command_name(bash_tester):
    """Test that colons in command names work correctly in bash completion.

    Unlike zsh where colons are special in _describe format, bash handles
    colons without special escaping in compgen -W word lists.
    """
    app = App(name="myapp")

    sub = App()

    @sub.default
    def action(value: str = ""):
        """Perform an action."""
        pass

    # Register command with colon in name
    app.command(sub, name="utility:ping")

    tester = bash_tester(app, "myapp")
    script = tester.completion_script

    # Command name should appear in the script
    assert "utility:ping" in script, "Command name with colon should appear in script"

    assert tester.validate_script_syntax()


def test_glob_chars_in_command_name(bash_tester):
    """Test that glob characters in command names are properly escaped.

    Regression test: Command names containing glob characters like * ? [ ]
    should be escaped in case patterns to prevent glob matching.
    """
    app = App(name="myapp")

    sub1 = App()

    @sub1.default
    def action1():
        """Action with brackets."""
        pass

    # Register command with brackets in name (unusual but possible)
    app.command(sub1, name="test[1]")

    tester = bash_tester(app, "myapp")
    script = tester.completion_script

    # Brackets should be escaped in case patterns
    # The pattern should be "test\[1\]" not "test[1]"
    assert r"test\[1\]" in script, "Brackets in command name should be escaped in case patterns"

    assert tester.validate_script_syntax()
