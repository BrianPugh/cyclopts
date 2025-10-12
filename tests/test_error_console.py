"""Tests for error_console functionality."""

import sys
from io import StringIO

import pytest

from cyclopts import App
from cyclopts.exceptions import UnknownOptionError


def test_error_goes_to_stderr(capfd):
    """Test that error messages go to stderr."""
    app = App()

    @app.default
    def main(name: str = "World"):
        print(f"Hello, {name}!")

    with pytest.raises(SystemExit):
        app("--invalid-option", exit_on_error=True, print_error=True)

    captured = capfd.readouterr()
    assert captured.err != ""  # Error message should be on stderr
    assert "Unknown option" in captured.err or "invalid-option" in captured.err
    assert captured.out == ""  # Nothing on stdout


def test_help_goes_to_stdout(capfd):
    """Test that help messages go to stdout."""
    app = App()

    @app.default
    def main(name: str = "World"):
        print(f"Hello, {name}!")

    with pytest.raises(SystemExit):
        app("--help")

    captured = capfd.readouterr()
    assert captured.out != ""  # Help should be on stdout
    assert captured.err == ""  # Nothing on stderr


def test_version_goes_to_stdout(capfd):
    """Test that version messages go to stdout."""
    app = App(version="1.2.3")

    @app.default
    def main(name: str = "World"):
        print(f"Hello, {name}!")

    with pytest.raises(SystemExit):
        app("--version")

    captured = capfd.readouterr()
    assert "1.2.3" in captured.out  # Version should be on stdout
    assert captured.err == ""  # Nothing on stderr


def test_custom_error_console():
    """Test that custom error_console can be provided."""
    from rich.console import Console

    error_output = StringIO()
    error_console = Console(file=error_output, force_terminal=False)

    app = App(error_console=error_console)

    @app.default
    def main(name: str):
        pass

    with pytest.raises(UnknownOptionError):
        app("--invalid", exit_on_error=False, print_error=True)

    error_text = error_output.getvalue()
    assert "Unknown option" in error_text or "invalid" in error_text


def test_error_console_resolution_through_app_stack(mocker):
    """Test that error_console is properly resolved through app_stack."""
    from rich.console import Console

    # Create separate consoles for testing
    normal_console = mocker.MagicMock(spec=Console)
    error_console_mock = mocker.MagicMock(spec=Console)

    app = App(console=normal_console, error_console=error_console_mock)

    @app.default
    def main(name: str):
        pass

    try:
        app("--invalid", exit_on_error=False, print_error=True)
    except UnknownOptionError:
        pass

    # Verify error_console was used for error printing
    error_console_mock.print.assert_called()
    # Normal console should not be called for errors
    normal_console.print.assert_not_called()


def test_subapp_error_console_inheritance(mocker):
    """Test that subapp inherits error_console from parent."""
    from rich.console import Console

    error_console_mock = mocker.MagicMock(spec=Console)

    app = App(error_console=error_console_mock)
    subapp = App(name="sub")
    app.command(subapp)

    @subapp.default
    def sub_cmd(value: int):
        pass

    try:
        app("sub --invalid", exit_on_error=False, print_error=True)
    except UnknownOptionError:
        pass

    # Error console should be used
    error_console_mock.print.assert_called()


def test_explicit_error_console_parameter_overrides(mocker):
    """Test that explicit error_console parameter overrides default."""
    from rich.console import Console

    # Default error console (should not be used)
    default_error_console = mocker.MagicMock(spec=Console)

    # Override error console (should be used)
    override_error_console = mocker.MagicMock(spec=Console)

    app = App(error_console=default_error_console)

    @app.default
    def main(name: str):
        pass

    try:
        app("--invalid", error_console=override_error_console, exit_on_error=False, print_error=True)
    except UnknownOptionError:
        pass

    # Override console should be used
    override_error_console.print.assert_called()
    # Default should not be used
    default_error_console.print.assert_not_called()


def test_error_console_with_parse_args(mocker):
    """Test error_console works with parse_args method."""
    from rich.console import Console

    error_console_mock = mocker.MagicMock(spec=Console)

    app = App(error_console=error_console_mock)

    @app.default
    def main(name: str):
        pass

    with pytest.raises(UnknownOptionError):
        app.parse_args("--invalid", exit_on_error=False, print_error=True)

    # Error should use error_console
    error_console_mock.print.assert_called()


def test_unused_tokens_error_to_stderr(capfd):
    """Test that UnusedCliTokensError goes to stderr."""
    app = App()

    @app.command
    def foo():
        pass

    with pytest.raises(SystemExit):
        app("foo bar", exit_on_error=True, print_error=True)

    captured = capfd.readouterr()
    assert captured.err != ""  # Error should be on stderr
    assert "Unused" in captured.err or "bar" in captured.err
    assert captured.out == ""  # Nothing on stdout


def test_normal_output_to_stdout(capfd):
    """Test that normal command output goes to stdout."""
    app = App()

    @app.default
    def main(name: str = "World"):
        return f"Hello, {name}!"

    app([], result_action="return_none")

    captured = capfd.readouterr()
    # The command runs successfully, no errors
    assert captured.err == ""


def test_error_console_default_is_stderr():
    """Test that default error_console writes to stderr."""
    app = App()

    # Access error_console to trigger its creation
    error_console = app.error_console

    # Verify it's configured for stderr
    assert error_console.file == sys.stderr


def test_console_default_is_stdout():
    """Test that default console writes to stdout."""
    app = App()

    # Access console to trigger its creation
    console = app.console

    # Verify it's configured for stdout (default)
    assert console.file == sys.stdout
