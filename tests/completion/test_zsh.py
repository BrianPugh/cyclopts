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


def test_end_to_end_completion(zsh_tester):
    """End-to-end test: actually trigger zsh completion.

    This test uses pexpect to simulate real TAB completion.
    Requires pexpect to be installed (skip otherwise).
    """
    pexpect = pytest.importorskip("pexpect")

    import tempfile
    import time
    from pathlib import Path

    tester = zsh_tester(app_basic, "basic")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        comp_file = tmpdir / "_basic"
        comp_file.write_text(tester.completion_script)

        child = pexpect.spawn("zsh -i", encoding="utf-8", timeout=3)

        try:
            child.expect(["% ", "# ", r"\$ ", "zsh-"], timeout=2)

            child.sendline(f"fpath=({tmpdir} $fpath)")
            child.expect(["% ", "# ", r"\$ "])

            child.sendline("autoload -Uz compinit && compinit -u")
            child.expect(["% ", "# ", r"\$ "])

            child.send("basic --cou")
            child.send("\t")

            time.sleep(0.3)

            child.send(" MARKER\r")

            child.expect(["% ", "# ", r"\$ "], timeout=2)
            output = child.before

            import re

            clean_output = re.sub(r"\x1b\[[^a-zA-Z]*[a-zA-Z]", "", output)
            clean_output = re.sub(r"\x1b\].*?\x07", "", clean_output)
            clean_output = re.sub(r"[\x00-\x1f\x7f]", "", clean_output)

            assert "--count" in clean_output and "MARKER" in clean_output

        finally:
            child.close()
