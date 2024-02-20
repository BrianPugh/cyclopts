from contextlib import suppress

import pytest

from cyclopts import App, CycloptsError
from cyclopts.exceptions import UnusedCliTokensError


@pytest.fixture
def subapp(app):
    app.command(subapp := App(name="foo"))
    return subapp


@pytest.mark.parametrize("cmd", ["foo --help", "foo invalid-command"])
def test_root_console(app, mocker, cmd):
    app.console = mocker.MagicMock()

    with suppress(CycloptsError):
        app(cmd, exit_on_error=False)

    app.console.print.assert_called()


@pytest.mark.parametrize("cmd", ["foo --help", "foo invalid-command"])
def test_root_console_subapp(app, subapp, mocker, cmd):
    """Check if root console is properly resolved (subapp.console not specified)."""
    app.console = mocker.MagicMock()

    with suppress(CycloptsError):
        app(cmd, exit_on_error=False)

    app.console.print.assert_called()


@pytest.mark.parametrize("cmd", ["foo --help", "foo invalid-command"])
def test_root_subapp_console(app, subapp, mocker, cmd):
    """Check if subapp console is properly resolved (NOT app.console)."""
    app.console = mocker.MagicMock()
    subapp.console = mocker.MagicMock()

    with suppress(CycloptsError):
        app(cmd, exit_on_error=False)

    app.console.print.assert_not_called()
    subapp.console.print.assert_called()


@pytest.mark.parametrize("cmd", ["foo --help", "foo invalid-command"])
def test_root_subapp_arg_console(app, subapp, mocker, cmd):
    """Explicitly provided console should be used."""
    console = mocker.MagicMock()
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
