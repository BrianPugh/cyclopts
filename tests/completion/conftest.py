r"""Shell-completion test harness.

Each shell exposes two capabilities:

* ``validate_script_syntax()`` - runs ``{bash,zsh,fish} -n`` on the generated
  script. Already non-interactive.
* ``get_completions(partial)`` - returns the list of suggestions a user would
  see for a partial command line. Historically driven via ``pexpect`` with an
  interactive shell; that was fragile, disabled on macOS CI, and missing
  entirely for bash. The drivers below use **non-interactive** shell features
  wherever possible:

  * **Bash** - spawn ``bash -c``, source the completion script, set ``COMP_*``
    variables, invoke the registered ``_<prog>`` completion function by name,
    and print ``COMPREPLY``. No TTY, no timing. Bash 3.2-safe (the mac-stock
    version).
  * **Fish** - use fish's built-in ``complete -C '<partial>'`` flag. Prints
    ``completion\tdescription`` one per line. Deterministic since fish 3.0.
  * **Zsh** - zle's completion machinery refuses to run outside zle context
    (``_arguments`` errors with "can only be called from completion function"
    when invoked directly). A reliable non-interactive driver is deferred;
    ``get_completions`` currently skips, and zsh behavioral matrix rows are
    skipped as a result. ``validate_script_syntax`` plus the extensive
    string-content checks in ``test_zsh.py`` continue to cover zsh.
"""

import re
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import pytest


class CompletionTesterBase(ABC):
    """Base class for shell completion testers."""

    def __init__(self, completion_script: str, prog_name: str):
        self.completion_script = completion_script
        self.prog_name = prog_name

    @abstractmethod
    def validate_script_syntax(self) -> bool:
        """Return True if the generated script is syntactically valid for this shell."""

    @abstractmethod
    def get_completions(self, partial_command: str) -> list[str]:
        """Return the completion suggestions a real shell would offer for ``partial_command``."""


# --- Bash --------------------------------------------------------------------


_BASH_FUNC_RE = re.compile(r"^complete -F (\S+) ", re.MULTILINE)


