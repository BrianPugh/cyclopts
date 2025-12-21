"""Tests for completion installation functionality."""

import sys
from unittest.mock import patch

import pytest

from cyclopts import App


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Create a temporary home directory for testing."""
    if sys.platform == "win32":
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
    else:
        monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def test_install_completion_bash_add_to_startup_true(temp_home):
    """Test that add_to_startup=True adds source line to bashrc."""
    app = App(name="testapp")
    bashrc = temp_home / ".bashrc"

    install_path = app.install_completion(shell="bash", add_to_startup=True)

    assert install_path.exists()
    assert bashrc.exists()

    bashrc_content = bashrc.read_text()
    assert "# Load testapp completion" in bashrc_content
    assert f'[ -f "{install_path}" ] && . "{install_path}"' in bashrc_content


def test_install_completion_bash_add_to_startup_false(temp_home):
    """Test that add_to_startup=False does not modify bashrc."""
    app = App(name="testapp")
    bashrc = temp_home / ".bashrc"

    install_path = app.install_completion(shell="bash", add_to_startup=False)

    assert install_path.exists()
    assert not bashrc.exists()


def test_install_completion_bash_add_to_startup_idempotent(temp_home):
    """Test that running install_completion multiple times doesn't duplicate bashrc entries."""
    app = App(name="testapp")
    bashrc = temp_home / ".bashrc"

    app.install_completion(shell="bash", add_to_startup=True)
    first_content = bashrc.read_text()

    app.install_completion(shell="bash", add_to_startup=True)
    second_content = bashrc.read_text()

    assert first_content == second_content
    assert first_content.count("# Load testapp completion") == 1


def test_install_completion_bash_add_to_startup_preserves_existing(temp_home):
    """Test that add_to_startup=True preserves existing bashrc content."""
    app = App(name="testapp")
    bashrc = temp_home / ".bashrc"

    existing_content = "# Existing config\nexport PATH=/usr/local/bin:$PATH\n"
    bashrc.write_text(existing_content)

    app.install_completion(shell="bash", add_to_startup=True)

    bashrc_content = bashrc.read_text()
    assert existing_content in bashrc_content
    assert "# Load testapp completion" in bashrc_content


def test_install_completion_zsh_add_to_startup_true(temp_home):
    """Test that add_to_startup=True adds fpath line to zshrc."""
    app = App(name="testapp")
    zshrc = temp_home / ".zshrc"

    install_path = app.install_completion(shell="zsh", add_to_startup=True)

    assert install_path.exists()
    assert zshrc.exists()

    zshrc_content = zshrc.read_text()
    completion_dir = install_path.parent
    assert "# testapp completions" in zshrc_content
    assert f"fpath=({completion_dir} $fpath)" in zshrc_content


def test_install_completion_zsh_add_to_startup_false(temp_home):
    """Test that add_to_startup=False does not modify zshrc."""
    app = App(name="testapp")
    zshrc = temp_home / ".zshrc"

    install_path = app.install_completion(shell="zsh", add_to_startup=False)

    assert install_path.exists()
    assert not zshrc.exists()


def test_install_completion_zsh_add_to_startup_idempotent(temp_home):
    """Test that running install_completion multiple times doesn't duplicate zshrc entries."""
    app = App(name="testapp")
    zshrc = temp_home / ".zshrc"

    app.install_completion(shell="zsh", add_to_startup=True)
    first_content = zshrc.read_text()

    app.install_completion(shell="zsh", add_to_startup=True)
    second_content = zshrc.read_text()

    assert first_content == second_content
    assert first_content.count("# testapp completions") == 1


def test_install_completion_custom_output_path(temp_home):
    """Test that custom output path works with add_to_startup."""
    app = App(name="testapp")
    custom_path = temp_home / "custom" / "completion.sh"
    bashrc = temp_home / ".bashrc"

    install_path = app.install_completion(shell="bash", output=custom_path, add_to_startup=True)

    assert install_path == custom_path
    assert install_path.exists()
    assert bashrc.exists()

    bashrc_content = bashrc.read_text()
    assert str(custom_path) in bashrc_content


def test_register_install_completion_command_default_add_to_startup(temp_home):
    """Test that register_install_completion_command defaults to add_to_startup=True."""
    app = App(name="testapp")
    app.register_install_completion_command()

    bashrc = temp_home / ".bashrc"

    with patch("sys.exit"):
        try:
            app(["--install-completion", "--shell", "bash"], exit_on_error=False)
        except SystemExit:
            pass

    assert bashrc.exists()
    bashrc_content = bashrc.read_text()
    assert "# Load testapp completion" in bashrc_content


def test_register_install_completion_command_add_to_startup_false(temp_home):
    """Test that register_install_completion_command respects add_to_startup=False."""
    app = App(name="testapp")
    app.register_install_completion_command(add_to_startup=False)

    bashrc = temp_home / ".bashrc"

    with patch("sys.exit"):
        try:
            app(["--install-completion", "--shell", "bash"], exit_on_error=False)
        except SystemExit:
            pass

    assert not bashrc.exists()


