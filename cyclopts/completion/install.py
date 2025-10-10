"""Shell completion installation utilities.

This module handles the installation of completion scripts to shell-specific
locations and the updating of shell RC files to load completions.
"""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal

from cyclopts.parameter import Parameter


def get_default_completion_path(shell: Literal["zsh", "bash", "fish"], prog_name: str) -> Path:
    """Get the default completion script path for a given shell.

    Parameters
    ----------
    shell : Literal["zsh", "bash", "fish"]
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
        zsh_completions = home / ".zsh" / "completions"
        zsh_completions.mkdir(parents=True, exist_ok=True)
        return zsh_completions / f"_{prog_name}"
    elif shell == "bash":
        bash_completions = home / ".local" / "share" / "bash-completion" / "completions"
        bash_completions.mkdir(parents=True, exist_ok=True)
        return bash_completions / prog_name
    elif shell == "fish":
        fish_completions = home / ".config" / "fish" / "completions"
        fish_completions.mkdir(parents=True, exist_ok=True)
        return fish_completions / f"{prog_name}.fish"
    else:
        raise ValueError(f"Unsupported shell: {shell}")


def add_to_rc_file(script_path: Path, prog_name: str, shell: Literal["bash", "zsh"]) -> bool:
    """Add source line to shell RC file to ensure completion is loaded.

    Parameters
    ----------
    script_path : Path
        Path to the completion script.
    prog_name : str
        Program name for display in comments.
    shell : Literal["bash", "zsh"]
        Shell type.

    Returns
    -------
    bool
        True if the source line was added, False if it already existed or on error.
    """
    if shell == "bash":
        rc_file = Path.home() / ".bashrc"
        source_line = f'[ -f "{script_path}" ] && . "{script_path}"'
    elif shell == "zsh":
        rc_file = Path.home() / ".zshrc"
        source_line = f'[ -f "{script_path}" ] && . "{script_path}"'
    else:
        raise NotImplementedError

    rc_file = rc_file.resolve()

    if rc_file.exists():
        content = rc_file.read_text()
        if source_line in content:
            return False
        needs_newline = content and not content.endswith("\n")
    else:
        needs_newline = False

    with rc_file.open("a") as f:
        if needs_newline:
            f.write("\n")
        f.write(f"# Load {prog_name} completion\n{source_line}\n")

    return True


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
        shell: Annotated[Literal["zsh", "bash", "fish"] | None, Parameter()] = None,
        output: Annotated[Path | None, Parameter(name=["-o", "--output"])] = None,
    ):
        """Install shell completion for this application.

        This command generates and installs the completion script to the appropriate
        location for your shell. After installation, you may need to restart your
        shell or source your shell configuration file.

        Parameters
        ----------
        shell : Literal["zsh", "bash", "fish"] | None
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

        print(f"✓ Completion script installed to {install_path}")

        if shell == "zsh":
            if add_to_startup:
                zshrc = Path.home() / ".zshrc"
                print(f"✓ Added completion loader to {zshrc}")
                print("\nRestart your shell or run: source ~/.zshrc")
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
                print(f"✓ Added completion loader to {bashrc}")
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
        else:
            raise NotImplementedError

    return _install_completion_command
