import subprocess
import tempfile
from pathlib import Path

import pytest


class BashCompletionTester:
    """Test bash completion by executing real bash subprocess.

    Uses actual bash completion system to validate generated scripts.
    Requires bash 3.2+ (macOS) or 4.0+ (Linux) to be installed.
    """

    def __init__(self, completion_script: str, prog_name: str):
        self.completion_script = completion_script
        self.prog_name = prog_name

    def validate_script_syntax(self) -> bool:
        """Check if the completion script has valid bash syntax.

        Returns
        -------
        bool
            True if syntax is valid, False otherwise.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            comp_file = tmpdir / f"{self.prog_name}_completion.bash"
            comp_file.write_text(self.completion_script)

            result = subprocess.run(
                ["bash", "-n", str(comp_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )

            return result.returncode == 0

    def get_completions(self, partial_command: str) -> list[str]:
        """Get completion suggestions for partial command.

        Parameters
        ----------
        partial_command : str
            Partial command line, e.g., "myapp --verb"

        Returns
        -------
        list[str]
            Completion suggestions from COMPREPLY array.
        """
        try:
            import pexpect
        except ImportError:
            pytest.skip("pexpect not available for end-to-end testing")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            comp_file = tmpdir / f"{self.prog_name}_completion.bash"
            comp_file.write_text(self.completion_script)

            child = pexpect.spawn("bash --norc -i", encoding="utf-8", timeout=3)

            try:
                child.expect([r"\$", r"bash-"], timeout=2)

                child.sendline(f"source {comp_file}")
                child.expect([r"\$", r"bash-"])

                child.send(partial_command)
                child.send("\t\t")

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
        script = app.generate_completion(prog_name=prog_name, shell="zsh")
        return ZshCompletionTester(script, prog_name)

    return _make_tester


def _check_bash_available():
    """Check if bash is available and meets minimum version requirement.

    Returns
    -------
    bool
        True if bash 3.2+ is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["bash", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            version_str = result.stdout.strip()
            if "bash" in version_str.lower():
                return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return False


@pytest.fixture(scope="session")
def bash_available():
    """Check if bash is available for testing."""
    return _check_bash_available()


@pytest.fixture
def bash_tester(bash_available):
    """Fixture for BashCompletionTester.

    Parameters
    ----------
    bash_available : bool
        Whether bash is available for testing.

    Returns
    -------
    callable
        Factory function that creates BashCompletionTester instances.
    """
    if not bash_available:
        pytest.skip("bash not available")

    def _make_tester(app, prog_name="testapp"):
        script = app.generate_completion(prog_name=prog_name, shell="bash")
        return BashCompletionTester(script, prog_name)

    return _make_tester


class FishCompletionTester:
    """Test fish completion by executing real fish subprocess.

    Uses actual fish completion system to validate generated scripts.
    Requires fish 3.0+ to be installed.

    Testing Approach
    ----------------
    Most tests should use `validate_script_syntax()` and verify script content
    directly via string assertions. The `get_completions()` method is fragile
    and should be used sparingly due to:
    - Dependency on pexpect and interactive shell behavior
    - Sensitivity to fish version output format changes
    - Potential issues with custom prompt configurations
    - Difficulty handling completions with whitespace

    For robust testing, prefer validating the generated script structure
    rather than relying on interactive completion behavior.
    """

    def __init__(self, completion_script: str, prog_name: str):
        self.completion_script = completion_script
        self.prog_name = prog_name

    def validate_script_syntax(self) -> bool:
        """Check if the completion script has valid fish syntax.

        Returns
        -------
        bool
            True if syntax is valid, False otherwise.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            comp_file = tmpdir / f"{self.prog_name}.fish"
            comp_file.write_text(self.completion_script)

            result = subprocess.run(
                ["fish", "-n", str(comp_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )

            return result.returncode == 0

    def get_completions(self, partial_command: str) -> list[str]:
        """Get completion suggestions for partial command using pexpect.

        NOTE: This implementation is fragile and makes assumptions about fish's
        interactive output format. It parses the completion output by:
        1. Looking for lines that don't start with the command name
        2. Splitting lines by whitespace to extract completion words

        This may break with:
        - Different fish versions that format output differently
        - Custom fish prompt configurations
        - Completions containing whitespace or special formatting

        For more robust testing, consider using fish's --print-completions flag
        when it becomes available in future fish versions.

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

            comp_file = tmpdir / f"{self.prog_name}.fish"
            comp_file.write_text(self.completion_script)

            child = pexpect.spawn("fish", encoding="utf-8", timeout=3)

            try:
                child.expect([r"> ", r"~> ", r"\$ "], timeout=2)

                child.sendline(f"source {comp_file}")
                child.expect([r"> ", r"~> ", r"\$ "])

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


def _check_fish_available():
    """Check if fish is available and meets minimum version requirement.

    Returns
    -------
    bool
        True if fish 3.0+ is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["fish", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            version_str = result.stdout.strip()
            if "fish" in version_str.lower():
                return True
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return False


@pytest.fixture(scope="session")
def fish_available():
    """Check if fish is available for testing."""
    return _check_fish_available()


@pytest.fixture
def fish_tester(fish_available):
    """Fixture for FishCompletionTester.

    Parameters
    ----------
    fish_available : bool
        Whether fish is available for testing.

    Returns
    -------
    callable
        Factory function that creates FishCompletionTester instances.
    """
    if not fish_available:
        pytest.skip("fish not available")

    def _make_tester(app, prog_name="testapp"):
        script = app.generate_completion(prog_name=prog_name, shell="fish")
        return FishCompletionTester(script, prog_name)

    return _make_tester
