"""Shell detection utilities for completion generation.

This module provides functionality to detect the current shell type by inspecting
environment variables. This is useful for dynamically generating appropriate completion
scripts for different shell environments.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Literal


class ShellDetectionError(Exception):
    """Raised when the shell type cannot be detected."""


def _extract_shell_name(shell_string: str) -> Literal["zsh", "bash", "fish", "powershell"] | None:
    """Extract shell name from a string (path or process name).

    Parameters
    ----------
    shell_string : str
        String that may contain a shell name (e.g., "/bin/bash", "zsh", "-bash").

    Returns
    -------
    Literal["zsh", "bash", "fish", "powershell"] | None
        The detected shell type, or None if not recognized.
    """
    shell_lower = shell_string.lower()
    if "zsh" in shell_lower:
        return "zsh"
    elif "bash" in shell_lower:
        return "bash"
    elif "fish" in shell_lower:
        return "fish"
    elif "pwsh" in shell_lower or "powershell" in shell_lower:
        return "powershell"
    return None


def _running_in_windows_powershell() -> bool:
    """Whether a PowerShell session (either edition) launched us on Windows.

    Windows has no ``ps`` for the parent-process check. Both PowerShell editions
    add the user's own module directory (under their home) to ``PSModulePath``
    for child processes, while the system-wide default (what ``cmd.exe`` sees)
    has none.
    """
    if sys.platform != "win32":
        return False
    home = str(Path.home()).lower()
    return any(path.lower().startswith(home) for path in os.environ.get("PSModulePath", "").split(os.pathsep) if path)


def detect_shell() -> Literal["zsh", "bash", "fish", "powershell"]:
    """Detect the current shell type using multiple detection methods.

    Returns
    -------
    Literal["zsh", "bash", "fish", "powershell"]
        The detected shell type.

    Raises
    ------
    ShellDetectionError
        If the shell type cannot be determined from any detection method.

    Examples
    --------
    >>> shell = detect_shell()  # doctest: +SKIP
    >>> print(f"Detected shell: {shell}")  # doctest: +SKIP
    Detected shell: bash
    """
    if os.environ.get("ZSH_VERSION"):
        return "zsh"
    elif os.environ.get("BASH_VERSION"):
        return "bash"
    elif os.environ.get("FISH_VERSION"):
        return "fish"

    try:
        ppid = os.getppid()
        result = subprocess.run(
            ["ps", "-p", str(ppid), "-o", "comm="],
            capture_output=True,
            text=True,
            timeout=1,
        )
        if result.returncode == 0 and result.stdout:
            parent_process = result.stdout.strip()
            shell = _extract_shell_name(parent_process)
            if shell:
                return shell
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        shell_name = Path(shell_path).name
        shell = _extract_shell_name(shell_name)
        if shell:
            return shell

    if _running_in_windows_powershell():
        return "powershell"

    raise ShellDetectionError("Unable to detect shell type.")
