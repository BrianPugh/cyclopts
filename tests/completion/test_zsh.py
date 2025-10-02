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


def test_command_prefix_completion(zsh_tester):
    """End-to-end test: verify command name prefix completion works.

    This test verifies that typing "d" and pressing TAB completes to "deploy".
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

            child.send("basic d")
            child.send("\t")

            time.sleep(0.3)

            child.send(" MARKER\r")

            child.expect(["% ", "# ", r"\$ "], timeout=2)
            output = child.before

            import re

            clean_output = re.sub(r"\x1b\[[^a-zA-Z]*[a-zA-Z]", "", output)
            clean_output = re.sub(r"\x1b\].*?\x07", "", clean_output)
            clean_output = re.sub(r"[\x00-\x1f\x7f]", "", clean_output)

            assert "deploy" in clean_output and "MARKER" in clean_output

        finally:
            child.close()


def test_optional_path_completion(zsh_tester):
    """Test that Optional[Path] and Path | None generate file completion."""
    tester = zsh_tester(app_path, "pathapp")

    assert "'--output[Output file]:output:_files'" in tester.completion_script


def test_nested_command_uses_correct_word_index(zsh_tester):
    """Test that nested commands use $words[1] for subcommand dispatch."""
    tester = zsh_tester(app_nested, "nested")

    script_lines = tester.completion_script.split("\n")
    words_checks = [line for line in script_lines if "case $words[1] in" in line]

    assert len(words_checks) >= 2, "Should have multiple case $words[1] checks for nested commands"


def test_invalid_prog_name():
    """Test that invalid prog names raise ValueError."""
    from cyclopts.completion import generate_completion_script

    with pytest.raises(ValueError, match="Invalid prog_name"):
        generate_completion_script(app_basic, "foo bar")

    with pytest.raises(ValueError, match="Invalid prog_name"):
        generate_completion_script(app_basic, "test;rm -rf /")

    with pytest.raises(ValueError, match="Invalid prog_name"):
        generate_completion_script(app_basic, "")


def test_description_escaping(zsh_tester):
    """Test that descriptions with special chars are properly escaped."""
    from typing import Annotated

    from cyclopts import App, Parameter

    app = App(name="escape_test")

    @app.default
    def main(
        param1: Annotated[str, Parameter(help="Test 'single' quotes")] = "",
        param2: Annotated[str, Parameter(help='Test "double" quotes')] = "",
        param3: Annotated[str, Parameter(help="Test $variable and `backticks`")] = "",
        param4: Annotated[str, Parameter(help="Test [brackets] here")] = "",
    ):
        """Test app."""

    tester = zsh_tester(app, "escape_test")

    assert r"'\'' " in tester.completion_script or "'\\''" in tester.completion_script
    assert "\\$" in tester.completion_script
    assert "\\`" in tester.completion_script
    assert r"\[" in tester.completion_script
    assert r"\]" in tester.completion_script


def test_special_chars_in_literal_choices(zsh_tester):
    """Test that Literal choices with special characters are properly escaped."""
    from typing import Annotated, Literal

    from cyclopts import App, Parameter

    app = App(name="special_choices")

    @app.default
    def main(
        choice: Annotated[Literal["foo bar", "baz()", "test[1]", "back\\slash"], Parameter()] = "foo bar",
    ):
        """Test app with special chars in choices."""

    tester = zsh_tester(app, "special_choices")

    assert r"foo\ bar" in tester.completion_script
    assert r"baz\(\)" in tester.completion_script
    assert r"test\[1\]" in tester.completion_script
    assert r"back\\slash" in tester.completion_script


def test_unicode_in_descriptions(zsh_tester):
    """Test that Unicode characters in descriptions are handled properly."""
    from typing import Annotated

    from cyclopts import App, Parameter

    app = App(name="unicode_test")

    @app.default
    def main(
        emoji: Annotated[str, Parameter(help="Enable 🚀 rocket mode")] = "",
        chinese: Annotated[str, Parameter(help="中文描述")] = "",
        arabic: Annotated[str, Parameter(help="وصف بالعربية")] = "",
    ):
        """Test app with Unicode."""

    tester = zsh_tester(app, "unicode_test")

    assert "🚀" in tester.completion_script or "rocket mode" in tester.completion_script
    assert tester.validate_script_syntax()


def test_deeply_nested_commands(zsh_tester):
    """Test completion for deeply nested commands (3+ levels)."""
    from cyclopts import App

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

    tester = zsh_tester(root, "root")

    assert "level1" in tester.completion_script
    assert "level2" in tester.completion_script
    assert "level3" in tester.completion_script
    assert "action" in tester.completion_script
    assert tester.validate_script_syntax()
