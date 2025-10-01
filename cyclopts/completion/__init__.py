"""Shell completion generation for Cyclopts applications."""

from cyclopts.completion.detect import ShellDetectionError, detect_shell
from cyclopts.completion.zsh import generate_completion_script

__all__ = ["generate_completion_script", "detect_shell", "ShellDetectionError"]
