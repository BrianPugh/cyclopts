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
    from cyclopts.completion.zsh import generate_completion_script

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


def test_no_trailing_colons_in_specs(zsh_tester):
    """Test that argument specs don't have trailing colons when action is empty.

    Regression test for issue where specs like '1:description:' or '*:args:'
    would cause zsh eval errors. When there's no completion action, the spec
    should be '1:description' or '*:args' (no trailing colon).
    """
    from typing import Annotated

    from cyclopts import App, Parameter

    app = App(name="notrail")

    @app.command
    def run(
        pos1: Annotated[str, Parameter(help="First positional")],
        pos2: Annotated[int, Parameter(help="Second positional")],
        *args: Annotated[str, Parameter(help="Variadic args")],
    ):
        """Command with positionals."""
        pass

    @app.default
    def main(
        flag: Annotated[str, Parameter(help="A non-path option")],
    ):
        """Main command."""
        pass

    tester = zsh_tester(app, "notrail")

    # Check for problematic trailing colons (but not in file/directory actions)
    for line in tester.completion_script.split("\n"):
        stripped = line.strip()
        # Skip comments and lines with valid actions
        if stripped.startswith("#") or ":_files" in line or ":_directories" in line:
            continue
        # Check for trailing :'  patterns (ignoring quote escaping)
        if line.rstrip().endswith(":'") or line.rstrip().endswith(":' \\"):
            if "'\\'':" not in line:  # Not part of quote escaping in descriptions
                raise AssertionError(f"Found trailing colon in spec: {line}")

    assert tester.validate_script_syntax()


def test_colon_escaping_in_descriptions(zsh_tester):
    """Test that colons in descriptions are escaped to prevent field separator issues.

    Regression test for issue where colons in positional argument descriptions
    like '::app_object' would be treated as field separators in specs like
    '1:message:action', causing unmatched quote errors.
    """
    from typing import Annotated

    from cyclopts import App, Parameter

    app = App(name="colontest")

    @app.command
    def run(
        script: Annotated[str, Parameter(help="Path with '::app' notation")],
    ):
        """Command with colon in description."""
        pass

    tester = zsh_tester(app, "colontest")

    assert r"\:\:" in tester.completion_script
    assert tester.validate_script_syntax()


def test_run_command_only_special_for_cyclopts(zsh_tester):
    """Test that 'run' command only gets dynamic completion for cyclopts CLI, not user apps.

    Regression test for issue where any app with a 'run' command would get
    dynamic completion instead of normal static completion.
    """
    from typing import Annotated

    from cyclopts import App, Parameter

    app = App(name="myapp")

    @app.command
    def run(
        script: Annotated[str, Parameter(help="Script to execute")],
        verbose: Annotated[bool, Parameter(help="Verbose mode")] = False,
    ):
        """Run a script."""
        pass

    tester = zsh_tester(app, "myapp")

    # Should generate normal static completion, not dynamic completion
    # Dynamic completion has "local script_path", "local -a completions", etc.
    assert "local script_path" not in tester.completion_script
    assert "_complete run" not in tester.completion_script

    # Should have normal argument specs for the run command
    assert "--verbose" in tester.completion_script or "verbose" in tester.completion_script.lower()
    assert tester.validate_script_syntax()


def test_cyclopts_run_command_has_dynamic_completion(zsh_tester):
    """Test that cyclopts CLI's 'run' command gets dynamic completion."""
    from cyclopts.cli import app as cyclopts_app

    tester = zsh_tester(cyclopts_app, "cyclopts")

    # Should have dynamic completion for the run command
    assert "local script_path" in tester.completion_script
    assert "_complete run" in tester.completion_script
    assert tester.validate_script_syntax()


def test_empty_iterable_flag_completion(zsh_tester):
    """Test that --empty-* flags for list parameters are treated as flags.

    Regression test for issue where --empty-items on list[str] parameters
    would expect a value instead of being treated as a flag.
    """
    from typing import Annotated

    from cyclopts import App, Parameter

    app = App(name="listapp")

    @app.command
    def process(
        items: Annotated[list[str], Parameter(help="Items to process")],
        tags: Annotated[list[str] | None, Parameter(help="Optional tags")] = None,
        count: Annotated[int, Parameter(help="Count")] = 1,
    ):
        """Process items."""
        pass

    tester = zsh_tester(app, "listapp")

    # Both positive and negative flags should be present
    assert "--items" in tester.completion_script
    assert "--empty-items" in tester.completion_script
    assert "--tags" in tester.completion_script
    assert "--empty-tags" in tester.completion_script
    assert "--count" in tester.completion_script

    # Negative flags should be formatted as flags (no trailing :action)
    # They should have the format '--empty-items[description]' not '--empty-items[description]:empty-items'
    assert "'--empty-items[Items to process]'" in tester.completion_script
    assert "'--empty-tags[Optional tags]'" in tester.completion_script

    # Positive names should expect values (have :action or :name suffix)
    lines_with_items = [line for line in tester.completion_script.split("\n") if "'--items[" in line]
    assert any(
        ":items:" in line or ":items'" in line for line in lines_with_items
    ), "Positive --items flag should expect a value"

    assert tester.validate_script_syntax()


