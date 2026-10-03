"""Shell completion installation utilities.

This module handles the installation of completion scripts to shell-specific
locations and the updating of shell RC files to load completions.
"""

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal

from cyclopts.parameter import Parameter


def _detect_omz_completions_dir() -> Path | None:
    """Detect oh-my-zsh custom completions directory.

    Uses ``$ZSH_CUSTOM/completions`` (the recommended location for user
    completions in oh-my-zsh). Falls back to ``$ZSH/custom/completions``
    when ``$ZSH_CUSTOM`` is not set.

    Returns
    -------
    Path | None
        Path to the oh-my-zsh custom completions directory, or None if
        oh-my-zsh is not detected.
    """
    zsh_custom_str = os.environ.get("ZSH_CUSTOM")
    if zsh_custom_str:
        zsh_custom = Path(zsh_custom_str)
        if zsh_custom.is_dir():
            return zsh_custom / "completions"
    zsh_dir_str = os.environ.get("ZSH")
    if not zsh_dir_str:
        return None
    zsh_dir = Path(zsh_dir_str)
    if zsh_dir.is_dir():
        return zsh_dir / "custom" / "completions"
    return None


def _powershell_executable() -> str:
    r"""``pwsh`` (PowerShell 7+) or ``powershell`` (Windows PowerShell 5.1), whichever is likely running us.

    PowerShell 7 adds its own module directories (``...\PowerShell\Modules``) to
    ``PSModulePath`` for child processes; Windows PowerShell's are all ``...\WindowsPowerShell\...``.
    """
    if sys.platform != "win32":
        return "pwsh"
    paths = os.environ.get("PSModulePath", "").lower().split(os.pathsep)
    return "pwsh" if any("\\powershell\\" in path for path in paths) else "powershell"


def powershell_profile() -> Path:
    """The current user's all-hosts PowerShell profile (``$PROFILE.CurrentUserAllHosts``).

    Asks PowerShell, since Windows may redirect Documents (e.g. into OneDrive).
    """
    executable = _powershell_executable()
    try:
        result = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-Command", "$PROFILE.CurrentUserAllHosts"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        pass
    home = Path.home()
    if sys.platform != "win32":
        return home / ".config" / "powershell" / "profile.ps1"
    return home / "Documents" / ("PowerShell" if executable == "pwsh" else "WindowsPowerShell") / "profile.ps1"


def get_default_completion_path(shell: Literal["zsh", "bash", "fish", "powershell"], prog_name: str) -> Path:
    """Get the default completion script path for a given shell.

    Parameters
    ----------
    shell : Literal["zsh", "bash", "fish", "powershell"]
        Shell type.
    prog_name : str
        Program name for the completion script.

    Returns
    -------
    Path
        Default installation path for the shell.

    Raises
    ------
    ValueError
        If shell type is unsupported.
    """
    home = Path.home()
    if shell == "zsh":
        # Namespace the file as ``_cyclopts_<prog>`` so the autoload entry
        # doesn't shadow zsh helpers (``_files``, ``_directories``, etc.) when
        # ``<prog>`` happens to match one.
        omz_completions = _detect_omz_completions_dir()
        if omz_completions is not None:
            omz_completions.mkdir(parents=True, exist_ok=True)
            return omz_completions / f"_cyclopts_{prog_name}"
        # Vanilla zsh fallback
        zsh_completions = home / ".zsh" / "completions"
        zsh_completions.mkdir(parents=True, exist_ok=True)
        return zsh_completions / f"_cyclopts_{prog_name}"
    elif shell == "bash":
        bash_completions = home / ".local" / "share" / "bash-completion" / "completions"
        bash_completions.mkdir(parents=True, exist_ok=True)
        return bash_completions / prog_name
    elif shell == "fish":
        fish_completions = home / ".config" / "fish" / "completions"
        fish_completions.mkdir(parents=True, exist_ok=True)
        return fish_completions / f"{prog_name}.fish"
    elif shell == "powershell":
        powershell_completions = powershell_profile().parent / "Completions"
        powershell_completions.mkdir(parents=True, exist_ok=True)
        return powershell_completions / f"{prog_name}.ps1"
    else:
        raise ValueError(f"Unsupported shell: {shell}")


def _powershell_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def add_to_rc_file(script_path: Path, prog_name: str, shell: Literal["bash", "zsh", "powershell"]) -> bool:
    """Add completion configuration to shell RC file.

    For bash, adds a source line to load the completion script.
    For zsh, adds the completion directory to fpath so compinit can find it.
    For PowerShell, adds a dot-source line to the current user's all-hosts profile.

    Parameters
    ----------
    script_path : Path
        Path to the completion script.
    prog_name : str
        Program name for display in comments.
    shell : Literal["bash", "zsh", "powershell"]
        Shell type.

    Returns
    -------
    bool
        True if configuration was added, False if it already existed or on error.
    """
    prog_name = prog_name.replace("\r", " ").replace("\n", " ")
    if shell == "bash":
        rc_file = Path.home() / ".bashrc"
        config_line = f'[ -f "{script_path}" ] && . "{script_path}"'
        comment = f"# Load {prog_name} completion"
    elif shell == "zsh":
        if _detect_omz_completions_dir():
            return False
        rc_file = Path.home() / ".zshrc"
        completion_dir = script_path.parent
        config_line = f"fpath=({completion_dir} $fpath)"
        comment = f"# {prog_name} completions"
    elif shell == "powershell":
        rc_file = powershell_profile()
        quoted = _powershell_quote(script_path)
        config_line = f"if (Test-Path {quoted}) {{ . {quoted} }}"
        comment = f"# Load {prog_name} completion"
    else:
        raise NotImplementedError

    rc_file = rc_file.resolve()

    if rc_file.exists():
        content = rc_file.read_text()
        # For zsh, check if this directory is already in fpath configuration
        # For bash, check if the exact source line exists
        if shell == "zsh" and str(script_path.parent) in content and "fpath=" in content:
            return False
        elif config_line in content:
            return False
    else:
        content = ""

    if shell == "zsh":
        # Prepend to ensure fpath is set before any compinit call
        rc_file.write_text(f"{comment}\n{config_line}\n{content}")
    else:
        # Bash/PowerShell: append
        rc_file.parent.mkdir(parents=True, exist_ok=True)
        needs_newline = content and not content.endswith("\n")
        with rc_file.open("a") as f:
            if needs_newline:
                f.write("\n")
            f.write(f"{comment}\n{config_line}\n")

    return True


