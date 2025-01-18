import subprocess
from pathlib import Path

import pytest

from cyclopts._edit import (
    EditorDidNotChangeError,
    EditorDidNotSaveError,
    EditorError,
    EditorNotFoundError,
    edit,
)


@pytest.fixture
def mock_editor():
    """Mock editor that simulates saving file with edited content."""

    def fake_editor(args):
        Path(args[1]).write_text("edited content")
        return 0

    return fake_editor


def test_basic_edit(mocker, mock_editor, monkeypatch):
    """Test basic editing functionality."""
    monkeypatch.setenv("EDITOR", "test_editor")
    mocker.patch("shutil.which", return_value=True)
    mocker.patch("subprocess.check_call", side_effect=mock_editor)

    result = edit("initial text")
    assert result == "edited content"


def test_custom_path(mocker, mock_editor, tmp_path, monkeypatch):
    """Test editing with custom path."""
    custom_path = tmp_path / "custom.txt"
    monkeypatch.setenv("EDITOR", "test_editor")
    mocker.patch("shutil.which", return_value=True)
    mocker.patch("subprocess.check_call", side_effect=mock_editor)

    result = edit("initial text", path=custom_path)
    assert result == "edited content"


def test_editor_not_found(mocker, monkeypatch):
    """Test behavior when no editor is found."""
    monkeypatch.delenv("EDITOR", raising=False)
    mocker.patch("shutil.which", return_value=False)

    with pytest.raises(EditorNotFoundError):
        edit("test")


def test_did_not_save(mocker, monkeypatch):
    """Test behavior when user doesn't save."""
    monkeypatch.setenv("EDITOR", "test_editor")

    def fake_editor(_):  # Doesn't "save"
        return 0

    mocker.patch("shutil.which", return_value=True)
    mocker.patch("subprocess.check_call", side_effect=fake_editor)

    with pytest.raises(EditorDidNotSaveError):
        edit("initial text", save=True)


def test_did_not_change(mocker, monkeypatch):
    """Test behavior when content isn't changed."""
    monkeypatch.setenv("EDITOR", "test_editor")
    initial_text = "unchanged text"

    def fake_editor(args):
        assert args[0] == "test_editor"
        Path(args[1]).write_text(initial_text)
        return 0

    mocker.patch("shutil.which", return_value=True)
    mocker.patch("subprocess.check_call", side_effect=fake_editor)

    with pytest.raises(EditorDidNotChangeError):
        edit(initial_text, required=True)


def test_editor_error(mocker, monkeypatch):
    """Test handling of editor errors."""
    monkeypatch.setenv("EDITOR", "test_editor")
    mocker.patch("shutil.which", return_value=True)
    mocker.patch("subprocess.check_call", side_effect=subprocess.CalledProcessError(1, "test_editor"))

    with pytest.raises(EditorError) as exc_info:
        edit("test")
    assert "status 1" in str(exc_info.value)


def test_custom_encoding(mocker, tmp_path, monkeypatch):
    """Test custom encoding support."""
    test_path = tmp_path / "test.txt"
    monkeypatch.setenv("EDITOR", "test_editor")

    def fake_editor_with_encoding(args):
        assert args[0] == "test_editor"
        Path(args[1]).write_text("текст", encoding="utf-16")
        return 0

    mocker.patch("shutil.which", return_value=True)
    mocker.patch("subprocess.check_call", side_effect=fake_editor_with_encoding)

    result = edit("initial", path=test_path, encoding="utf-16")
    assert result == "текст"


def test_fallback_editors(mocker, mock_editor, monkeypatch):
    """Test fallback editor selection."""
    monkeypatch.delenv("EDITOR", raising=False)

    def mock_which(editor_name):
        return editor_name == "vim"

    mocker.patch("shutil.which", side_effect=mock_which)
    mock_check_call = mocker.patch("subprocess.check_call", side_effect=mock_editor)

    result = edit("test", fallback_editors=["emacs", "vim", "nano"])
    assert result == "edited content"
    assert mock_check_call.call_args_list[0].args[0][0] == "vim"


def test_editor_args(mocker, monkeypatch):
    """Test passing additional arguments to editor."""
    monkeypatch.setenv("EDITOR", "test_editor")

    def check_editor_args(args):
        assert args[0] == "test_editor"
        assert "--no-splash" in args
        Path(args[1]).write_text("edited with args")
        return 0

    mocker.patch("shutil.which", return_value=True)
    mocker.patch("subprocess.check_call", side_effect=check_editor_args)

    result = edit("test", editor_args=["--no-splash"])
    assert result == "edited with args"


def test_optional_change(mocker, monkeypatch):
    """Test when content changes are optional."""
    monkeypatch.setenv("EDITOR", "test_editor")
    initial_text = "unchanged"

    def fake_editor(args):
        assert args[0] == "test_editor"
        Path(args[1]).write_text(initial_text)
        return 0

    mocker.patch("shutil.which", return_value=True)
    mocker.patch("subprocess.check_call", side_effect=fake_editor)

    # Should not raise DidNotChangeError
    result = edit(initial_text, required=False)
    assert result == initial_text


def test_file_cleanup(mocker, tmp_path, monkeypatch, mock_editor):
    """Test temporary file cleanup."""
    test_path = tmp_path / "cleanup_test.txt"
    monkeypatch.setenv("EDITOR", "test_editor")

    mocker.patch("shutil.which", return_value=True)
    mocker.patch("subprocess.check_call", side_effect=mock_editor)

    edit("test", path=test_path)
    assert not test_path.exists()
