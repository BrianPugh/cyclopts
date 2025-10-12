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
