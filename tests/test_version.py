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


def test_subcommand_version(console):
    """Test that subcommands display their own version, not the parent's version.

    Regression test for issue #627 where subcommand --version showed parent version.
    """
    from cyclopts import App

    # Root app with no version (defaults to 0.0.0)
    root_app = App(version_flags=[], result_action="return_value")

    # Subcommand with explicit version
    subcommand = App(
        name="subcommand",
        version="1.2.3",
        version_flags=["--version"],
    )
    root_app.command(subcommand)

    @subcommand.default
    def subcommand_default():
        """Subcommand default function."""
        return "executed"

    # Test that subcommand --version shows subcommand's version, not root's
    with console.capture() as capture:
        root_app(["subcommand", "--version"], console=console)

    assert "1.2.3\n" == capture.get()


def test_subcommand_version_with_meta_app(console):
    """Test that subcommand version works correctly with meta apps.

    Regression test for issue #627 with meta app wrapper.
    """
    from typing import Annotated

    from cyclopts import App, Parameter

    # Root app with no version
    root_app = App(version_flags=[], result_action="return_value")

    # Subcommand with explicit version
    subcommand = App(
        name="subcommand",
        version="1.2.3",
        version_flags=["-v", "--version"],
    )
    root_app.command(subcommand)

    @subcommand.default
    def subcommand_default():
        """Subcommand default function."""
        return "executed"

    @root_app.meta.default
    def meta(
        *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
        verbose: Annotated[bool, Parameter(alias="-V")] = False,
    ):
        return root_app(tokens)

    # Test that subcommand --version shows subcommand's version even with meta app
    with console.capture() as capture:
        root_app.meta(["subcommand", "--version"], console=console)

    assert "1.2.3\n" == capture.get()

    # Also test with meta flag present
    with console.capture() as capture:
        root_app.meta(["-V", "subcommand", "-v"], console=console)

    assert "1.2.3\n" == capture.get()


def test_subcommand_inherits_parent_version(console):
    """Test that subcommand inherits parent's version when not explicitly set.

    When a subcommand doesn't have an explicit version, it should inherit
    the parent's version if the parent has one set.
    """
    from cyclopts import App

    # Root app with explicit version
    root_app = App(version="2.0.0", result_action="return_value")

    # Subcommand without explicit version - should inherit from parent
    subcommand = App(name="subcommand")
    root_app.command(subcommand)

    @subcommand.default
    def subcommand_default():
        """Subcommand default function."""
        return "executed"

    # Test that subcommand --version shows parent's version
    with console.capture() as capture:
        root_app(["subcommand", "--version"], console=console)

    assert "2.0.0\n" == capture.get()


def test_subcommand_explicit_version_overrides_parent(console):
    """Test that subcommand's explicit version overrides parent's version."""
    from cyclopts import App

    # Root app with version 2.0.0
    root_app = App(version="2.0.0", result_action="return_value")

    # Subcommand with explicit different version - should NOT inherit
    subcommand = App(name="subcommand", version="3.0.0")
    root_app.command(subcommand)

    @subcommand.default
    def subcommand_default():
        """Subcommand default function."""
        return "executed"

    # Test that subcommand --version shows its own version, not parent's
    with console.capture() as capture:
        root_app(["subcommand", "--version"], console=console)

    assert "3.0.0\n" == capture.get()


def test_function_command_inherits_parent_version(console):
    """Test that function commands inherit parent's version."""
    from cyclopts import App

    root_app = App(version="4.0.0", result_action="return_value")

    @root_app.command
    def my_command():
        """A command function."""
        return "executed"

    # Test that function command --version shows parent's version
    with console.capture() as capture:
        root_app(["my-command", "--version"], console=console)

    assert "4.0.0\n" == capture.get()