def test_completion_after_empty_flag(zsh_tester):
    """Test that completion works after using an --empty-* flag.

    Regression test for: cyclopts-demo process --empty-items --<TAB> should show other options.
    """
    pexpect = pytest.importorskip("pexpect")

    import tempfile
    import time
    from pathlib import Path
    from typing import Annotated

    from cyclopts import App, Parameter

    app = App(name="testapp")

    @app.command
    def process(
        items: Annotated[list[str], Parameter(help="Items to process")],
        count: Annotated[int, Parameter(help="Count")] = 1,
        verbose: Annotated[bool, Parameter(help="Verbose")] = False,
    ):
        """Process items."""
        pass

    tester = zsh_tester(app, "testapp")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        comp_file = tmpdir / "_testapp"
        comp_file.write_text(tester.completion_script)

        child = pexpect.spawn("zsh -i", encoding="utf-8", timeout=3)

        try:
            child.expect(["% ", "# ", r"\$ ", "zsh-"], timeout=2)

            child.sendline(f"fpath=({tmpdir} $fpath)")
            child.expect(["% ", "# ", r"\$ "])

            child.sendline("autoload -Uz compinit && compinit -u")
            child.expect(["% ", "# ", r"\$ "])

            # Type: testapp process --empty-items --c<TAB>
            child.send("testapp process --empty-items --c")
            child.send("\t")

            time.sleep(0.3)

            child.send(" MARKER\r")

            child.expect(["% ", "# ", r"\$ "], timeout=2)
            output = child.before

            import re

            clean_output = re.sub(r"\x1b\[[^a-zA-Z]*[a-zA-Z]", "", output)
            clean_output = re.sub(r"\x1b\].*?\x07", "", clean_output)
            clean_output = re.sub(r"[\x00-\x1f\x7f]", "", clean_output)

            # Should complete to --count
            # Note: MARKER may be corrupted by terminal escape sequences during completion display,
            # so we check for MARK (prefix) instead of full MARKER string
            assert (
                "--count" in clean_output and "MARK" in clean_output
            ), f"Expected --count and MARK in output, got: {clean_output}"

        finally:
            child.close()


def test_positional_or_keyword_literal_completion(zsh_tester):
    """Test that POSITIONAL_OR_KEYWORD Literal arguments generate positional completion.

    Regression test for issue where 'cyclopts-demo deploy d<TAB>' should complete
    to 'dev' but no completions were shown. The environment parameter is
    POSITIONAL_OR_KEYWORD (not positional-only) and has Literal choices.
    """
    from typing import Literal

    from cyclopts import App

    app = App(name="testapp")

    @app.command
    def deploy(
        environment: Literal["dev", "staging", "production"],
        region: Literal["us-east-1", "us-west-2"] = "us-east-1",
    ):
        """Deploy to environment.

        Parameters
        ----------
        environment : Literal["dev", "staging", "production"]
            Target environment.
        region : Literal["us-east-1", "us-west-2"]
            AWS region.
        """
        pass

    tester = zsh_tester(app, "testapp")

    # Should have positional spec for first argument (1-indexed in zsh)
    assert "'1:Target environment.:(dev staging production)'" in tester.completion_script or (
        "1:Target environment.:(dev staging production)" in tester.completion_script
    )

    # Should also have keyword spec for --environment
    assert "--environment" in tester.completion_script
    assert "(dev staging production)" in tester.completion_script

    # Should have positional spec for second argument
    assert "'2:AWS region.:(us-east-1 us-west-2)'" in tester.completion_script or (
        "2:AWS region.:(us-east-1 us-west-2)" in tester.completion_script
    )

    assert tester.validate_script_syntax()


def test_help_version_flags_in_subcommands(zsh_tester):
    """Test that help and version flags appear in subcommand completions.

    Regression test for issue where --help and --version were only available
    in the root command but not in subcommands.
    """
    tester = zsh_tester(app_basic, "basic")

    script_lines = tester.completion_script.split("\n")

    in_deploy = False
    deploy_section = []
    for i, line in enumerate(script_lines):
        if "deploy)" in line and not in_deploy:
            in_deploy = True
        if in_deploy:
            deploy_section.append(line)
            if ";;" in line and i > 0:
                break

    deploy_text = "\n".join(deploy_section)

    assert "--help[Display this message and exit.]" in deploy_text
    assert "-h[Display this message and exit.]" in deploy_text
    assert "--version[Display application version.]" in deploy_text
