import pytest

from .apps import (
    app_basic,
    app_enum,
    app_negative,
    app_nested,
    app_path,
)


def test_basic_option_completion(zsh_tester):
    """Test basic option name completion."""
    tester = zsh_tester(app_basic, "basic")

    assert "--verbose" in tester.completion_script
    assert "--count" in tester.completion_script
    assert "--help" in tester.completion_script


def test_command_completion(zsh_tester):
    """Test command completion."""
    tester = zsh_tester(app_basic, "basic")

    assert "deploy" in tester.completion_script


def test_literal_value_completion(zsh_tester):
    """Test Literal type value completion."""
    tester = zsh_tester(app_basic, "basic")

    assert "dev" in tester.completion_script
    assert "staging" in tester.completion_script
    assert "prod" in tester.completion_script


def test_enum_value_completion(zsh_tester):
    """Test Enum type value completion."""
    tester = zsh_tester(app_enum, "enumapp")

    assert "fast" in tester.completion_script
    assert "slow" in tester.completion_script


def test_nested_subcommand_completion(zsh_tester):
    """Test nested subcommand completion."""
    tester = zsh_tester(app_nested, "nested")

    assert "config" in tester.completion_script
    assert "get" in tester.completion_script
    assert "set" in tester.completion_script


def test_negative_flag_completion(zsh_tester):
    """Test negative flag completion."""
    tester = zsh_tester(app_negative, "negapp")

    assert "--no-verbose" in tester.completion_script
    assert "--no-colors" in tester.completion_script


def test_help_descriptions(zsh_tester):
    """Test that help descriptions appear in completions."""
    tester = zsh_tester(app_basic, "basic")

    assert "Enable verbose output" in tester.completion_script
    assert "Deploy to environment" in tester.completion_script


def test_script_syntax_valid(zsh_tester):
    """Test that generated script has valid zsh syntax."""
    tester = zsh_tester(app_basic, "basic")

    assert tester.validate_script_syntax()


def test_compdef_header(zsh_tester):
    """Test that script has proper #compdef header."""
    tester = zsh_tester(app_basic, "basic")

    assert tester.completion_script.startswith("#compdef basic")


def test_path_completion(zsh_tester):
    """Test that Path types generate file completion."""
    tester = zsh_tester(app_path, "pathapp")

    assert "_files" in tester.completion_script


@pytest.mark.slow
def test_end_to_end_option_completion(zsh_tester):
    """End-to-end test: actually trigger zsh completion for options.

    This test uses zpty to simulate real completion.
    Marked as slow since it spawns subprocess.
    """
    tester = zsh_tester(app_basic, "basic")

    completions = tester.get_completions("basic --")

    assert any("--verbose" in c for c in completions)
    assert any("--count" in c for c in completions)
    assert any("--help" in c for c in completions)


@pytest.mark.slow
def test_end_to_end_command_completion(zsh_tester):
    """End-to-end test: actually trigger zsh completion for commands.

    This test uses zpty to simulate real completion.
    Marked as slow since it spawns subprocess.
    """
    tester = zsh_tester(app_basic, "basic")

    completions = tester.get_completions("basic ")

    assert any("deploy" in c for c in completions)
