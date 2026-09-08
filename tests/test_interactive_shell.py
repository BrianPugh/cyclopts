import sys
import textwrap
from pathlib import Path

import pytest

from cyclopts import App
from cyclopts.core import DEFAULT_SHELL_INTRO


@pytest.fixture
def readline(mocker):
    """Stand-in for ``readline``, which does not exist on Windows."""
    mock = mocker.MagicMock()
    mocker.patch.dict(sys.modules, {"readline": mock})
    return mock


def test_interactive_shell(app, mocker, console):
    mocker.patch(
        "builtins.input",
        side_effect=[
            "foo 1 2 3",
            "bad-command 123",
            "",
            "bar bloop",
            "quit",
        ],
    )

    foo_called, bar_called = 0, 0

    @app.command
    def foo(a: int, b: int, c: int):
        nonlocal foo_called
        foo_called += 1

    @app.command
    def bar(token):
        nonlocal bar_called
        bar_called += 1

    with console.capture() as capture:
        app.interactive_shell(error_console=console)

    actual = capture.get()

    assert foo_called == 1
    assert bar_called == 1

    assert actual == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        '│ Unknown command "bad-command". Available commands: foo, bar.       │\n'
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_interactive_shell_result_action_default_string(mocker, console):
    """Test that string returns are printed in interactive shell (default behavior)."""
    app = App()

    mocker.patch(
        "builtins.input",
        side_effect=[
            "greet Alice",
            "quit",
        ],
    )

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    with console.capture() as capture:
        app.interactive_shell(console=console)

    actual = capture.get()
    assert "Hello Alice!" in actual


def test_interactive_shell_result_action_default_int(app, mocker, console):
    """Test that int returns are not printed in interactive shell (default behavior)."""
    mocker.patch(
        "builtins.input",
        side_effect=[
            "get-code 42",
            "quit",
        ],
    )

    @app.command
    def get_code(code: int) -> int:
        return code

    with console.capture() as capture:
        app.interactive_shell(console=console)

    actual = capture.get()
    assert "42" not in actual


def test_interactive_shell_result_action_default_bool_true(app, mocker, console):
    """Test that True returns are not printed in interactive shell."""
    mocker.patch(
        "builtins.input",
        side_effect=[
            "check",
            "quit",
        ],
    )

    @app.command
    def check() -> bool:
        return True

    with console.capture() as capture:
        app.interactive_shell(console=console)

    actual = capture.get()
    assert "True" not in actual


def test_interactive_shell_result_action_default_bool_false(app, mocker, console):
    """Test that False returns are not printed in interactive shell."""
    mocker.patch(
        "builtins.input",
        side_effect=[
            "check",
            "quit",
        ],
    )

    @app.command
    def check() -> bool:
        return False

    with console.capture() as capture:
        app.interactive_shell(console=console)

    actual = capture.get()
    assert "False" not in actual


def test_interactive_shell_result_action_default_none(app, mocker, console):
    """Test that None returns are not printed in interactive shell."""
    mocker.patch(
        "builtins.input",
        side_effect=[
            "do-nothing",
            "quit",
        ],
    )

    @app.command
    def do_nothing() -> None:
        pass

    with console.capture() as capture:
        app.interactive_shell(console=console)

    actual = capture.get()
    assert "None" not in actual


def test_interactive_shell_result_action_default_list(mocker, console):
    """Test that list returns are printed in interactive shell."""
    app = App()

    mocker.patch(
        "builtins.input",
        side_effect=[
            "get-list",
            "quit",
        ],
    )

    @app.command
    def get_list() -> list:
        return [1, 2, 3]

    with console.capture() as capture:
        app.interactive_shell(console=console)

    actual = capture.get()
    assert "[1, 2, 3]" in actual


def test_interactive_shell_result_action_custom_app(app, mocker, console):
    """Test that custom result_action on App is respected in interactive shell."""
    custom_app = App(result_action="print_non_none_return_int_as_exit_code")

    mocker.patch(
        "builtins.input",
        side_effect=[
            "get-number",
            "quit",
        ],
    )

    @custom_app.command
    def get_number() -> int:
        return 42

    with console.capture() as capture:
        custom_app.interactive_shell(console=console)

    actual = capture.get()
    assert "42" in actual


def test_interactive_shell_result_action_override_parameter(app, mocker, console):
    """Test that result_action parameter overrides App setting."""
    mocker.patch(
        "builtins.input",
        side_effect=[
            "greet Bob",
            "quit",
        ],
    )

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    with console.capture() as capture:
        app.interactive_shell(console=console, result_action="return_int_as_exit_code_else_zero")

    actual = capture.get()
    assert "Hello Bob!" not in actual