def test_install_completion_path_with_spaces(temp_home):
    """Test that paths with spaces are properly quoted in RC file."""
    app = App(name="testapp")
    custom_path = temp_home / "my scripts" / "completion.sh"
    bashrc = temp_home / ".bashrc"

    install_path = app.install_completion(shell="bash", output=custom_path, add_to_startup=True)

    assert install_path.exists()
    assert bashrc.exists()

    bashrc_content = bashrc.read_text()
    assert f'[ -f "{custom_path}" ] && . "{custom_path}"' in bashrc_content


def test_register_install_completion_command_custom_help():
    """Test that register_install_completion_command respects custom help parameter."""
    app = App(name="testapp")
    custom_help = "My custom installation help text."
    app.register_install_completion_command(help=custom_help)

    # Get the registered command
    install_cmd_app = app["--install-completion"]

    assert install_cmd_app.help == custom_help


def test_install_completion_fish(temp_home):
    """Test that fish completion installs correctly."""
    app = App(name="testapp")

    install_path = app.install_completion(shell="fish", add_to_startup=False)

    assert install_path.exists()
    assert install_path.name == "testapp.fish"
    assert install_path.parent == temp_home / ".config" / "fish" / "completions"


def test_install_completion_command_shell_detection_error(temp_home, monkeypatch, capsys):
    """Test that install-completion command handles shell detection errors."""
    from cyclopts.completion.detect import ShellDetectionError

    app = App(name="testapp")
    app.register_install_completion_command()

    def mock_detect_shell():
        raise ShellDetectionError("Cannot detect shell")

    monkeypatch.setattr("cyclopts.completion.detect.detect_shell", mock_detect_shell)

    with pytest.raises(SystemExit) as exc_info:
        app(["--install-completion"], exit_on_error=False)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Could not auto-detect shell" in captured.err
    assert "Please specify --shell explicitly" in captured.err


def test_install_completion_command_zsh_with_add_to_startup(temp_home, monkeypatch, capsys):
    """Test that install-completion command prints zsh instructions with add_to_startup."""
    app = App(name="testapp")
    app.register_install_completion_command(add_to_startup=True)

    monkeypatch.setattr("cyclopts.completion.detect.detect_shell", lambda: "zsh")

    with patch("sys.exit"):
        try:
            app(["--install-completion"], exit_on_error=False)
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "Completion script installed" in captured.out
    assert "fpath" in captured.out
    assert ".zshrc" in captured.out
    assert "exec zsh" in captured.out


def test_install_completion_command_zsh_without_add_to_startup(temp_home, monkeypatch, capsys):
    """Test that install-completion command prints zsh instructions without add_to_startup."""
    app = App(name="testapp")
    app.register_install_completion_command(add_to_startup=False)

    monkeypatch.setattr("cyclopts.completion.detect.detect_shell", lambda: "zsh")

    with patch("sys.exit"):
        try:
            app(["--install-completion"], exit_on_error=False)
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "Completion script installed" in captured.out
    assert "ensure" in captured.out.lower() and "$fpath" in captured.out
    assert "fpath=" in captured.out
    assert "autoload -Uz compinit" in captured.out
    assert "exec zsh" in captured.out


def test_install_completion_command_bash_with_add_to_startup(temp_home, monkeypatch, capsys):
    """Test that install-completion command prints bash instructions with add_to_startup."""
    app = App(name="testapp")
    app.register_install_completion_command(add_to_startup=True)

    monkeypatch.setattr("cyclopts.completion.detect.detect_shell", lambda: "bash")

    with patch("sys.exit"):
        try:
            app(["--install-completion"], exit_on_error=False)
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "Completion script installed" in captured.out
    assert "Added completion loader to" in captured.out
    assert ".bashrc" in captured.out
    assert "source ~/.bashrc" in captured.out


def test_install_completion_command_bash_without_add_to_startup(temp_home, monkeypatch, capsys):
    """Test that install-completion command prints bash instructions without add_to_startup."""
    app = App(name="testapp")
    app.register_install_completion_command(add_to_startup=False)

    monkeypatch.setattr("cyclopts.completion.detect.detect_shell", lambda: "bash")

    with patch("sys.exit"):
        try:
            app(["--install-completion"], exit_on_error=False)
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "Completion script installed" in captured.out
    assert "automatically loaded by bash-completion" in captured.out
    assert "bash-completion is installed" in captured.out
    assert "exec bash" in captured.out


def test_install_completion_command_fish(temp_home, monkeypatch, capsys):
    """Test that install-completion command prints fish instructions."""
    app = App(name="testapp")
    app.register_install_completion_command()

    monkeypatch.setattr("cyclopts.completion.detect.detect_shell", lambda: "fish")

    with patch("sys.exit"):
        try:
            app(["--install-completion"], exit_on_error=False)
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "Completion script installed" in captured.out
    assert "automatically loaded in fish" in captured.out
    assert "source ~/.config/fish/config.fish" in captured.out
