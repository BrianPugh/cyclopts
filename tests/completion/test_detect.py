"""Tests for shell detection functionality."""

import subprocess
from unittest.mock import Mock

import pytest

from cyclopts.completion import ShellDetectionError, detect_shell


@pytest.mark.parametrize(
    ("env_var", "version", "expected"),
    [
        ("ZSH_VERSION", "5.8", "zsh"),
        ("BASH_VERSION", "5.0.0", "bash"),
        ("FISH_VERSION", "3.3.0", "fish"),
    ],
)
def test_detect_shell_via_version_variable(monkeypatch, env_var, version, expected):
    """Test detection of shell via version environment variables."""
    monkeypatch.setenv(env_var, version)
    assert detect_shell() == expected


@pytest.mark.parametrize(
    ("primary_var", "primary_version", "secondary_var", "secondary_version", "expected"),
    [
        ("ZSH_VERSION", "5.8", "BASH_VERSION", "5.0.0", "zsh"),
        ("BASH_VERSION", "5.0.0", "FISH_VERSION", "3.3.0", "bash"),
    ],
)
def test_version_variable_priority(
    monkeypatch, primary_var, primary_version, secondary_var, secondary_version, expected
):
    """Test that higher priority version variables take precedence."""
    monkeypatch.setenv(primary_var, primary_version)
    monkeypatch.setenv(secondary_var, secondary_version)
    assert detect_shell() == expected


def _mock_failed_subprocess(monkeypatch):
    """Helper to mock failed subprocess for testing fallback behavior."""
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)


def test_detect_shell_no_detection_methods_available(monkeypatch):
    """Test that ShellDetectionError is raised when no detection methods succeed."""
    monkeypatch.delenv("ZSH_VERSION", raising=False)
    monkeypatch.delenv("BASH_VERSION", raising=False)
    monkeypatch.delenv("FISH_VERSION", raising=False)
    monkeypatch.delenv("SHELL", raising=False)
    _mock_failed_subprocess(monkeypatch)

    with pytest.raises(ShellDetectionError) as exc_info:
        detect_shell()

    assert "Unable to detect shell type" in str(exc_info.value)


def test_detect_shell_empty_string_not_detected(monkeypatch):
    """Test that empty string environment variables don't trigger detection."""
    monkeypatch.setenv("ZSH_VERSION", "")
    monkeypatch.setenv("BASH_VERSION", "")
    monkeypatch.setenv("FISH_VERSION", "")
    monkeypatch.delenv("SHELL", raising=False)
    _mock_failed_subprocess(monkeypatch)

    with pytest.raises(ShellDetectionError):
        detect_shell()


@pytest.mark.parametrize(
    ("shell_path", "expected"),
    [
        ("/bin/zsh", "zsh"),
        ("/usr/bin/bash", "bash"),
        ("/usr/local/bin/fish", "fish"),
        ("/bin/ZSH", "zsh"),
        ("/opt/homebrew/bin/fish", "fish"),
    ],
)
def test_detect_shell_fallback_to_shell_variable(monkeypatch, shell_path, expected):
    """Test fallback to SHELL variable for various paths."""
    monkeypatch.delenv("ZSH_VERSION", raising=False)
    monkeypatch.delenv("BASH_VERSION", raising=False)
    monkeypatch.delenv("FISH_VERSION", raising=False)
    monkeypatch.setenv("SHELL", shell_path)
    _mock_failed_subprocess(monkeypatch)

    assert detect_shell() == expected


def test_version_variable_takes_priority_over_shell(monkeypatch):
    """Test that version variables take priority over SHELL variable."""
    monkeypatch.setenv("BASH_VERSION", "5.0.0")
    monkeypatch.setenv("SHELL", "/bin/zsh")

    assert detect_shell() == "bash"


def test_detect_shell_fallback_unsupported_shell(monkeypatch):
    """Test that unsupported shells in SHELL variable raise error."""
    monkeypatch.delenv("ZSH_VERSION", raising=False)
    monkeypatch.delenv("BASH_VERSION", raising=False)
    monkeypatch.delenv("FISH_VERSION", raising=False)
    monkeypatch.setenv("SHELL", "/bin/ksh")
    _mock_failed_subprocess(monkeypatch)

    with pytest.raises(ShellDetectionError):
        detect_shell()