def test_interactive_shell_result_action_callable(app, mocker, console):
    """Test that callable result_action works in interactive shell."""
    mocker.patch(
        "builtins.input",
        side_effect=[
            "greet Alice",
            "quit",
        ],
    )

    results = []

    def custom_handler(result):
        results.append(f"CUSTOM: {result}")
        return result

    @app.command
    def greet(name: str) -> str:
        return f"Hello {name}!"

    app.interactive_shell(console=console, result_action=custom_handler)

    assert results == ["CUSTOM: Hello Alice!"]


def test_interactive_shell_async_command(mocker, console):
    """Async commands should be run, not returned as un-awaited coroutines.

    See https://github.com/BrianPugh/cyclopts/issues/826
    """
    app = App(backend="asyncio")

    mocker.patch(
        "builtins.input",
        side_effect=[
            "start",
            "quit",
        ],
    )

    start_called = 0

    @app.command
    async def start():
        nonlocal start_called
        start_called += 1
        return "Started!"

    with console.capture() as capture:
        app.interactive_shell(console=console)

    actual = capture.get()

    assert start_called == 1
    assert "Started!" in actual
    assert "coroutine object" not in actual


def test_interactive_shell_no_sys_exit_on_command(app, mocker, console):
    """Test that commands continue to execute (no sys.exit called) in interactive shell."""
    mocker.patch(
        "builtins.input",
        side_effect=[
            "cmd1",
            "cmd2",
            "cmd3",
            "quit",
        ],
    )

    cmd1_called, cmd2_called, cmd3_called = 0, 0, 0

    @app.command
    def cmd1():
        nonlocal cmd1_called
        cmd1_called += 1
        return "result1"

    @app.command
    def cmd2():
        nonlocal cmd2_called
        cmd2_called += 1
        return 0

    @app.command
    def cmd3():
        nonlocal cmd3_called
        cmd3_called += 1
        return True

    app.interactive_shell(console=console)

    assert cmd1_called == 1
    assert cmd2_called == 1
    assert cmd3_called == 1


def test_interactive_shell_unbalanced_quote(app, mocker, console):
    """A tokenization error should be reported and the shell should keep running."""
    mocker.patch("builtins.input", side_effect=['foo "1', "foo 2", "quit"])

    calls = []

    @app.command
    def foo(a: int):
        calls.append(a)

    with console.capture() as capture:
        app.interactive_shell(error_console=console)

    assert calls == [2]
    assert capture.get() == (
        "╭─ Error ────────────────────────────────────────────────────────────╮\n"
        "│ No closing quotation: 'foo \"1'                                     │\n"
        "╰────────────────────────────────────────────────────────────────────╯\n"
    )


def test_interactive_shell_keyboard_interrupt_clears_typed_line(app, mocker, readline):
    """Ctrl-C with text on the line should discard the line, not exit the shell."""
    mocker.patch("builtins.input", side_effect=[KeyboardInterrupt(), "foo 1", "quit"])
    readline.get_line_buffer.return_value = "foo 5"

    calls = []

    @app.command
    def foo(a: int):
        calls.append(a)

    app.interactive_shell()

    assert calls == [1]


def test_interactive_shell_keyboard_interrupt_empty_line_exits(app, mocker, readline):
    mock_input = mocker.patch("builtins.input", side_effect=[KeyboardInterrupt(), "foo 1", "quit"])
    readline.get_line_buffer.return_value = ""

    calls = []

    @app.command
    def foo(a: int):
        calls.append(a)

    app.interactive_shell()

    assert calls == []
    assert mock_input.call_count == 1


def test_interactive_shell_keyboard_interrupt_stale_libedit_buffer_after_interrupt(app, mocker, readline):
    """Libedit reports the previous line until new text is typed; a repeat means the line was empty."""
    mock_input = mocker.patch("builtins.input", side_effect=["foo 1", KeyboardInterrupt(), KeyboardInterrupt(), "quit"])
    readline.get_line_buffer.side_effect = ["foo 2", "foo 2"]

    calls = []

    @app.command
    def foo(a: int):
        calls.append(a)

    app.interactive_shell()

    assert calls == [1]
    assert mock_input.call_count == 3


def test_interactive_shell_keyboard_interrupt_stale_libedit_buffer_after_line(app, mocker, readline):
    mock_input = mocker.patch("builtins.input", side_effect=["foo 1", KeyboardInterrupt(), "quit"])
    readline.get_line_buffer.return_value = "foo 1\n"

    calls = []

    @app.command
    def foo(a: int):
        calls.append(a)

    app.interactive_shell()

    assert calls == [1]
    assert mock_input.call_count == 2


