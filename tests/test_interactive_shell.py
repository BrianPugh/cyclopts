from cyclopts import App


def test_interactive_shell(app, mocker, console):
    mocker.patch(
        "cyclopts.core.input",
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
        "cyclopts.core.input",
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
        "cyclopts.core.input",
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
        "cyclopts.core.input",
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
        "cyclopts.core.input",
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
        "cyclopts.core.input",
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
        "cyclopts.core.input",
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
        "cyclopts.core.input",
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
        "cyclopts.core.input",
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
        "cyclopts.core.input",
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


def test_interactive_shell_no_sys_exit_on_command(app, mocker, console):
    """Test that commands continue to execute (no sys.exit called) in interactive shell."""
    mocker.patch(
        "cyclopts.core.input",
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
