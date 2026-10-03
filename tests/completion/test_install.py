"""Tests for completion installation functionality."""

import os
import subprocess
import sys
from pathlib import Path
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
    monkeypatch.delenv("ZSH", raising=False)
    return tmp_path


@pytest.fixture
def omz_dir(temp_home, monkeypatch):
    """Create a fake oh-my-zsh installation with $ZSH set."""
    omz = temp_home / ".oh-my-zsh"
    (omz / "custom").mkdir(parents=True)
    monkeypatch.setenv("ZSH", str(omz))
    return omz


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


def test_install_completion_zsh_ohmyzsh_default_path(omz_dir):
    """Test that $ZSH set with valid dir installs to $ZSH/custom/completions/_cyclopts_testapp."""
    app = App(name="testapp")
    install_path = app.install_completion(shell="zsh", add_to_startup=True)

    assert install_path == omz_dir / "custom" / "completions" / "_cyclopts_testapp"
    assert install_path.exists()


def test_install_completion_zsh_ohmyzsh_zsh_custom_env(omz_dir, temp_home, monkeypatch):
    """Test that $ZSH_CUSTOM takes precedence over $ZSH/custom."""
    custom_dir = temp_home / "my-custom-omz"
    custom_dir.mkdir()
    monkeypatch.setenv("ZSH_CUSTOM", str(custom_dir))

    app = App(name="testapp")
    install_path = app.install_completion(shell="zsh", add_to_startup=True)

    assert install_path == custom_dir / "completions" / "_cyclopts_testapp"
    assert install_path.exists()


def test_install_completion_zsh_ohmyzsh_no_zshrc_modification(omz_dir, temp_home):
    """Test that .zshrc is not created/modified when oh-my-zsh detected."""
    zshrc = temp_home / ".zshrc"
    app = App(name="testapp")
    app.install_completion(shell="zsh", add_to_startup=True)

    assert not zshrc.exists()


def test_install_completion_zsh_ohmyzsh_dir_missing(temp_home, monkeypatch):
    """Test that $ZSH pointing to nonexistent dir falls back to vanilla path."""
    monkeypatch.setenv("ZSH", str(temp_home / "nonexistent"))

    app = App(name="testapp")
    install_path = app.install_completion(shell="zsh", add_to_startup=False)

    expected = temp_home / ".zsh" / "completions" / "_cyclopts_testapp"
    assert install_path == expected
    assert install_path.exists()


def test_install_completion_zsh_add_to_startup_prepends(temp_home):
    """Test that for vanilla zsh, fpath line appears before existing .zshrc content."""
    app = App(name="testapp")
    zshrc = temp_home / ".zshrc"

    existing_content = "# Existing config\nautoload -Uz compinit && compinit\n"
    zshrc.write_text(existing_content)

    app.install_completion(shell="zsh", add_to_startup=True)

    zshrc_content = zshrc.read_text()
    fpath_pos = zshrc_content.index("fpath=")
    existing_pos = zshrc_content.index("# Existing config")
    assert fpath_pos < existing_pos, "fpath line should be prepended before existing content"


def test_install_completion_zsh_ohmyzsh_message(omz_dir, monkeypatch, capsys):
    """Test that printed output mentions oh-my-zsh and doesn't mention .zshrc."""
    app = App(name="testapp")
    app.register_install_completion_command(add_to_startup=True)

    monkeypatch.setattr("cyclopts.completion.detect.detect_shell", lambda: "zsh")

    with patch("sys.exit"):
        try:
            app(["--install-completion"], exit_on_error=False)
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "oh-my-zsh" in captured.out
    assert ".zshrc" not in captured.out
    assert "exec zsh" in captured.out


def test_install_completion_bash_add_to_startup_appends(temp_home):
    """Regression test: bash still appends to .bashrc."""
    app = App(name="testapp")
    bashrc = temp_home / ".bashrc"

    existing_content = "# Existing bash config\nexport PATH=/usr/local/bin:$PATH\n"
    bashrc.write_text(existing_content)

    app.install_completion(shell="bash", add_to_startup=True)

    bashrc_content = bashrc.read_text()
    existing_pos = bashrc_content.index("# Existing bash config")
    completion_pos = bashrc_content.index("# Load testapp completion")
    assert existing_pos < completion_pos, "bash completion should be appended after existing content"


@pytest.fixture
def ps_profile(temp_home, monkeypatch):
    """Point PowerShell's profile into the temp home without spawning PowerShell."""
    profile = temp_home / "pwsh-config" / "profile.ps1"
    monkeypatch.setattr("cyclopts.completion.install.powershell_profile", lambda: profile)
    return profile


