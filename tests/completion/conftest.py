import subprocess
import tempfile
from pathlib import Path

import pytest


class ZshCompletionTester:
    """Test zsh completion by executing real zsh subprocess.

    Uses actual zsh completion system to validate generated scripts.
    Requires zsh 5.0+ to be installed.
    """

    def __init__(self, completion_script: str, prog_name: str):
        self.completion_script = completion_script
        self.prog_name = prog_name

    def validate_script_syntax(self) -> bool:
        """Check if the completion script has valid zsh syntax.

        Returns
        -------
        bool
            True if syntax is valid, False otherwise.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            comp_file = tmpdir / f"_{self.prog_name}"
            comp_file.write_text(self.completion_script)

            result = subprocess.run(
                ["zsh", "-n", str(comp_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )

            return result.returncode == 0

    def get_completions(self, partial_command: str) -> list[str]:
        """Get completion suggestions for partial command using zpty.

        Parameters
        ----------
        partial_command : str
            Partial command line, e.g., "myapp --verb"

        Returns
        -------
        list[str]
            Completion suggestions
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            comp_file = tmpdir / f"_{self.prog_name}"
            comp_file.write_text(self.completion_script)

            zsh_script = f"""
            fpath=({tmpdir} $fpath)
            autoload -Uz compinit && compinit -u

            zmodload zsh/zpty

            comptest () {{
                zstyle ':completion:*:default' list-colors 'no=<C>' 'lc=' 'rc=' 'ec=</C>'
                zstyle ':completion:*' group-name ''

                bindkey '^I' complete-word
                zle -C {{,,}}complete-word
                complete-word () {{
                    unset 'compstate[vared]'
                    compadd -x $'\\C-B'
                    _main_complete "$@"
                    compadd -J -last- -x $'\\C-C'
                    exit
                }}

                vared -c tmp
            }}

            zpty {{,}}comptest

            zpty -w comptest $'{partial_command}\\t'
            zpty -r comptest REPLY $'*\\C-B'
            zpty -r comptest REPLY $'*\\C-C'

            print -r -- "${{REPLY%$'\\C-C'}}"

            zpty -d comptest
            """

            result = subprocess.run(
                ["zsh", "-c", zsh_script],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Zsh completion test failed: {result.stderr}")

            output = result.stdout.strip()
            if not output:
                return []

            completions = []
            for line in output.split("\n"):
                line = line.strip()
                if line and not line.startswith("<"):
                    completions.append(line)

            return completions


def _check_zsh_available():
    """Check if zsh is available and meets minimum version requirement.

    Returns
    -------
    bool
        True if zsh 5.0+ is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["zsh", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            version_str = result.stdout.strip()
            if "zsh" in version_str.lower():
                return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return False


@pytest.fixture(scope="session")
def zsh_available():
    """Check if zsh is available for testing."""
    return _check_zsh_available()


@pytest.fixture
def zsh_tester(zsh_available):
    """Fixture for ZshCompletionTester.

    Parameters
    ----------
    zsh_available : bool
        Whether zsh is available for testing.

    Returns
    -------
    callable
        Factory function that creates ZshCompletionTester instances.
    """
    if not zsh_available:
        pytest.skip("zsh not available")

    def _make_tester(app, prog_name="testapp"):
        from cyclopts.completion.zsh import generate_completion_script

        script = generate_completion_script(app, prog_name)
        return ZshCompletionTester(script, prog_name)

    return _make_tester