def test_interactive_shell_keyboard_interrupt_in_command(app, mocker):
    """Ctrl-C during a command should return to the prompt when suppress_keyboard_interrupt is set."""
    mocker.patch("builtins.input", side_effect=["foo", "bar", "quit"])

    calls = []

    @app.command
    def foo():
        raise KeyboardInterrupt

    @app.command
    def bar():
        calls.append("bar")

    app.interactive_shell()
    assert calls == ["bar"]


def test_interactive_shell_keyboard_interrupt_in_command_not_suppressed(mocker):
    mocker.patch("builtins.input", side_effect=["foo", "quit"])
    app = App(suppress_keyboard_interrupt=False)

    @app.command
    def foo():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        app.interactive_shell()


def test_interactive_shell_exception_goes_to_error_console(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["foo", "quit"])

    @app.command
    def foo():
        raise RuntimeError("boom")

    with console.capture() as capture:
        app.interactive_shell(error_console=console)

    actual = capture.get()
    assert "Traceback (most recent call last):" in actual
    assert "RuntimeError: boom" in actual


def test_interactive_shell_subcommand_error_console(mocker, console):
    """A subcommand's own error_console must not be overridden by the root's."""
    mocker.patch("builtins.input", side_effect=["sub foo notanint", "quit"])

    root = App()
    sub = App(name="sub", error_console=console)
    root.command(sub)

    @sub.command
    def foo(a: int):
        pass

    with console.capture() as capture:
        root.interactive_shell()

    assert "Error" in capture.get()


def test_interactive_shell_exit_word(app, mocker):
    mock_input = mocker.patch("builtins.input", side_effect=["exit", "foo"])

    @app.command
    def foo():
        pass

    app.interactive_shell()
    assert mock_input.call_count == 1


def test_interactive_shell_intro_default(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["quit"])

    with console.capture() as capture:
        app.interactive_shell(console=console)

    assert capture.get() == DEFAULT_SHELL_INTRO + "\n"


def test_interactive_shell_intro_custom(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["quit"])

    with console.capture() as capture:
        app.interactive_shell(console=console, intro="Welcome!")

    assert capture.get() == "Welcome!\n"


def test_interactive_shell_intro_none(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["quit"])

    with console.capture() as capture:
        app.interactive_shell(console=console, intro=None)

    assert capture.get() == ""


def test_interactive_shell_history_file(app, mocker, tmp_path, readline):
    mocker.patch("builtins.input", side_effect=["quit"])
    history_file = tmp_path / "nested" / "history"

    app.interactive_shell(history_file=str(history_file))

    readline.clear_history.assert_called_once_with()
    readline.read_history_file.assert_called_once_with(history_file)
    readline.write_history_file.assert_called_once_with(history_file)
    assert history_file.parent.is_dir()


def test_interactive_shell_history_file_expands_user(app, mocker, readline):
    mocker.patch("builtins.input", side_effect=["quit"])
    mocker.patch("pathlib.Path.mkdir")

    app.interactive_shell(history_file="~/.myapp_history")

    readline.write_history_file.assert_called_once_with(Path.home() / ".myapp_history")


@pytest.mark.parametrize("error", [FileNotFoundError, PermissionError])
def test_interactive_shell_history_file_read_error_ignored(app, mocker, readline, error):
    """Missing file on first run, or libedit's PermissionError on a header-only file."""
    mocker.patch("builtins.input", side_effect=["quit"])
    readline.read_history_file.side_effect = error

    app.interactive_shell(history_file="history")

    readline.write_history_file.assert_called_once()


def test_interactive_shell_history_file_write_error_ignored(app, mocker, readline):
    mocker.patch("builtins.input", side_effect=["quit"])
    readline.write_history_file.side_effect = PermissionError

    app.interactive_shell(history_file="history")


def test_interactive_shell_history_file_written_on_exception(mocker, readline):
    mocker.patch("builtins.input", side_effect=["foo"])
    app = App(suppress_keyboard_interrupt=False)

    @app.command
    def foo():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        app.interactive_shell(history_file="history")

    readline.write_history_file.assert_called_once()


def test_interactive_shell_intro_not_markup(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["quit"])

    with console.capture() as capture:
        app.interactive_shell(console=console, intro="Type [help] or [q]")

    assert capture.get() == "Type [help] or [q]\n"


def test_interactive_shell_quit_word_user_command_wins(app, mocker):
    mock_input = mocker.patch("builtins.input", side_effect=["exit", "quit"])
    calls = []

    @app.command
    def exit():
        calls.append("exit")

    app.interactive_shell(intro=None)
    assert calls == ["exit"]
    assert mock_input.call_count == 2


