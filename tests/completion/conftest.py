r"""Shell-completion test harness.

Each shell exposes two capabilities:

* ``validate_script_syntax()`` - runs ``{bash,zsh,fish} -n`` on the generated
  script. Already non-interactive.
* ``get_completions(partial)`` - returns the list of suggestions a user would
  see for a partial command line.

  * **Bash** - spawn ``bash -c``, source the completion script, populate
    ``COMP_WORDS`` using a ``COMP_WORDBREAKS``-aware tokenizer (default
    ``WORDBREAKS`` includes ``=`` and ``:``, which matters for ``--opt=value``
    and ``host:port`` forms), invoke the registered ``_<prog>`` function, and
    print ``COMPREPLY``. No TTY, no timing. Bash 3.2-safe (the mac-stock
    version).
  * **Fish** - use fish's built-in ``complete -C '<partial>'`` flag. Prints
    ``completion\tdescription`` one per line. Deterministic since fish 3.0.
  * **Zsh** - drive an interactive ``zsh -i`` via ``pexpect`` and ask it to
    *list* matches without modifying the line by sending the
    ``list-choices`` widget (``\e\C-d``). Matches are screen-scraped between
    two prompt sentinels. Skipped if ``pexpect`` is unavailable.
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

            # Tokenize the line the way real interactive bash does: split on
            # whitespace AND on every char in ``COMP_WORDBREAKS`` (default:
            # space tab newline " ' < > = ; | & ( :). Each break char becomes
            # its own word. Without this the driver can't probe ``--opt=value``
            # or ``host:port`` style completions.
            driver = (
                'source "$1"\n'
                'COMP_LINE="$2"\n'
                "COMP_POINT=${#COMP_LINE}\n"
                "COMP_WORDS=()\n"
                "COMPREPLY=()\n"
                "_word=''\n"
                "for ((_k=0; _k<${#COMP_LINE}; _k++)); do\n"
                '  _ch="${COMP_LINE:$_k:1}"\n'
                '  case "$_ch" in\n'
                "    ' '|$'\\t'|$'\\n')\n"
                '      [[ -n "$_word" ]] && { COMP_WORDS+=("$_word"); _word=""; }\n'
                "      ;;\n"
                "    '\"'|\"'\"|'<'|'>'|'='|';'|'|'|'&'|'('|':')\n"
                '      [[ -n "$_word" ]] && { COMP_WORDS+=("$_word"); _word=""; }\n'
                '      COMP_WORDS+=("$_ch")\n'
                "      ;;\n"
                "    *)\n"
                '      _word+="$_ch"\n'
                "      ;;\n"
                "  esac\n"
                "done\n"
                # Final word: trailing whitespace means there's an empty
                # "current word" the user is about to type; otherwise the
                # accumulated word is the current word.
                'if [[ "${COMP_LINE: -1}" == " " || "${COMP_LINE: -1}" == $\'\\t\' ]]; then\n'
                '  [[ -n "$_word" ]] && COMP_WORDS+=("$_word")\n'
                '  COMP_WORDS+=("")\n'
                "else\n"
                '  COMP_WORDS+=("$_word")\n'
                "fi\n"
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


_ZSH_ANSI_RE = re.compile(r"\x1b\[[\d;?]*[a-zA-Z]|\x1b[=>()][a-zA-Z0-9]?|\x1b[=>]|\r|\x07|\x0e|\x0f")


class ZshCompletionTester(CompletionTesterBase):
    """Zsh completion tester driven via ``pexpect``.

    zsh's completion helpers (``_arguments``, ``_describe``, ``_files``) only
    run inside a real zle widget context, so the driver spawns an interactive
    ``zsh -i`` in a pty. To get matches without zsh inserting / cycling
    through them, the partial line is followed by the ``list-choices`` widget
    (``\\e\\C-d``), which lists matches in place and leaves the buffer
    untouched. Output is screen-scraped between two prompt sentinels and
    stripped of ANSI.

    Notes
    -----
    * Skipped if ``pexpect`` is not importable (e.g. Windows).
    * The TERM is forced to ``dumb`` to minimize control-byte noise.
    * ``ZDOTDIR`` is pointed at a temp dir so the host's ``.zshrc`` cannot
      perturb completion (custom widgets, ``zstyle`` settings, oh-my-zsh).
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
        try:
            import pexpect
        except ImportError:
            pytest.skip("pexpect not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            (td / f"_{self.prog_name}").write_text(self.completion_script)

            (td / ".zshrc").write_text(
                "PROMPT='ZTEST> '\n"
                f"fpath=({td} $fpath)\n"
                "autoload -Uz compinit && compinit -u\n"
                # Force "list, don't insert" semantics so we always see the
                # full set of matches even when there's only one.
                "unsetopt MENU_COMPLETE AUTO_MENU AUTO_LIST\n"
                "setopt NO_BEEP NO_LIST_BEEP\n"
                # Suppress descriptions/headers so each line is just matches.
                "zstyle ':completion:*' format ''\n"
                "zstyle ':completion:*:descriptions' format ''\n"
                "zstyle ':completion:*:messages' format ''\n"
                "zstyle ':completion:*:warnings' format ''\n"
                "zstyle ':completion:*' verbose no\n"
                "zstyle ':completion:*' group-name ''\n"
                "zstyle ':completion:*' list-prompt ''\n"
            )

            env_vars = {
                "HOME": str(td),
                "ZDOTDIR": str(td),
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "TERM": "dumb",
            }
            child = pexpect.spawn(
                "zsh -i",
                encoding="utf-8",
                env=env_vars,
                timeout=5,
                dimensions=(40, 400),
            )
            try:
                child.expect("ZTEST> ", timeout=4)
                child.send(partial_command)
                child.send("\x1b\x04")  # list-choices widget (Esc Ctrl-D)
                try:
                    child.expect("ZTEST> ", timeout=1.5)
                except pexpect.TIMEOUT:
                    pass
                output = child.before or ""
            finally:
                child.close(force=True)

        cleaned = _ZSH_ANSI_RE.sub("", output)
        # First line is the user's typed partial echoed back; subsequent
        # lines are the listed matches.
        lines = cleaned.split("\n")
        matches: list[str] = []
        for line in lines[1:]:
            for token in line.split():
                matches.append(token)
        return matches


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
