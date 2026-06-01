import sniffio
import trio

from cyclopts import App


def test_async_handler(app):
    @app.command(name="command")
    async def async_handler():
        assert sniffio.current_async_library() == "trio"
        await trio.lowlevel.checkpoint()  # Ensure trio is functioning
        return "Async handler works"

    assert app("command", backend="trio") == "Async handler works"


def test_async_handler_with_subcommand_works(app):
    sub_app = App(name="foo")
    app.command(sub_app)

    @sub_app.command(name="bar")
    async def async_handler():
        assert sniffio.current_async_library() == "trio"
        await trio.lowlevel.checkpoint()  # Ensure trio is functioning
        return "Async handler works"

    assert app("foo bar", backend="trio") == "Async handler works"


def test_handler(app):
    @app.command(name="command")
    def sync_handler():
        return "Sync handler works"

    assert app("command") == "Sync handler works"


def test_interactive_shell_async_command(mocker, console):
    """Async commands should be run with the trio backend in the interactive shell.

    See https://github.com/BrianPugh/cyclopts/issues/826
    """
    app = App(backend="trio")

    mocker.patch(
        "cyclopts.core.input",
        side_effect=[
            "start",
            "quit",
        ],
    )

    start_called = 0

    @app.command
    async def start():
        nonlocal start_called
        assert sniffio.current_async_library() == "trio"
        await trio.lowlevel.checkpoint()  # Ensure trio is functioning
        start_called += 1
        return "Started!"

    with console.capture() as capture:
        app.interactive_shell(console=console)

    actual = capture.get()

    assert start_called == 1
    assert "Started!" in actual
    assert "coroutine object" not in actual
