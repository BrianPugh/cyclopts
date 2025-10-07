"""Tests for completion installation functionality."""

from unittest.mock import patch

import pytest

from cyclopts import App


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Create a temporary home directory for testing."""
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
    """Test that add_to_startup=True adds source line to zshrc."""
    app = App(name="testapp")
    zshrc = temp_home / ".zshrc"

    install_path = app.install_completion(shell="zsh", add_to_startup=True)

    assert install_path.exists()
    assert zshrc.exists()

    zshrc_content = zshrc.read_text()
    assert "# Load testapp completion" in zshrc_content
    assert f'[ -f "{install_path}" ] && . "{install_path}"' in zshrc_content


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
    assert first_content.count("# Load testapp completion") == 1


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


def test_register_install_completion_default_add_to_startup(temp_home):
    """Test that register_install_completion defaults to add_to_startup=True."""
    app = App(name="testapp")
    app.register_install_completion()

    bashrc = temp_home / ".bashrc"

    with patch("sys.exit"):
        try:
            app(["--install-completion", "--shell", "bash"], exit_on_error=False)
        except SystemExit:
            pass

    assert bashrc.exists()
    bashrc_content = bashrc.read_text()
    assert "# Load testapp completion" in bashrc_content


def test_register_install_completion_add_to_startup_false(temp_home):
    """Test that register_install_completion respects add_to_startup=False."""
    app = App(name="testapp")
    app.register_install_completion(add_to_startup=False)

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
