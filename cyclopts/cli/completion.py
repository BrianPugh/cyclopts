"""Shell completion CLI commands."""

import sys
from pathlib import Path
from typing import Annotated, Literal

from cyclopts.cli import app
from cyclopts.completion.detect import ShellDetectionError, detect_shell
from cyclopts.parameter import Parameter


def _get_completion_install_path(shell: str, prog_name: str) -> Path:
    """Get the appropriate completion installation path for the given shell."""
    home = Path.home()

    if shell == "zsh":
        # Prefer user's local completion directory
        # This directory should be added to fpath in .zshrc
        zsh_completions = home / ".zsh" / "completions"
        zsh_completions.mkdir(parents=True, exist_ok=True)
        return zsh_completions / f"_{prog_name}"
    elif shell == "bash":
        return home / ".bash_completion"
    elif shell == "fish":
        fish_completions = home / ".config" / "fish" / "completions"
        fish_completions.mkdir(parents=True, exist_ok=True)
        return fish_completions / f"{prog_name}.fish"
    else:
        raise ValueError(f"Unsupported shell: {shell}")


@app.command(name="--install-completion")
def install_completion(
    *,
    shell: Annotated[Literal["zsh", "bash", "fish"] | None, Parameter()] = None,
    output: Annotated[Path | None, Parameter(name=["-o", "--output"])] = None,
):
    """Install shell completion for cyclopts CLI.

    This command generates and installs the completion script to the appropriate
    location for your shell. After installation, you may need to restart your
    shell or source your shell configuration file.

    Parameters
    ----------
    shell : Literal["zsh", "bash", "fish"] | None
        Shell type for completion. If not specified, attempts to auto-detect current shell.
    output : Path | None
        Output path for the completion script. If not specified, uses shell-specific default.

    Examples
    --------
    Auto-detect shell and install:
        cyclopts install-completion

    Install for specific shell:
        cyclopts install-completion --shell zsh

    Install to custom path:
        cyclopts install-completion --output /custom/path/to/completion

    Notes
    -----
    Installation locations:
    - zsh: ~/.zsh/completions/_<prog_name>
    - bash: ~/.bash_completion
    - fish: ~/.config/fish/completions/<prog_name>.fish
    """
    if shell is None:
        try:
            shell = detect_shell()
        except ShellDetectionError:
            print(
                "Could not auto-detect shell. Please specify --shell explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)

    script_content = app.generate_completion(shell=shell)
    install_path = output if output is not None else _get_completion_install_path(shell, app.name[0])
    install_path.parent.mkdir(parents=True, exist_ok=True)
    install_path.write_text(script_content)

    print(f"✓ Completion script installed to {install_path}")

    if shell == "zsh":
        completion_dir = install_path.parent
        print(f"\nTo enable completions, ensure {completion_dir} is in your $fpath.")
        print("Add this to your ~/.zshrc or ~/.zprofile if not already present:")
        print(f"    fpath=({completion_dir} $fpath)")
        print("    autoload -Uz compinit && compinit")
        print("\nThen restart your shell or run: exec zsh")
    elif shell == "bash":
        print("\nTo enable completions, source the completion file:")
        print("  Add this to your ~/.bashrc:")
        print("    [ -f ~/.bash_completion ] && source ~/.bash_completion")
        print("\nThen restart your shell or run: source ~/.bashrc")
    elif shell == "fish":
        print("\nCompletions are automatically loaded in fish.")
        print("Restart your shell or run: source ~/.config/fish/config.fish")
    else:
        raise NotImplementedError