def test_interactive_shell_remap_help_root(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["help", "quit"])

    @app.command
    def foo(a: int):
        """Foo docstring."""

    with console.capture() as capture:
        app.interactive_shell(console=console, intro=None)

    actual = capture.get()
    assert "Usage:" in actual
    assert "Foo docstring." in actual


def test_interactive_shell_remap_subcommand_not_remapped(app, mocker):
    """Only the root remaps; ``foo help`` passes ``help`` through as data."""
    mocker.patch("builtins.input", side_effect=["foo help", "quit"])
    calls = []

    @app.command
    def foo(a: str):
        calls.append(a)

    app.interactive_shell(intro=None)
    assert calls == ["help"]


def test_interactive_shell_remap_version(mocker, console):
    mocker.patch("builtins.input", side_effect=["version", "quit"])
    app = App(version="1.2.3")

    with console.capture() as capture:
        app.interactive_shell(console=console, intro=None)

    assert capture.get() == "1.2.3\n"


def test_interactive_shell_remap_user_command_wins(app, mocker):
    mocker.patch("builtins.input", side_effect=["help", "quit"])
    calls = []

    @app.command
    def help():
        calls.append("help")

    app.interactive_shell(intro=None)
    assert calls == ["help"]


def test_interactive_shell_remap_shadowed_by_parameter(app, mocker):
    """A default command whose own parameter claims ``--help`` receives the bare word as data."""
    mocker.patch("builtins.input", side_effect=["help", "quit"])
    calls = []

    @app.default
    def main(help: str):
        calls.append(help)

    app.interactive_shell(intro=None)
    assert calls == ["help"]


def test_interactive_shell_remap_only_first_token(app, mocker):
    mocker.patch("builtins.input", side_effect=["1 help", "quit"])
    calls = []

    @app.default
    def main(a: int, b: str):
        calls.append((a, b))

    app.interactive_shell(intro=None)
    assert calls == [(1, "help")]


def test_interactive_shell_remap_short_flag_not_remapped(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["h", "quit"])

    @app.command
    def foo():
        pass

    with console.capture() as capture:
        app.interactive_shell(error_console=console, intro=None)

    assert 'Unknown command "h"' in capture.get()


def test_interactive_shell_remap_disabled(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["help", "quit"])

    @app.command
    def foo():
        pass

    with console.capture() as capture:
        app.interactive_shell(error_console=console, intro=None, remap_flags=False)

    assert 'Unknown command "help"' in capture.get()


def test_interactive_shell_remap_help_panel_lists_bare_words(mocker, console):
    """Remapped ``help``/``version`` are listed by their bare word and sorted like any other command."""
    mocker.patch("builtins.input", side_effect=["help", "quit"])
    app = App(name="app", version="1.0", result_action="return_value")

    @app.command
    def zoo():
        """Zoo docstring."""

    @app.command
    def bar():
        """Bar docstring."""

    with console.capture() as capture:
        app.interactive_shell(console=console, intro=None)

    assert capture.get() == textwrap.dedent(
        """\
        Usage: app COMMAND

        ╭─ Commands ─────────────────────────────────────────────────────────╮
        │ bar                  Bar docstring.                                │
        │ help (--help, -h)    Display this message and exit.                │
        │ version (--version)  Display application version.                  │
        │ zoo                  Zoo docstring.                                │
        ╰────────────────────────────────────────────────────────────────────╯
        """
    )


def test_interactive_shell_remap_help_panel_user_command_not_aliased(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["--help", "quit"])

    @app.command
    def help():
        """User help."""

    with console.capture() as capture:
        app.interactive_shell(console=console, intro=None)

    actual = capture.get()
    assert "User help." in actual
    assert "--help (-h)" in actual
    assert "help (--help" not in actual
    assert "version (--version)" in actual


def test_interactive_shell_remap_disabled_help_panel_unchanged(app, mocker, console):
    mocker.patch("builtins.input", side_effect=["--help", "quit"])

    with console.capture() as capture:
        app.interactive_shell(console=console, intro=None, remap_flags=False)

    actual = capture.get()
    assert "--help (-h)" in actual
    assert "help (--help" not in actual


def test_interactive_shell_remap_help_panel_subcommand_unchanged(app, mocker, console):
    """A nested app's help page keeps the plain flags; only the root lists ``help``."""
    mocker.patch("builtins.input", side_effect=["foo --help", "quit"])
    foo = App(name="foo")
    app.command(foo)

    @foo.command
    def bar():
        pass

    with console.capture() as capture:
        app.interactive_shell(console=console, intro=None)

    actual = capture.get()
    assert "│ bar" in actual
    assert "help (--help" not in actual
