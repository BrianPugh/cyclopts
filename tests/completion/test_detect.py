"""Tests for shell detection functionality."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from cyclopts.completion import ShellDetectionError, detect_shell


@pytest.fixture
def clean_shell_env(monkeypatch):
    """Remove all shell version environment variables to ensure clean test environment."""
    monkeypatch.delenv("ZSH_VERSION", raising=False)
    monkeypatch.delenv("BASH_VERSION", raising=False)
    monkeypatch.delenv("FISH_VERSION", raising=False)
    monkeypatch.delenv("PSModulePath", raising=False)


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


def test_detect_shell_no_detection_methods_available(clean_shell_env, monkeypatch):
    """Test that ShellDetectionError is raised when no detection methods succeed."""
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
    monkeypatch.delenv("PSModulePath", raising=False)
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
def test_detect_shell_fallback_to_shell_variable(clean_shell_env, monkeypatch, shell_path, expected):
    """Test fallback to SHELL variable for various paths."""
    monkeypatch.setenv("SHELL", shell_path)
    _mock_failed_subprocess(monkeypatch)

    assert detect_shell() == expected


def test_version_variable_takes_priority_over_shell(monkeypatch):
    """Test that version variables take priority over SHELL variable."""
    monkeypatch.setenv("BASH_VERSION", "5.0.0")
    monkeypatch.setenv("SHELL", "/bin/zsh")

    assert detect_shell() == "bash"


def test_detect_shell_fallback_unsupported_shell(clean_shell_env, monkeypatch):
    """Test that unsupported shells in SHELL variable raise error."""
    monkeypatch.setenv("SHELL", "/bin/ksh")
    _mock_failed_subprocess(monkeypatch)

    with pytest.raises(ShellDetectionError):
        detect_shell()


@pytest.mark.parametrize(
    ("parent_process_name", "expected"),
    [
        ("zsh", "zsh"),
        ("/bin/bash", "bash"),
        ("/usr/local/bin/fish", "fish"),
        ("-zsh", "zsh"),
        ("login_bash", "bash"),
        ("pwsh", "powershell"),
        ("/usr/local/microsoft/powershell/7/pwsh", "powershell"),
    ],
)
def test_detect_shell_via_parent_process(clean_shell_env, monkeypatch, parent_process_name, expected):
    """Test detection via parent process when version variables are not available."""
    monkeypatch.delenv("SHELL", raising=False)

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = parent_process_name
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

    assert detect_shell() == expected


def test_detect_shell_subprocess_timeout_falls_back_to_shell_var(clean_shell_env, monkeypatch):
    """Test that subprocess timeout falls back to SHELL variable."""
    monkeypatch.setenv("SHELL", "/bin/zsh")

    def mock_subprocess_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1)

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    assert detect_shell() == "zsh"


def test_detect_shell_subprocess_error_falls_back_to_shell_var(clean_shell_env, monkeypatch):
    """Test that subprocess errors fall back to SHELL variable."""
    monkeypatch.setenv("SHELL", "/bin/bash")

    def mock_subprocess_run(*args, **kwargs):
        raise FileNotFoundError("ps command not found")

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    assert detect_shell() == "bash"


def test_detect_shell_subprocess_returns_unsupported_shell_falls_back(clean_shell_env, monkeypatch):
    """Test that unsupported parent process name falls back to SHELL variable."""
    monkeypatch.setenv("SHELL", "/bin/fish")

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "ksh"  # Unsupported shell
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

    assert detect_shell() == "fish"


@pytest.mark.parametrize(
    ("ps_module_path", "expected"),
    [
        (r"{home}\Documents\PowerShell\Modules;C:\Program Files\PowerShell\Modules", True),
        (r"{home}\Documents\WindowsPowerShell\Modules;C:\WINDOWS\system32\WindowsPowerShell\v1.0\Modules", True),
        (r"C:\Program Files\WindowsPowerShell\Modules;C:\WINDOWS\system32\WindowsPowerShell\v1.0\Modules", False),
    ],
)
def test_detect_shell_windows_powershell_module_path(clean_shell_env, monkeypatch, tmp_path, ps_module_path, expected):
    """On Windows (no ``ps``), a user-level ``PSModulePath`` entry means PowerShell launched us."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "pathsep", ";")
    monkeypatch.setattr(Path, "home", lambda: Path(r"C:\Users\me"))
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setenv("PSModulePath", ps_module_path.format(home=r"C:\Users\me"))
    _mock_failed_subprocess(monkeypatch)

    if expected:
        assert detect_shell() == "powershell"
    else:
        with pytest.raises(ShellDetectionError):
            detect_shell()