def _check_mark() -> str:
    """``✓``, or ``*`` when stdout can't encode it (redirected output on Windows is typically cp1252)."""
    try:
        "✓".encode(sys.stdout.encoding or "utf-8")
    except (UnicodeEncodeError, LookupError):
        return "*"
    return "✓"


def create_install_completion_command(
    install_completion_fn: Callable[..., Path],
    add_to_startup: bool,
):
    """Create a command function for installing shell completion.

    Parameters
    ----------
    install_completion_fn : Callable
        Function that performs the actual installation (typically App.install_completion).
        Should accept (shell, output, add_to_startup) and return the installation path.
    add_to_startup : bool
        Whether to add source line to shell RC file.

    Returns
    -------
    Callable
        Command function that can be registered with App.command().
    """

    def _install_completion_command(
        *,
        shell: Annotated[Literal["zsh", "bash", "fish", "powershell"] | None, Parameter()] = None,
        output: Annotated[Path | None, Parameter(name=["-o", "--output"])] = None,
    ):
        """Install shell completion for this application.

        This command generates and installs the completion script to the appropriate
        location for your shell. After installation, you may need to restart your
        shell or source your shell configuration file.

        Parameters
        ----------
        shell : Literal["zsh", "bash", "fish", "powershell"] | None
            Shell type for completion. If not specified, attempts to auto-detect current shell.
        output : Path | None
            Output path for the completion script. If not specified, uses shell-specific default.
        """
        from cyclopts.completion.detect import ShellDetectionError, detect_shell

        if shell is None:
            try:
                shell = detect_shell()
            except ShellDetectionError:
                print(
                    "Could not auto-detect shell. Please specify --shell explicitly.",
                    file=sys.stderr,
                )
                sys.exit(1)

        install_path = install_completion_fn(shell=shell, output=output, add_to_startup=add_to_startup)
        mark = _check_mark()

        print(f"{mark} Completion script installed to {install_path}")

        if shell == "zsh":
            if _detect_omz_completions_dir():
                print(f"{mark} Detected oh-my-zsh: completions directory is already in $fpath.")
                print("\nRestart your shell or run: exec zsh")
            elif add_to_startup:
                zshrc = Path.home() / ".zshrc"
                completion_dir = install_path.parent
                print(f"{mark} Added {completion_dir} to fpath in {zshrc}")
                print("\nNote: Ensure compinit is configured in your .zshrc (most zsh setups already have this).")
                print("Restart your shell or run: exec zsh")
            else:
                completion_dir = install_path.parent
                print(f"\nTo enable completions, ensure {completion_dir} is in your $fpath.")
                print("Add this to your ~/.zshrc or ~/.zprofile if not already present:")
                print(f"    fpath=({completion_dir} $fpath)")
                print("    autoload -Uz compinit && compinit")
                print("\nThen restart your shell or run: exec zsh")
        elif shell == "bash":
            if add_to_startup:
                bashrc = Path.home() / ".bashrc"
                print(f"{mark} Added completion loader to {bashrc}")
                print("\nRestart your shell or run: source ~/.bashrc")
            else:
                print("\nCompletions will be automatically loaded by bash-completion.")
                print("If completions don't work:")
                print("  1. Ensure bash-completion is installed (v2.8+)")
                print("  2. Restart your shell or run: exec bash")
                print("\nNote: bash-completion is typically installed via:")
                print("  - macOS: brew install bash-completion@2")
                print("  - Debian/Ubuntu: apt install bash-completion")
                print("  - Fedora/RHEL: dnf install bash-completion")
        elif shell == "fish":
            print("\nCompletions are automatically loaded in fish.")
            print("Restart your shell or run: source ~/.config/fish/config.fish")
        elif shell == "powershell":
            if add_to_startup:
                profile = powershell_profile()
                print(f"{mark} Added completion loader to {profile}")
                print(f"\nRestart PowerShell or run: . {_powershell_quote(profile)}")
            else:
                print("\nTo enable completions, add this line to your PowerShell profile ($PROFILE):")
                print(f"    . {_powershell_quote(install_path)}")
            if sys.platform == "win32":
                print("\nIf PowerShell reports that running scripts is disabled, allow local scripts with:")
                print("    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned")
        else:
            raise NotImplementedError

    return _install_completion_command
