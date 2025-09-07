import sniffio

from cyclopts import App


def test_async_handler():
    app = App()

    @app.command(name="command")
    async def async_handler():
        assert sniffio.current_async_library() == "asyncio"
        return "Async handler works"

    assert app("command") == "Async handler works"


def test_async_handler_with_subcommand_works():
    app = App()

    sub_app = App(name="foo")
    app.command(sub_app)

    @sub_app.command(name="bar")
    async def async_handler():
        assert sniffio.current_async_library() == "asyncio"
        return "Async handler works"

    assert app("foo bar") == "Async handler works"


def test_handler():
    app = App()

    @app.command(name="command")
    def sync_handler():
        return "Sync handler works"

    assert app("command") == "Sync handler works"