def test_install_completion_powershell(ps_profile):
    app = App(name="testapp")

    install_path = app.install_completion(shell="powershell")

    assert install_path == ps_profile.parent / "Completions" / "testapp.ps1"
    assert "Register-ArgumentCompleter -Native" in install_path.read_text()
    assert ps_profile.read_text() == (
        f"# Load testapp completion\nif (Test-Path '{install_path}') {{ . '{install_path}' }}\n"
    )


def test_install_completion_powershell_idempotent_and_appends(ps_profile):
    ps_profile.parent.mkdir(parents=True)
    ps_profile.write_text("Set-PSReadLineOption -EditMode Emacs")
    app = App(name="testapp")

    app.install_completion(shell="powershell")
    app.install_completion(shell="powershell")

    content = ps_profile.read_text()
    assert content.startswith("Set-PSReadLineOption -EditMode Emacs\n# Load testapp completion\n")
    assert content.count("# Load testapp completion") == 1


def test_install_completion_powershell_quotes_path(ps_profile):
    app = App(name="testapp")
    output = ps_profile.parent / "it's" / "testapp.ps1"

    app.install_completion(shell="powershell", output=output)

    quoted = "'" + str(output).replace("'", "''") + "'"
    assert f"if (Test-Path {quoted}) {{ . {quoted} }}" in ps_profile.read_text()


def test_install_completion_powershell_add_to_startup_false(ps_profile):
    App(name="testapp").install_completion(shell="powershell", add_to_startup=False)
    assert not ps_profile.exists()


def test_install_completion_command_powershell(ps_profile, monkeypatch, capsys):
    app = App(name="testapp")
    app.register_install_completion_command()
    monkeypatch.setattr("cyclopts.completion.detect.detect_shell", lambda: "powershell")

    with patch("sys.exit"):
        try:
            app(["--install-completion"], exit_on_error=False)
        except SystemExit:
            pass

    out = capsys.readouterr().out
    assert f"Added completion loader to {ps_profile}" in out
    assert f"run: . '{ps_profile}'" in out


def test_powershell_profile_queries_powershell(monkeypatch):
    from unittest.mock import Mock

    from cyclopts.completion import install

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Mock(returncode=0, stdout="/somewhere/profile.ps1\n")

    monkeypatch.setattr(install.subprocess, "run", fake_run)
    assert install.powershell_profile() == Path("/somewhere/profile.ps1")
    assert calls[0][-1] == "$PROFILE.CurrentUserAllHosts"


def test_powershell_profile_fallback(temp_home, monkeypatch):
    from cyclopts.completion import install

    def missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(install.subprocess, "run", missing)
    if sys.platform == "win32":
        expected = Path.home() / "Documents" / "PowerShell" / "profile.ps1"
        monkeypatch.setenv("PSModulePath", str(Path.home() / "Documents" / "PowerShell" / "Modules"))
    else:
        expected = temp_home / ".config" / "powershell" / "profile.ps1"
    assert install.powershell_profile() == expected


@pytest.mark.skipif(sys.platform == "win32", reason="Windows resolves the profile from Documents, not $HOME")
def test_install_completion_powershell_real_profile(temp_home, tmp_path, monkeypatch):
    """Install into a real (temp-$HOME) profile, then complete in a fresh pwsh that loads it."""
    from .conftest import _check_pwsh_available, write_shim

    if not _check_pwsh_available():
        pytest.skip("pwsh not available")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    entry = tmp_path / "entry.py"
    entry.write_text("from cyclopts import App\napp = App(name='testapp')\n@app.command\ndef deploy(): ...\napp()\n")
    write_shim(tmp_path / "bin", "testapp", entry)
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}")

    install_path = App(name="testapp").install_completion(shell="powershell")

    assert install_path == temp_home / ".config" / "powershell" / "Completions" / "testapp.ps1"
    result = subprocess.run(
        [
            "pwsh",
            "-NonInteractive",
            "-Command",
            "(TabExpansion2 -inputScript 'testapp de' -cursorColumn 10).CompletionMatches.CompletionText",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.stdout.split() == ["deploy"]


def test_install_completion_command_non_utf8_stdout(ps_profile, monkeypatch):
    """Redirected stdout on Windows is cp1252, which has no check mark; the messages must still print."""
    import io

    app = App(name="testapp")
    app.register_install_completion_command()
    monkeypatch.setattr("cyclopts.completion.detect.detect_shell", lambda: "powershell")
    stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stdout)

    app(["--install-completion"], exit_on_error=False, result_action="return_value")

    stdout.seek(0)
    assert "Completion script installed" in stdout.read()