class BashCompletionTester(CompletionTesterBase):
    """Bash completion tester using a non-interactive ``bash -c`` driver."""

    def validate_script_syntax(self) -> bool:
        with tempfile.TemporaryDirectory() as tmpdir:
            comp_file = Path(tmpdir) / f"{self.prog_name}_completion.bash"
            comp_file.write_text(self.completion_script)
            result = subprocess.run(
                ["bash", "-n", str(comp_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0

    def get_completions(self, partial_command: str) -> list[str]:
        match = _BASH_FUNC_RE.search(self.completion_script)
        if not match:
            raise RuntimeError("Could not locate 'complete -F <fn>' line in generated bash script")
        func_name = match.group(1)

        with tempfile.TemporaryDirectory() as tmpdir:
            comp_file = Path(tmpdir) / f"{self.prog_name}_completion.bash"
            comp_file.write_text(self.completion_script)

            driver = (
                'source "$1"\n'
                'COMP_LINE="$2"\n'
                "COMP_POINT=${#COMP_LINE}\n"
                "COMP_WORDS=()\n"
                "COMPREPLY=()\n"
                'read -ra COMP_WORDS <<< "$COMP_LINE"\n'
                'if [[ "$COMP_LINE" == *" " ]]; then COMP_WORDS+=(""); fi\n'
                "COMP_CWORD=$(( ${#COMP_WORDS[@]} - 1 ))\n"
                f'"{func_name}" "$3" "${{COMP_WORDS[COMP_CWORD]}}" "${{COMP_WORDS[COMP_CWORD-1]:-}}" >/dev/null\n'
                'printf "%s\\n" "${COMPREPLY[@]}"\n'
            )

            result = subprocess.run(
                ["bash", "-c", driver, "_", str(comp_file), partial_command, self.prog_name],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=tmpdir,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"bash driver failed (exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
                )
            return [line for line in result.stdout.splitlines() if line]


def _check_bash_available() -> bool:
    try:
        result = subprocess.run(["bash", "--version"], capture_output=True, text=True, timeout=2)
        return result.returncode == 0 and "bash" in result.stdout.lower()
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def bash_available():
    return _check_bash_available()


@pytest.fixture
def bash_tester(bash_available):
    if not bash_available:
        pytest.skip("bash not available")

    def _make_tester(app, prog_name="testapp"):
        script = app.generate_completion(prog_name=prog_name, shell="bash")
        return BashCompletionTester(script, prog_name)

    return _make_tester


# --- Fish --------------------------------------------------------------------


class FishCompletionTester(CompletionTesterBase):
    """Fish completion tester using the built-in non-interactive ``complete -C`` flag."""

    def validate_script_syntax(self) -> bool:
        with tempfile.TemporaryDirectory() as tmpdir:
            comp_file = Path(tmpdir) / f"{self.prog_name}.fish"
            comp_file.write_text(self.completion_script)
            result = subprocess.run(
                ["fish", "-n", str(comp_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0

    def get_completions(self, partial_command: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            comp_file = Path(tmpdir) / f"{self.prog_name}.fish"
            comp_file.write_text(self.completion_script)

            # `source` the completion then ask fish for completions of the partial line.
            # Single-quote the partial and escape any single quotes inside it.
            escaped = partial_command.replace("'", "\\'")
            script = f"source {comp_file}; complete -C '{escaped}'"
            result = subprocess.run(
                ["fish", "-c", script],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=tmpdir,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"fish driver failed (exit {result.returncode}): {result.stderr.strip() or result.stdout.strip()}"
                )
            # `complete -C` prints "completion\tdescription" per line (description optional).
            completions = []
            for line in result.stdout.splitlines():
                if not line:
                    continue
                completions.append(line.split("\t", 1)[0])
            return completions


def _check_fish_available() -> bool:
    try:
        result = subprocess.run(["fish", "--version"], capture_output=True, text=True, timeout=2)
        return result.returncode == 0 and "fish" in result.stdout.lower()
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def fish_available():
    return _check_fish_available()


@pytest.fixture
def fish_tester(fish_available):
    if not fish_available:
        pytest.skip("fish not available")

    def _make_tester(app, prog_name="testapp"):
        script = app.generate_completion(prog_name=prog_name, shell="fish")
        return FishCompletionTester(script, prog_name)

    return _make_tester


# --- Zsh ---------------------------------------------------------------------


class ZshCompletionTester(CompletionTesterBase):
    """Zsh completion tester.

    **Interactive completion driving is not currently supported.** zsh's
    completion helpers (``_arguments``, ``_describe``, ``_files``) refuse to
    run outside a real zle widget context, and the non-rc zle environment
    spawned by ``zsh -f`` doesn't bind TAB to completion. A reliable
    non-interactive zsh driver (zpty-based or otherwise) is deferred.

    For now, zsh tests rely on ``validate_script_syntax()`` plus string-level
    assertions in ``test_zsh.py`` to verify the generated script's structure.
    ``get_completions()`` raises ``pytest.skip`` so the cross-shell behavioral
    matrix degrades gracefully until a driver lands.
    """

    def validate_script_syntax(self) -> bool:
        with tempfile.TemporaryDirectory() as tmpdir:
            comp_file = Path(tmpdir) / f"_{self.prog_name}"
            comp_file.write_text(self.completion_script)
            result = subprocess.run(
                ["zsh", "-n", str(comp_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0

    def get_completions(self, partial_command: str) -> list[str]:
        pytest.skip("Interactive zsh completion driver is not yet implemented. See the ZshCompletionTester docstring.")


def _check_zsh_available() -> bool:
    try:
        result = subprocess.run(["zsh", "--version"], capture_output=True, text=True, timeout=2)
        return result.returncode == 0 and "zsh" in result.stdout.lower()
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def zsh_available():
    return _check_zsh_available()


@pytest.fixture
def zsh_tester(zsh_available):
    if not zsh_available:
        pytest.skip("zsh not available")

    def _make_tester(app, prog_name="testapp"):
        script = app.generate_completion(prog_name=prog_name, shell="zsh")
        return ZshCompletionTester(script, prog_name)

    return _make_tester
