"""Shell completion installation utilities.

This module handles the installation of completion scripts to shell-specific
locations and the updating of shell RC files to load completions.
"""

from pathlib import Path
from typing import Literal


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
