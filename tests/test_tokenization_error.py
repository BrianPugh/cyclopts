import asyncio

import pytest

from cyclopts import App, CycloptsError, TokenizationError


@pytest.fixture
def foo_app(console):
    app = App(error_console=console)

    @app.command
    def foo(a: int):
        return a

    return app


def test_parse_args_prints_and_raises(foo_app, console):
    with console.capture() as capture, pytest.raises(TokenizationError):
        foo_app.parse_args('foo "1', exit_on_error=False)

    assert capture.get() == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        "│ No closing quotation: 'foo \"1'                                     │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_call_exits(foo_app, console):
    with console.capture(), pytest.raises(SystemExit) as e:
        foo_app('foo "1')
    assert e.value.code == 1


def test_call_uses_error_formatter(console):
    seen = []

    def formatter(e: CycloptsError):
        seen.append(e)
        return "formatted"

    app = App(error_console=console, error_formatter=formatter, exit_on_error=False)

    with console.capture() as capture, pytest.raises(TokenizationError):
        app('foo "1')

    assert isinstance(seen[0], TokenizationError)
    assert capture.get() == "formatted\n"


def test_run_async_raises(foo_app, console):
    with console.capture(), pytest.raises(TokenizationError):
        asyncio.run(foo_app.run_async('foo "1', exit_on_error=False))


def test_interactive_shell_respects_exit_on_error(foo_app, mocker, console):
    mocker.patch("cyclopts.core.input", side_effect=['foo "1', "quit"])
    with console.capture(), pytest.raises(SystemExit):
        foo_app.interactive_shell(exit_on_error=True)
