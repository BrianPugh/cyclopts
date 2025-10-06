"""Tests for bash completion script generation."""

import pytest

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


def test_generate_completion_script_not_implemented():
    """Test that bash completion raises NotImplementedError until implemented."""
    with pytest.raises(NotImplementedError, match="Bash completion support is not yet implemented"):
        generate_completion_script(app_basic, "basic")


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_basic_option_completion(bash_tester):
    """Test basic option name completion."""
    tester = bash_tester(app_basic, "basic")

    assert "--verbose" in tester.completion_script
    assert "--count" in tester.completion_script
    assert "--help" in tester.completion_script


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_command_completion(bash_tester):
    """Test command completion."""
    tester = bash_tester(app_basic, "basic")

    assert "deploy" in tester.completion_script


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_literal_value_completion(bash_tester):
    """Test Literal type value completion."""
    tester = bash_tester(app_basic, "basic")

    assert "dev" in tester.completion_script
    assert "staging" in tester.completion_script
    assert "prod" in tester.completion_script


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_enum_value_completion(bash_tester):
    """Test Enum type value completion."""
    tester = bash_tester(app_enum, "enumapp")

    assert "fast" in tester.completion_script
    assert "slow" in tester.completion_script


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_nested_subcommand_completion(bash_tester):
    """Test nested subcommand completion."""
    tester = bash_tester(app_nested, "nested")

    assert "config" in tester.completion_script
    assert "get" in tester.completion_script
    assert "set" in tester.completion_script


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_path_completion_action(bash_tester):
    """Test that Path types trigger file completion."""
    tester = bash_tester(app_path, "pathapp")

    assert tester.validate_script_syntax()


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_negative_flag_completion(bash_tester):
    """Test negative flag handling."""
    tester = bash_tester(app_negative, "negapp")

    assert "--verbose" in tester.completion_script
    assert "--no-verbose" in tester.completion_script
    assert "--colors" in tester.completion_script
    assert "--no-colors" in tester.completion_script


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_script_syntax_validation(bash_tester):
    """Test that generated script has valid bash syntax."""
    tester = bash_tester(app_basic, "basic")

    assert tester.validate_script_syntax()


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_completion_function_naming(bash_tester):
    """Test that completion function uses correct naming convention."""
    tester = bash_tester(app_basic, "myapp")

    assert "_myapp" in tester.completion_script or "_myapp_completion" in tester.completion_script
    assert "complete -F" in tester.completion_script


@pytest.mark.skip(reason="Bash completion not yet implemented")
def test_special_characters_in_choices(bash_tester):
    """Test that special characters in choices are properly escaped."""
    from typing import Annotated, Literal

    from cyclopts import App, Parameter

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
