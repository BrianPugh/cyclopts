"""Tests for cyclopts.loader module."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from cyclopts.loader import load_app_from_script


@pytest.fixture
def sample_app_script(tmp_path):
    """Create a sample script with a Cyclopts app."""
    script = tmp_path / "sample_app.py"
    script.write_text(
        """\
from cyclopts import App

app = App(name="sample")

@app.default
def main(value: str = "default"):
    return value
"""
    )
    return script


@pytest.fixture
def multi_app_script(tmp_path):
    """Create a script with multiple Cyclopts apps."""
    script = tmp_path / "multi_app.py"
    script.write_text(
        """\
from cyclopts import App

app1 = App(name="first")
app2 = App(name="second")

@app1.default
def main1():
    return "app1"

@app2.default
def main2():
    return "app2"
"""
    )
    return script


def test_load_basic_script(sample_app_script):
    """Test loading a basic script with one app."""
    app, name = load_app_from_script(sample_app_script)
    assert name == "app"
    assert "sample" in app.name


def test_load_with_explicit_app_name(multi_app_script):
    """Test loading with explicit app name using :: notation."""
    app, name = load_app_from_script(f"{multi_app_script}::app1")
    assert name == "app1"
    assert "first" in app.name

    app, name = load_app_from_script(f"{multi_app_script}::app2")
    assert name == "app2"
    assert "second" in app.name


def test_load_with_path_object(sample_app_script):
    """Test loading with Path object."""
    app, name = load_app_from_script(Path(sample_app_script))
    assert name == "app"
    assert "sample" in app.name


def test_nonexistent_file(tmp_path):
    """Test error handling for nonexistent file."""
    nonexistent = tmp_path / "nonexistent.py"
    with pytest.raises(SystemExit):
        load_app_from_script(nonexistent)


def test_non_python_file(tmp_path):
    """Test error handling for non-Python file."""
    txt_file = tmp_path / "not_python.txt"
    txt_file.write_text("This is not Python")
    with pytest.raises(SystemExit):
        load_app_from_script(txt_file)


def test_script_without_app(tmp_path):
    """Test error handling when script has no App objects."""
    script = tmp_path / "no_app.py"
    script.write_text("x = 42")
    with pytest.raises(SystemExit):
        load_app_from_script(script)


def test_invalid_app_name(sample_app_script):
    """Test error handling for invalid app name."""
    with pytest.raises(SystemExit):
        load_app_from_script(f"{sample_app_script}::nonexistent")


def test_not_an_app_object(tmp_path):
    """Test error when specified object is not an App."""
    script = tmp_path / "not_app.py"
    script.write_text(
        """\
not_an_app = "I am a string"
"""
    )
    with pytest.raises(SystemExit):
        load_app_from_script(f"{script}::not_an_app")


def test_multiple_apps_without_specification(multi_app_script):
    """Test error when multiple apps exist without specification."""
    with pytest.raises(SystemExit):
        load_app_from_script(multi_app_script)


def test_app_execution_suppressed(tmp_path):
    """Test that app() calls are suppressed during loading."""
    script = tmp_path / "executes.py"
    script.write_text(
        """\
from cyclopts import App

app = App()
executed = False

@app.default
def main():
    global executed
    executed = True
    return "executed"

# This call should be suppressed
result = app()
"""
    )
    app, _ = load_app_from_script(script)
    assert app is not None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_windows_path_with_backslashes(tmp_path):
    """Test loading script with Windows-style backslashes."""
    script = tmp_path / "windows_app.py"
    script.write_text(
        """\
from cyclopts import App
app = App(name="windows")
"""
    )
    windows_path = str(script).replace("/", "\\")
    app, name = load_app_from_script(windows_path)
    assert name == "app"
    assert "windows" in app.name


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_windows_path_with_drive_letter(tmp_path):
    """Test loading script with Windows drive letter."""
    script = tmp_path / "drive_app.py"
    script.write_text(
        """\
from cyclopts import App
app = App(name="drive")
"""
    )
    absolute_path = script.resolve()
    app, name = load_app_from_script(str(absolute_path))
    assert name == "app"
    assert "drive" in app.name


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_windows_mixed_path_separators(tmp_path):
    """Test loading script with mixed forward/backslashes."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    script = subdir / "mixed_app.py"
    script.write_text(
        """\
from cyclopts import App
app = App(name="mixed")
"""
    )
    mixed_path = str(tmp_path).replace("/", "\\") + "/subdir/mixed_app.py"
    app, name = load_app_from_script(mixed_path)
    assert name == "app"
    assert "mixed" in app.name


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-specific test")
def test_posix_path_resolution(tmp_path):
    """Test POSIX path resolution."""
    script = tmp_path / "posix_app.py"
    script.write_text(
        """\
from cyclopts import App
app = App(name="posix")
"""
    )
    app, name = load_app_from_script(script)
    assert name == "app"
    assert "posix" in app.name


def test_path_resolution_with_symlinks(tmp_path):
    """Test loading script through symlink."""
    script = tmp_path / "original.py"
    script.write_text(
        """\
from cyclopts import App
app = App(name="original")
"""
    )
    link = tmp_path / "link.py"
    try:
        link.symlink_to(script)
        app, name = load_app_from_script(link)
        assert name == "app"
        assert "original" in app.name
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform")


def test_relative_path_resolution(tmp_path, monkeypatch):
    """Test loading script with relative path."""
    script = tmp_path / "relative_app.py"
    script.write_text(
        """\
from cyclopts import App
app = App(name="relative")
"""
    )
    monkeypatch.chdir(tmp_path)
    app, name = load_app_from_script("relative_app.py")
    assert name == "app"
    assert "relative" in app.name


def test_path_with_spaces(tmp_path):
    """Test loading script from path with spaces."""
    subdir = tmp_path / "path with spaces"
    subdir.mkdir()
    script = subdir / "spaces app.py"
    script.write_text(
        """\
from cyclopts import App
app = App(name="spaces")
"""
    )
    app, name = load_app_from_script(script)
    assert name == "app"
    assert "spaces" in app.name


@patch.dict("os.environ", {"USERPROFILE": "/fake/windows/home"}, clear=False)
def test_windows_userprofile_in_path(tmp_path):
    """Test that Windows USERPROFILE environment variable doesn't break path resolution."""
    script = tmp_path / "userprofile_app.py"
    script.write_text(
        """\
from cyclopts import App
app = App(name="userprofile")
"""
    )
    app, name = load_app_from_script(script)
    assert name == "app"
    assert "userprofile" in app.name


def test_script_with_syntax_error(tmp_path):
    """Test handling of script with syntax errors."""
    script = tmp_path / "syntax_error.py"
    script.write_text("this is not valid python @@@@")
    with pytest.raises(SyntaxError):
        load_app_from_script(script)


def test_script_with_import_error(tmp_path):
    """Test handling of script with import errors."""
    script = tmp_path / "import_error.py"
    script.write_text(
        """\
from cyclopts import App
import nonexistent_module

app = App()
"""
    )
    with pytest.raises(ModuleNotFoundError):
        load_app_from_script(script)


def test_unicode_in_path(tmp_path):
    """Test loading script from path with Unicode characters."""
    subdir = tmp_path / "ディレクトリ"
    subdir.mkdir()
    script = subdir / "アプリ.py"
    script.write_text(
        """\
from cyclopts import App
app = App(name="unicode")
"""
    )
    app, name = load_app_from_script(script)
    assert name == "app"
    assert "unicode" in app.name
