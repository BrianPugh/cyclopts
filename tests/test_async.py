import asyncio
from typing import Annotated

import sniffio

from cyclopts import Parameter


def test_async_handler(app):
    @app.command(name="command")
    async def async_handler():
        assert sniffio.current_async_library() == "asyncio"
        return "Async handler works"

    assert app("command") == "Async handler works"


def test_async_handler_with_subcommand_works(app):
    from cyclopts import App

    sub_app = App(name="foo")
    app.command(sub_app)

    @sub_app.command(name="bar")
    async def async_handler():
        assert sniffio.current_async_library() == "asyncio"
        return "Async handler works"

    assert app("foo bar") == "Async handler works"


def test_handler(app):
    @app.command(name="command")
    def sync_handler():
        return "Sync handler works"

    assert app("command") == "Sync handler works"


def test_async_meta_with_async_command(app):
    results = []

    @app.command
    async def async_command(value: int):
        await asyncio.sleep(0)  # Simulate async work
        result = f"Async command executed with {value}"
        results.append(result)
        return result

    @app.meta.default
    async def launcher(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
        await asyncio.sleep(0)  # Simulate async initialization
        results.append("Meta initialized")
        result = await app.run_async(tokens)  # Use run_async when inside an async context
        results.append("Meta finished")
        return result

    result = app.meta(["async-command", "42"])
    assert result == "Async command executed with 42"
    assert results == ["Meta initialized", "Async command executed with 42", "Meta finished"]


def test_async_meta_with_sync_command(app):
    results = []

    @app.command
    def sync_command(value: int):
        result = f"Sync command executed with {value}"
        results.append(result)
        return result

    @app.meta.default
    async def launcher(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
        await asyncio.sleep(0)  # Simulate async initialization
        results.append("Meta initialized")
        # Synchronous commands should also work from async meta
        result = await app.run_async(tokens)  # Use run_async when inside an async context
        results.append("Meta finished")
        return result

    result = app.meta(["sync-command", "42"])
    assert result == "Sync command executed with 42"
    assert results == ["Meta initialized", "Sync command executed with 42", "Meta finished"]


def test_async_meta_with_nested_async(app):
    results = []

    @app.default
    async def default_handler():
        await asyncio.sleep(0)
        results.append("Default handler")
        return "Default result"

    @app.meta.default
    async def meta(*tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]):
        await asyncio.sleep(0)
        results.append("Meta handler")
        result = await app.run_async(tokens)  # Use run_async when inside an async context
        results.append("Meta complete")
        return result

    result = app.meta([])
    assert result == "Default result"
    assert results == ["Meta handler", "Default handler", "Meta complete"]
