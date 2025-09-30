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
        """Get completion suggestions for partial command using pexpect.

        Parameters
        ----------
        partial_command : str
            Partial command line, e.g., "myapp --verb"

        Returns
        -------
        list[str]
            Completion suggestions (words that appeared after TAB)
        """
        try:
            import pexpect
        except ImportError:
            pytest.skip("pexpect not available for end-to-end testing")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            comp_file = tmpdir / f"_{self.prog_name}"
            comp_file.write_text(self.completion_script)

            child = pexpect.spawn("zsh -i", encoding="utf-8", timeout=3)

            try:
                child.expect(["% ", "# ", r"\$ ", "zsh-"], timeout=2)

                child.sendline(f"fpath=({tmpdir} $fpath)")
                child.expect(["% ", "# ", r"\$ "])

                child.sendline("autoload -Uz compinit && compinit -u")
                child.expect(["% ", "# ", r"\$ "])

                child.send(partial_command)
                child.send("\t")

                try:
                    child.expect([r"\r\n", pexpect.TIMEOUT], timeout=0.5)
                    output = child.before
                except pexpect.TIMEOUT:
                    output = child.before or ""

                child.sendline("\x03")

                completions = []
                if output:
                    for line in output.split("\n"):
                        line = line.strip()
                        if line and not line.startswith(partial_command.split()[0]):
                            words = line.split()
                            completions.extend(words)

                return completions

            finally:
                child.close()


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
