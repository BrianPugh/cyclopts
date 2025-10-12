import asyncio
from pathlib import Path


def test_version_print_console_from_init(app, console):
    app.console = console

    with console.capture() as capture:
        app.version_print()

    assert "0.0.0\n" == capture.get()


def test_version_print_console_from_method(app, console):
    with console.capture() as capture:
        app.version_print(console)

    assert "0.0.0\n" == capture.get()


def test_version_print_console_none(app, console):
    app.version = None
    with console.capture() as capture:
        app.version_print(console)

    assert "0.0.0\n" == capture.get()


def test_version_print_custom_string(app, console):
    """The asterisks also test to make sure the proper help_format is being used."""
    app.version = "**foo**"

    with console.capture() as capture:
        app.version_print(console)

    assert "foo\n" == capture.get()


def test_version_print_custom_callable(app, console):
    def my_version():
        return "**foo**"

    app.version = my_version

    with console.capture() as capture:
        app.version_print(console)

    assert "foo\n" == capture.get()


def test_version_print_help_format_fallback(app, console):
    """If no explicit version_format is provided, we should fallback to help_format."""
    app.help_format = "rich"
    app.version = "[red]foo[/red]"

    with console.capture() as capture:
        app.version_print(console)

    assert "foo\n" == capture.get()


def test_version_print_help_format_override(app, console):
    """If version_format is provided, help_format should not be used for version."""
    app.help_format = "plain"
    app.version_format = "rich"
    app.version = "[red]foo[/red]"

    with console.capture() as capture:
        app.version_print(console)

    assert "foo\n" == capture.get()


def test_version_print_custom_async_callable(app, console):
    """Test that async callables work for version via command-line."""

    async def my_async_version():
        return "**async-foo**"

    app.version = my_async_version

    # Test via command-line invocation (uses _run_maybe_async_command)
    with console.capture() as capture:
        app(["--version"], console=console)

    assert "async-foo\n" == capture.get()


def test_version_print_async_in_async_context(app, console):
    """Test that async version callables work when called from within an async context."""

    async def my_async_version():
        # Verify we're in an async context
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return "ERROR: Not in async context"
        return "**async-version-from-async-context**"

    app.version = my_async_version

    async def run_test():
        with console.capture() as capture:
            # This should use _version_print_async and not create a new event loop
            await app.run_async(["--version"], console=console)
        return capture.get()

    result = asyncio.run(run_test())
    assert "async-version-from-async-context\n" == result


def test_version_print_sync_callable_end_to_end(app, console):
    """Test that vanilla sync version callables works end-to-end."""

    def my_sync_version():
        return "**sync-foo**"

    app.version = my_sync_version

    with console.capture() as capture:
        app(["--version"], console=console)

    assert "sync-foo\n" == capture.get()


def test_help_and_version_flags_together(app, console):
    """Test that help flag takes priority when both --help and --version are provided.

    Regression test for bug where having both flags caused NameError on Console forward reference.
    """

    @app.command
    def files(
        input_file: Path,
        output_file: Path | None = None,
    ):
        """Work with files."""
        pass

    with console.capture() as capture:
        app(["files", "-h", "--version"], console=console)

    output = capture.get()
    assert "Work with files" in output
    assert "INPUT-FILE" in output
