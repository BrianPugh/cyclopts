"""Shell completion generation for Cyclopts applications."""

from cyclopts.completion.detect import ShellDetectionError, detect_shell

__all__ = ["detect_shell", "ShellDetectionError"]
