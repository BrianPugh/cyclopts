from contextlib import suppress

import pytest

from cyclopts import App, CycloptsError
from cyclopts.exceptions import UnusedCliTokensError


def _create_mock_console(mocker):
    from rich.console import ConsoleDimensions, ConsoleOptions

    console = mocker.MagicMock()
    console.width = 80
    console.height = 24
    console.legacy_windows = False
    console.is_terminal = True
    console.encoding = "utf-8"

    # Add a proper options attribute that matches what Rich provides
    console.options = ConsoleOptions(
        size=ConsoleDimensions(console.width, console.height),
        legacy_windows=console.legacy_windows,
        min_width=1,
        max_width=console.width,
        is_terminal=console.is_terminal,
        encoding=console.encoding,
        max_height=console.height,
    )

    return console


@pytest.fixture
def mock_console(mocker):
    """Create a mock console with required attributes for Rich compatibility."""
    return _create_mock_console(mocker)


@pytest.fixture
def subapp(app):
    app.command(subapp := App(name="foo"))
    return subapp


@pytest.mark.parametrize("cmd", ["foo --help"])
def test_root_console(app, mock_console, cmd):
    app.console = mock_console

    with suppress(CycloptsError):
        app(cmd, exit_on_error=False)

    app.console.print.assert_called()


@pytest.mark.parametrize("cmd", ["foo --help"])
def test_root_console_subapp(app, subapp, mock_console, cmd):
    """Check if root console is properly resolved (subapp.console not specified)."""
    app.console = mock_console

    with suppress(CycloptsError):
        app(cmd, exit_on_error=False)

    app.console.print.assert_called()


@pytest.mark.parametrize("cmd", ["foo --help"])
def test_root_subapp_console(app, subapp, mock_console, mocker, cmd):
    """Check if subapp console is properly resolved (NOT app.console)."""
    app.console = mock_console
    subapp.console = _create_mock_console(mocker)

    with suppress(CycloptsError):
        app(cmd, exit_on_error=False)

    app.console.print.assert_not_called()
    subapp.console.print.assert_called()


@pytest.mark.parametrize("cmd", ["foo --help"])
def test_root_subapp_arg_console(app, subapp, mock_console, mocker, cmd):
    """Explicitly provided console should be used."""
    console = mock_console
    app.console = mocker.MagicMock()
    subapp.console = mocker.MagicMock()

    with suppress(CycloptsError):
        app(cmd, console=console, exit_on_error=False)

    console.print.assert_called()
    app.console.print.assert_not_called()
    subapp.console.print.assert_not_called()


def test_console_populated_issue_103(app):
    """Ensures console is populated for an UnusedCliTokensError.

    https://github.com/BrianPugh/cyclopts/issues/103
    """

    @app.command
    def foo():
        pass

    with pytest.raises(UnusedCliTokensError):
        app("foo bar", exit_on_error=False)


@pytest.mark.parametrize("cmd", ["foo invalid-command"])
def test_root_error_console(app, mock_console, mocker, cmd):
    """Test that root error_console is used for errors."""
    error_console = _create_mock_console(mocker)
    app.error_console = error_console

    with suppress(CycloptsError):
        app(cmd, exit_on_error=False)

    error_console.print.assert_called()


@pytest.mark.parametrize("cmd", ["foo invalid-command"])
def test_root_error_console_subapp(app, subapp, mocker, cmd):
    """Check if root error_console is properly resolved (subapp.error_console not specified)."""
    error_console = _create_mock_console(mocker)
    app.error_console = error_console

    with suppress(CycloptsError):
        app(cmd, exit_on_error=False)

    error_console.print.assert_called()


@pytest.mark.parametrize("cmd", ["foo invalid-command"])
def test_root_subapp_error_console(app, subapp, mocker, cmd):
    """Check if subapp error_console is properly resolved (NOT app.error_console)."""
    app.error_console = _create_mock_console(mocker)
    subapp.error_console = _create_mock_console(mocker)

    with suppress(CycloptsError):
        app(cmd, exit_on_error=False)

    app.error_console.print.assert_not_called()
    subapp.error_console.print.assert_called()


@pytest.mark.parametrize("cmd", ["foo invalid-command"])
def test_root_subapp_arg_error_console(app, subapp, mocker, cmd):
    """Explicitly provided error_console should be used."""
    error_console = _create_mock_console(mocker)
    app.error_console = mocker.MagicMock()
    subapp.error_console = mocker.MagicMock()

    with suppress(CycloptsError):
        app(cmd, error_console=error_console, exit_on_error=False)

    error_console.print.assert_called()
    app.error_console.print.assert_not_called()
    subapp.error_console.print.assert_not_called()
